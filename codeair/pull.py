# Copyright (c) 2025 Didar Singh. All rights reserved.
# Licensed under the CodeAir Source Available License v1.0
# See LICENSE file in the root of this repository.
"""
codeair/pull.py  —  Phone → PC  (pull)
"""

import io
import os
import threading
import zipfile
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

from .tunnel import close_tunnel, open_tunnel
from .utils import find_free_port, human_size, print_qr


def _desktop() -> str:
    desk = os.path.join(os.path.expanduser("~"), "Desktop")
    if not os.path.isdir(desk):
        desk = os.path.expanduser("~")
    return desk


# ── HTML ──────────────────────────────────────────────────────────────────────

def _page(body: str) -> str:
    css = (
        "<style>"
        "*{box-sizing:border-box;margin:0;padding:0}"
        "body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;"
        "background:#0d0d0f;color:#e2e2e2;display:flex;flex-direction:column;"
        "align-items:center;justify-content:center;min-height:100vh;padding:24px}"
        ".card{background:#141416;border:1px solid #252528;border-radius:20px;"
        "padding:36px 28px;text-align:center;max-width:400px;width:100%}"
        ".logo{font-size:2rem;margin-bottom:4px}"
        "h1{color:#00ffcc;font-size:1.5rem;font-weight:700;margin-bottom:6px}"
        ".sub{color:#666;font-size:.85rem;margin-bottom:24px}"
        ".dropzone{border:2px dashed #2a2a2d;border-radius:14px;padding:28px 20px;"
        "margin:16px 0;cursor:pointer}"
        ".dropzone p{color:#555;font-size:.9rem}"
        ".dropzone .icon{font-size:2rem;margin-bottom:8px}"
        "#fname{color:#00ffcc;font-size:.9rem;margin-top:8px;min-height:20px}"
        ".btn{display:block;background:#00ffcc;color:#000;font-weight:700;"
        "font-size:1.05rem;padding:15px;border:none;border-radius:12px;"
        "cursor:pointer;margin-top:20px;width:100%}"
        ".btn:disabled{background:#1e3d35;color:#3a7a68;cursor:not-allowed}"
        "input[type=file]{display:none}"
        ".ok{color:#00ffcc;font-size:1.8rem;margin:16px 0}"
        ".sub2{color:#aaa;font-size:.9rem}"
        "progress{width:100%;height:6px;border-radius:3px;margin-top:16px;"
        "appearance:none;background:#1a1a1c}"
        "progress::-webkit-progress-bar{background:#1a1a1c;border-radius:3px}"
        "progress::-webkit-progress-value{background:#00ffcc;border-radius:3px}"
        "</style>"
    )
    return (
        "<!DOCTYPE html><html lang='en'>"
        "<head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>CodeAir</title>" + css + "</head>"
        "<body><div class='card'>" + body + "</div></body></html>"
    )


_UPLOAD_PAGE = _page(
    "<div class='logo'>\u2708</div><h1>CodeAir</h1>"
    "<p class='sub'>Send a file to the PC</p>"
    "<div class='dropzone' id='dz' onclick=\"document.getElementById('fi').click()\">"
    "<div class='icon'>\U0001f4c2</div>"
    "<p>Tap to choose a file</p>"
    "<p id='fname'></p>"
    "</div>"
    "<input type='file' id='fi' name='file'>"
    "<button class='btn' id='btn' disabled onclick='uploadFile()'>"
    "\u2b06 Send to PC</button>"
    "<progress id='prog' value='0' max='100' style='display:none'></progress>"
    "<script>"
    "var fi=document.getElementById('fi'),"
    "fn=document.getElementById('fname'),"
    "btn=document.getElementById('btn'),"
    "prog=document.getElementById('prog');"
    "fi.onchange=function(){"
    "  if(fi.files[0]){"
    "    fn.textContent=fi.files[0].name;"
    "    btn.disabled=false;}};"
    "function uploadFile(){"
    "  var fd=new FormData();"
    "  fd.append('file',fi.files[0]);"
    "  btn.disabled=true;"
    "  btn.textContent='Sending...';"
    "  prog.style.display='block';"
    "  var xhr=new XMLHttpRequest();"
    "  xhr.upload.onprogress=function(e){"
    "    if(e.lengthComputable)"
    "      prog.value=Math.round(e.loaded/e.total*100);};"
    "  xhr.onload=function(){"
    "    if(xhr.status===200)"
    "      document.body.innerHTML=xhr.responseText;"
    "    else{"
    "      btn.disabled=false;"
    "      btn.textContent='\u2b06 Send to PC';}};"
    "  xhr.open('POST','/upload');"
    "  xhr.send(fd);}"
    "</script>"
)


def _done_page(filename: str, size_str: str) -> str:
    return _page(
        "<div class='logo'>\u2708</div><h1>CodeAir</h1>"
        "<div class='ok'>\u2713</div>"
        "<p class='sub2'>Received by PC!</p>"
        "<div style='margin-top:18px;color:#555;font-size:.85rem'>"
        + filename + " \u00b7 " + size_str +
        "</div>"
    )


