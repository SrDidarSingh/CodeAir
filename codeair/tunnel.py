# Copyright (c) 2025 Didar Singh. All rights reserved.
# Licensed under the CodeAir Source Available License v1.0
# See LICENSE file in the root of this repository.
"""
codeair/tunnel.py  --  Public tunnel via localhost.run (no account needed)

Command:
    ssh -R 80:localhost:<port> nokey@localhost.run
"""

import re
import subprocess
import threading


def open_tunnel(port: int) -> tuple[str, object | None]:
    """
    Open a localhost.run SSH tunnel on *port*.
    Returns (url, proc).
    Falls back to local LAN IP if tunnel fails.
    """
    from .utils import get_lan_ip

    result: dict = {}
    ready = threading.Event()

    def _run():
        try:
            proc = subprocess.Popen(
                [
                    "ssh",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "ServerAliveInterval=30",
                    "-o", "BatchMode=yes",          # never prompt for passwords
                    "-R", "80:localhost:{}".format(port),
                    "nokey@localhost.run",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,           # SSH must NOT touch stdin
                text=True,
            )
            result["proc"] = proc
            for line in proc.stdout:
                # localhost.run prints a line containing the public URL, e.g.:
                # "abc123.lhr.life tunneled with tls termination, https://abc123.lhr.life"
                match = re.search(r"https://[a-z0-9]+\.lhr\.life", line)
                if match:
                    result["url"] = match.group(0)
                    ready.set()
                    break
                if "Permission denied" in line or "Connection refused" in line:
                    result["error"] = line.strip()
                    ready.set()
                    break
        except FileNotFoundError:
            result["error"] = "ssh not found"
            ready.set()

    threading.Thread(target=_run, daemon=True).start()
    ready.wait(timeout=20)

    if "url" in result:
        return result["url"], result.get("proc")

    # Fallback: local LAN
    lan = get_lan_ip()
    fallback = "http://{}:{}".format(lan, port)
    err = result.get("error", "timed out")
    print("\n  \u26a0  Tunnel failed ({}). Using local IP instead.".format(err))
    print("     (Phone must be on the same Wi-Fi)\n")

    proc = result.get("proc")
    if proc:
        try:
            proc.kill()
        except Exception:
            pass

    return fallback, None


def close_tunnel(proc) -> None:
    if proc is None:
        return
    try:
        proc.kill()
        proc.wait(timeout=3)
    except Exception:
        pass