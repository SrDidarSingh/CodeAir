# Copyright (c) 2025 Didar Singh. All rights reserved.
# Licensed under the CodeAir Source Available License v1.0
# See LICENSE file in the root of this repository.
"""
codeair/push.py  --  PC -> Phone  (push)
"""

import os
import shutil
import tempfile
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from .tunnel import close_tunnel, open_tunnel
from .utils import (
    bundle_to_zip, find_free_port, get_current_file,
    get_all_project_files,
    human_size, print_qr,
)


# ── HTML ──────────────────────────────────────────────────────────────────────

def _page(body):
    css = (
        "<style>"
        "*{box-sizing:border-box;margin:0;padding:0}"
        "body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;"
        "background:#0d0d0f;color:#e2e2e2;display:flex;flex-direction:column;"
        "align-items:center;justify-content:center;min-height:100vh;padding:24px}"
        ".card{background:#141416;border:1px solid #252528;border-radius:20px;"
        "padding:36px 28px;text-align:center;max-width:400px;width:100%;"
        "box-shadow:0 8px 40px #00000066}"
        ".logo{font-size:2rem;margin-bottom:4px}"
        "h1{color:#00ffcc;font-size:1.5rem;font-weight:700;margin-bottom:6px}"
        ".sub{color:#666;font-size:.85rem;margin-bottom:24px}"
        ".fname{background:#0d0d0f;border:1px solid #252528;border-radius:10px;"
        "padding:12px 16px;margin:16px 0;color:#00ffcc;font-size:.9rem;"
        "word-break:break-all}"
        ".size{color:#555;font-size:.8rem;margin-bottom:8px}"
        ".btn{display:block;background:#00ffcc;color:#000;font-weight:700;"
        "font-size:1.05rem;padding:15px;border:none;border-radius:12px;"
        "cursor:pointer;margin-top:20px;text-decoration:none;width:100%}"
        ".btn:active{opacity:.85}"
        "input[type=password]{background:#0d0d0f;border:1px solid #333;"
        "border-radius:10px;color:#eee;font-size:1rem;padding:13px 16px;"
        "width:100%;margin:14px 0;text-align:center;outline:none}"
        "input[type=password]:focus{border-color:#00ffcc}"
        ".err{color:#ff6b6b;font-size:.88rem;margin-top:8px}"
        ".list{margin-top:16px;text-align:left}"
        ".item{display:flex;align-items:center;gap:10px;padding:12px 14px;"
        "border-bottom:1px solid #1e1e20;text-decoration:none;color:#e2e2e2}"
        ".item:last-child{border-bottom:none}"
        ".icon{font-size:1.1rem}"
        ".iname{flex:1;font-size:.85rem;word-break:break-all}"
        ".dl{color:#00ffcc;font-size:.8rem;font-weight:600}"
        "</style>"
    )
    return (
        "<!DOCTYPE html><html lang='en'>"
        "<head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>CodeAir</title>" + css + "</head>"
        "<body><div class='card'>" + body + "</div></body></html>"
    )


def _header():
    return "<div class='logo'>\u2708</div><h1>CodeAir</h1>"


def _pw_page(error=False):
    err = "<p class='err'>\u2717 Incorrect password.</p>" if error else ""
    return _page(
        _header() +
        "<p class='sub'>Password protected transfer</p>"
        "<form method='POST'>"
        "<input type='password' name='pw' placeholder='Enter password' autofocus>"
        "<button class='btn' type='submit'>Unlock \u2192</button>"
        "</form>" + err
    )


def _download_page(filename, size_str):
    return _page(
        _header() +
        "<p class='sub'>Ready to download</p>"
        "<div class='fname'>\U0001f4c4 " + filename + "</div>"
        "<p class='size'>" + size_str + "</p>"
        "<a href='/download' class='btn'>\u2b07 Download</a>"
    )