# ── Multipart parser ──────────────────────────────────────────────────────────

def _parse_multipart(raw: bytes, boundary: str):
    sep = ("--" + boundary).encode()
    parts = raw.split(sep)
    for part in parts:
        if b"Content-Disposition" not in part:
            continue
        if b"filename=" not in part:
            continue
        try:
            header_raw, body = part.split(b"\r\n\r\n", 1)
        except ValueError:
            continue
        if body.endswith(b"\r\n"):
            body = body[:-2]
        filename = None
        for line in header_raw.decode("utf-8", errors="replace").splitlines():
            if "filename=" in line:
                for chunk in line.split(";"):
                    chunk = chunk.strip()
                    if chunk.startswith("filename="):
                        filename = chunk[9:].strip().strip('"').strip("'")
                        break
                break
        if not filename:
            filename = "received_file"
        return filename, body
    return None, None


# ── Request handler ───────────────────────────────────────────────────────────

def _make_handler(callback):
    class _H(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def handle(self):
            try:
                super().handle()
            except (ConnectionResetError, BrokenPipeError):
                pass

        def _html(self, body: str, code: int = 200) -> None:
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

        def do_GET(self):
            self._html(_UPLOAD_PAGE)

        def do_POST(self):
            path = urlparse(self.path).path
            if path != "/upload":
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            ct = self.headers.get("Content-Type", "")
            boundary = None
            for part in ct.split(";"):
                part = part.strip()
                if part.startswith("boundary="):
                    boundary = part[9:].strip()
                    break
            if not boundary:
                self.send_error(400, "Missing boundary")
                return
            filename, data = _parse_multipart(raw, boundary)
            if data is None:
                self.send_error(400, "Could not parse upload")
                return
            self._html(_done_page(filename or "file", human_size(len(data))))
            callback(filename or "received_file", data)

    return _H


# ── Public API ────────────────────────────────────────────────────────────────

_TEXT_EXTS = {
    ".py", ".txt", ".md", ".csv", ".json", ".html",
    ".js", ".ts", ".css", ".xml", ".yaml", ".yml",
    ".ini", ".cfg", ".toml", ".sh", ".bat",
}


def pull() -> None:
    received: dict = {}
    event = threading.Event()

    def _on_receive(filename: str, data: bytes) -> None:
        received["filename"] = filename
        received["data"] = data
        event.set()

    port = find_free_port()
    server = HTTPServer(("0.0.0.0", port), _make_handler(_on_receive))
    threading.Thread(target=server.serve_forever, daemon=True).start()

    print()
    print("  \u2554" + "\u2550" * 44 + "\u2557")
    print("  \u2551  PULL   \u2500\u2500  Receive from Phone \u2192 PC        \u2551")
    print("  \u2560" + "\u2550" * 44 + "\u2563")
    print("  \u2551  Opening tunnel\u2026{:<27}\u2551".format(""))
    print("  \u2560" + "\u2550" * 44 + "\u2563")
    # Providing URL
    url, tunnel_proc = open_tunnel(port)
    print("  \u2551  URL : " + url + "     \u2551")
    print("  \u255a" + "\u2550" * 44 + "\u255d")
    print("\n  Scan with your phone camera:\n")
    print_qr(url)
    print("  Waiting for upload\u2026  (Ctrl+C to cancel)\n")

    try:
        event.wait()
    except KeyboardInterrupt:
        print("\n  Cancelled.\n")
        server.shutdown()
        close_tunnel(tunnel_proc)
        return

    server.shutdown()
    close_tunnel(tunnel_proc)

    _handle_received(received["filename"], received["data"])


def _handle_received(filename: str, data: bytes) -> None:
    ext = os.path.splitext(filename)[1].lower()
    print("\n  \u2713  Received: {}  ({})".format(filename, human_size(len(data))))

    if ext in _TEXT_EXTS:
        print()
        print("  \u250c\u2500\u2500 File contents " + "\u2500" * 28 + "\u2510")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("latin-1")
        for line in text.splitlines():
            print("  \u2502 " + line)
        print("  \u2514" + "\u2500" * 43 + "\u2518")
        save = input("\n  Save to disk? [y/n]: ").strip().lower()
        if save == "y":
            _save_file(filename, data)
    elif ext == ".zip":
        dest = os.path.join(_desktop(), os.path.splitext(filename)[0])
        os.makedirs(dest, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            zf.extractall(dest)
        print("  \u2713  Extracted to: {}/\n".format(dest))
    else:
        _save_file(filename, data)


def _save_file(filename: str, data: bytes) -> None:
    path = os.path.join(_desktop(), filename)
    with open(path, "wb") as fh:
        fh.write(data)
    print("  \u2713  Saved to Desktop: {}\n".format(path))