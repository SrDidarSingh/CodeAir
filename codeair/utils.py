# Copyright (c) 2025 Didar Singh. All rights reserved.
# Licensed under the CodeAir Source Available License v1.0
# See LICENSE file in the root of this repository.
"""
codeair/utils.py  —  shared helpers
"""

import os
import socket
import inspect
import zipfile


# ── Network ───────────────────────────────────────────────────────────────────

def get_lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def find_free_port(start: int = 8765) -> int:
    for port in range(start, start + 200):
        try:
            s = socket.socket()
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("", port))
            s.close()
            return port
        except OSError:
            continue
    return start


# ── QR code ───────────────────────────────────────────────────────────────────

def print_qr(url: str) -> None:
    try:
        import qrcode
        qr = qrcode.QRCode(border=2)
        qr.add_data(url)
        qr.make(fit=True)
        # Use 2 chars per cell horizontally so the QR renders as a square.
        # Terminal characters are ~2x taller than wide, so "██" width ≈ cell height.
        matrix = qr.get_matrix()
        for row in matrix:
            print("".join("██" if cell else "  " for cell in row))
        print()
    except ImportError:
        print("\n  [qrcode not installed — pip install qrcode]")
        print("  URL: " + url + "\n")


# ── File helpers ──────────────────────────────────────────────────────────────

def get_current_file() -> str | None:
    """
    Walk the call stack to find the first .py file that isn't part of
    the codeair library itself.  Works in IDLE, terminal, and PyCharm.
    Filters by filename only so a project folder named 'codeair' won't
    accidentally block the user's own scripts.
    """
    _OWN_BASENAMES = {"__init__.py", "push.py", "pull.py", "utils.py"}
    for frame_info in inspect.stack():
        fname: str = frame_info[1]
        if not fname:
            continue
        if fname in ("<string>", "<stdin>"):
            continue
        if not fname.endswith(".py"):
            continue
        if os.path.basename(fname) in _OWN_BASENAMES:
            continue
        return os.path.abspath(fname)
    return None


def get_py_files_in_cwd() -> list[str]:
    """Top-level .py files only (used for option 3 module listing)."""
    cwd = os.getcwd()
    return sorted(
        os.path.join(cwd, f)
        for f in os.listdir(cwd)
        if f.endswith(".py")
    )


# Folders/suffixes to skip when walking the project tree
_SKIP_DIRS = {
    ".venv", "venv", ".env", "env",
    "__pycache__", ".git", ".hg", ".svn",
    "node_modules", ".tox", ".mypy_cache",
    ".pytest_cache", "dist", "build",
}
_SKIP_SUFFIXES = (".egg-info", ".dist-info")


def get_all_project_py_files(root: str | None = None) -> list[str]:
    """
    Recursively collect every .py file under root (default: cwd),
    skipping virtual-envs, caches, build artefacts, etc.
    Returns a sorted list of absolute paths.
    """
    if root is None:
        root = os.getcwd()
    result: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune dirs in-place so os.walk won't descend into them
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in _SKIP_DIRS
            and not any(d.endswith(s) for s in _SKIP_SUFFIXES)
        )
        for f in filenames:
            if f.endswith(".py"):
                result.append(os.path.join(dirpath, f))
    return sorted(result)


def bundle_to_zip(files: list[str], dest: str, root: str | None = None) -> str:
    """
    Zip files into dest, preserving relative paths from root.
    Returns dest.
    """
    if root is None:
        root = os.getcwd()
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            try:
                arcname = os.path.relpath(path, root)
            except ValueError:
                arcname = os.path.basename(path)
            zf.write(path, arcname)
    return dest


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} TB"


def get_all_project_files(root=None):
    """
    Recursively collect EVERY file under root (default: cwd),
    skipping virtual-envs, caches, build artefacts, and hidden dot-dirs.
    Returns a sorted list of absolute paths.
    """
    if root is None:
        root = os.getcwd()

    SKIP_DIRS = {
        ".venv", "venv", ".env", "env",
        "__pycache__", ".git", ".hg", ".svn",
        "node_modules", ".tox", ".mypy_cache",
        ".pytest_cache", "dist", "build",
    }
    SKIP_SUFFIXES = (".egg-info", ".dist-info")

    result = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in SKIP_DIRS
            and not any(d.endswith(s) for s in SKIP_SUFFIXES)
            and not d.startswith(".")          # skip all hidden dirs
        )
        for f in filenames:
            if f.startswith("."):              # skip hidden files
                continue
            result.append(os.path.join(dirpath, f))
    return sorted(result)