def _listing_page(entries):
    items = "".join(
        "<a class='item' href='/file/" + name + "'>"
        "<span class='icon'>\U0001f4c4</span>"
        "<span class='iname'>" + name + "</span>"
        "<span class='dl'>\u2b07</span></a>"
        for name, _ in entries
    )
    return _page(
        _header() +
        "<p class='sub'>" + str(len(entries)) + " file(s) available</p>"
        "<div class='list'>" + items + "</div>"
    )


# ── Request handler ───────────────────────────────────────────────────────────

def _make_handler(*, serve_path=None, serve_bytes=None, serve_name="file",
                  password=None, listing=None):
    authed_ips = set()

    class _H(BaseHTTPRequestHandler):
        def log_message(self, *_): pass

        def handle(self):
            try:
                super().handle()
            except (ConnectionResetError, BrokenPipeError):
                pass

        def _ip(self):
            return self.client_address[0]

        def _ok(self):
            return (not password) or (self._ip() in authed_ips)

        def _html(self, body, code=200):
            raw = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Bypass-Tunnel-Reminder", "true")  # skip pinggy interstitial
            self.end_headers()
            try:
                self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def _send_bytes(self, data, name):
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition",
                             "attachment; filename=\"" + name + "\"")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Bypass-Tunnel-Reminder", "true")  # skip pinggy interstitial
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def _read(self, path):
            with open(path, "rb") as fh:
                return fh.read()

        def _redirect(self, loc):
            self.send_response(302)
            self.send_header("Location", loc)
            self.send_header("Bypass-Tunnel-Reminder", "true")  # skip pinggy interstitial
            self.end_headers()

        def do_GET(self):
            path = urlparse(self.path).path

            if path == "/":
                if not self._ok():
                    self._html(_pw_page()); return
                if listing:
                    self._html(_listing_page(listing))
                elif serve_path:
                    self._html(_download_page(serve_name,
                               human_size(os.path.getsize(serve_path))))
                else:
                    self._html(_download_page(serve_name,
                               human_size(len(serve_bytes))))
                return

            if path == "/download":
                if not self._ok():
                    self._html(_pw_page()); return
                if serve_path:
                    self._send_bytes(self._read(serve_path), serve_name)
                elif serve_bytes is not None:
                    self._send_bytes(serve_bytes, serve_name)
                else:
                    self.send_error(404)
                return

            if path.startswith("/file/") and listing:
                if not self._ok():
                    self._html(_pw_page()); return
                wanted = path[6:]
                for name, abspath in listing:
                    if name == wanted:
                        self._send_bytes(self._read(abspath), os.path.basename(name))
                        return
                self.send_error(404)
                return

            self.send_error(404)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode(errors="replace")
            params = parse_qs(body)
            pw_in = params.get("pw", [""])[0]
            if pw_in == password:
                authed_ips.add(self._ip())
                self._redirect("/")
            else:
                self._html(_pw_page(error=True))

    return _H


# ── Push wizard ───────────────────────────────────────────────────────────────

def push(password=None):
    print()
    print("  \u2554" + "\u2550" * 42 + "\u2557")
    print("  \u2551   PUSH  \u2500\u2500  Send from PC \u2192 Phone         \u2551")
    print("  \u2560" + "\u2550" * 42 + "\u2563")
    print("  \u2551  [1]  Current .py file                   \u2551")
    print("  \u2551  [2]  Custom text  (as .txt)             \u2551")
    print("  \u2551  [3]  Send by path  (file or folder)     \u2551")
    print("  \u2551  [4]  Whole project                      \u2551")
    print("  \u255a" + "\u2550" * 42 + "\u255d")

    try:
        choice = input("  Choose (1/2/3/4): ").strip()
    except (EOFError, KeyboardInterrupt):
        print(); return

    tmpdir = tempfile.mkdtemp(prefix="codeair_push_")

    try:
        serve_path = None
        serve_bytes = None
        serve_name = "file"
        listing = None

        if choice == "1":
            cur = get_current_file()
            if not cur:
                print("\n  \u2717  Could not detect current .py file.")
                print("     Run from within a saved .py script.\n")
                return
            serve_path = cur
            serve_name = os.path.basename(cur)
            print("\n  \u2713  Found: " + serve_name)

        elif choice == "2":
            print("\n  Paste or type your text.")
            print("  Type  END  on its own line when done:\n")
            lines = []
            while True:
                try:
                    ln = input()
                except EOFError:
                    break
                if ln.strip() == "END":
                    break
                lines.append(ln)
            serve_bytes = "\n".join(lines).encode("utf-8")
            serve_name = "text.txt"
            print("\n  \u2713  " + human_size(len(serve_bytes)) + " of text ready.")

        elif choice == "3":
            raw_path = input("\n  Enter file or folder path: ").strip().strip("'\"")
            raw_path = raw_path.replace("\\ ", " ").replace("\\~", "~")
            target = os.path.expanduser(raw_path)
            target = os.path.abspath(target)

            if not os.path.exists(target):
                print("\n  \u2717  Path not found: " + target + "\n")
                return

            if os.path.isfile(target):
                serve_path = target
                serve_name = os.path.basename(target)
                print("\n  \u2713  File: " + serve_name +
                      "  (" + human_size(os.path.getsize(target)) + ")")
            else:
                folder_name = os.path.basename(target.rstrip("/\\"))
                zip_path = os.path.join(tmpdir, folder_name + ".zip")
                all_files = _walk_folder(target)
                if not all_files:
                    print("\n  \u2717  Folder is empty.\n")
                    return
                bundle_to_zip(all_files, zip_path, root=target)
                serve_path = zip_path
                serve_name = folder_name + ".zip"
                print("\n  \u2713  Folder zipped: " + serve_name +
                      "  (" + human_size(os.path.getsize(zip_path)) + ")" +
                      "  [" + str(len(all_files)) + " files]")

        elif choice == "4":
            root = os.getcwd()
            selected = get_all_project_files(root)
            if not selected:
                print("\n  \u2717  No files found in current directory.\n")
                return

            print("\n  " + str(len(selected)) + " file(s) found in project.")
            fmt = input("  Format — [1] Zip  [2] Individual links: ").strip()

            if fmt == "1":
                zip_path = os.path.join(tmpdir, "project.zip")
                bundle_to_zip(selected, zip_path, root=root)
                serve_path = zip_path
                serve_name = "project.zip"
                print("\n  \u2713  Zipped \u2192 " + serve_name +
                      "  (" + human_size(os.path.getsize(zip_path)) + ")")
            else:
                listing = [(os.path.relpath(f, root), f) for f in selected]
                print("\n  \u2713  " + str(len(listing)) +
                      " files ready for individual download.")
        else:
            print("\n  \u2717  Invalid choice.\n")
            return

        if password is None:
            pw_in = input("\n  Download password? (leave blank = none): ").strip()
            if pw_in:
                password = pw_in

        port = find_free_port()
        handler = _make_handler(
            serve_path=serve_path,
            serve_bytes=serve_bytes,
            serve_name=serve_name,
            password=password,
            listing=listing,
        )
        server = HTTPServer(("0.0.0.0", port), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()

        print("\n  Opening tunnel\u2026")
        url, tunnel_proc = open_tunnel(port)

        print()
        print("  \u250c" + "\u2500" * 48 + "\u2510")
        if password:
            print("  \u2502  \U0001f512  Password : {:<26}\u2502".format(password))
        print("  \u2502     URL     : {:<26}  \u2502".format(url))
        print("  \u2514" + "\u2500" * 48 + "\u2518")
        print("  Scan with your phone camera:\n")
        print_qr(url)

        input("  \u2500\u2500 Press ENTER to stop server & expire QR \u2500\u2500")
        server.shutdown()
        close_tunnel(tunnel_proc)
        print("  \u2713  QR expired. Transfer session closed.\n")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _walk_folder(root):
    result = []
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            result.append(os.path.join(dirpath, f))
    return sorted(result)