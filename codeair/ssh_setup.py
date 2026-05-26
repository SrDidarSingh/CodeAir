# Copyright (c) 2025 Didar Singh. All rights reserved.
# Licensed under the CodeAir Source Available License v1.0
# See LICENSE file in the root of this repository.
"""
codeair/ssh_setup.py  —  Detect SSH and offer to install it if missing.

Called once before the first tunnel attempt.  On subsequent calls within
the same process the result is cached so the user is never prompted twice.
"""

import platform
import shutil
import subprocess

# Module-level cache: None = not yet checked, True/False = result
_ssh_available: bool | None = None


# ── Public API ────────────────────────────────────────────────────────────────

def ensure_ssh() -> bool:
    """
    Return True if ssh is (or becomes) available.

    First call: checks for ssh, prompts + installs if missing.
    Subsequent calls: return cached result instantly.
    """
    global _ssh_available

    if _ssh_available is not None:          # already resolved this session
        return _ssh_available

    if shutil.which("ssh"):
        _ssh_available = True
        return True

    # ── SSH not found ─────────────────────────────────────────────────────────
    _print_banner()

    try:
        choice = input("  Install SSH now? [y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        _ssh_available = False
        return False

    if choice != "y":
        _warn_fallback()
        _ssh_available = False
        return False

    os_name = platform.system()
    if os_name == "Windows":
        ok = _install_windows()
    elif os_name == "Darwin":
        ok = _install_macos()
    elif os_name == "Linux":
        ok = _install_linux()
    else:
        print("  \u2717  Unrecognised OS ({}).".format(os_name))
        print("     Please install OpenSSH manually and re-run CodeAir.\n")
        ok = False

    _ssh_available = ok
    return ok


# ── Platform installers ───────────────────────────────────────────────────────

def _install_windows() -> bool:
    """
    Try two methods in order:
      1. PowerShell Add-WindowsCapability  (Win 10 1809+ – needs admin)
      2. winget                            (Win 10/11 – user scope, no admin)
      3. Manual instructions
    """
    print()

    # --- Method 1: Windows Optional Features via PowerShell ---
    print("  \u25b6  Trying Windows Optional Features (may need admin)...")
    ps_cmd: list[str] = [
        "powershell", "-NoProfile", "-NonInteractive", "-Command",
        "Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0",
    ]
    try:
        # noinspection PyTypeChecker
        ps_proc = subprocess.run(ps_cmd, capture_output=True, text=True)
        if ps_proc.returncode == 0 and shutil.which("ssh"):
            _print_ok()
            return True
        if "Access" in ps_proc.stderr or "admin" in ps_proc.stderr.lower():
            print("  \u26a0  Needs administrator privileges.")
    except FileNotFoundError:
        print("  \u26a0  PowerShell not found.")

    # --- Method 2: winget ---
    if shutil.which("winget"):
        print("  \u25b6  Trying winget (no admin required)...")  # spellchecker: disable-line
        winget_cmd: list[str] = [
            "winget", "install",                                # spellchecker: disable-line
            "--id", "Microsoft.OpenSSH.Beta",
            "--source", "winget",                               # spellchecker: disable-line
            "--accept-package-agreements",
            "--accept-source-agreements",
            "--silent",
        ]
        try:
            # noinspection PyTypeChecker
            subprocess.run(winget_cmd)
            if shutil.which("ssh"):
                _print_ok()
                print("  \u2139  Restart your terminal for PATH changes to take effect.\n")
                return True
        except Exception as exc:
            print("  \u26a0  winget error: {}".format(exc))     # spellchecker: disable-line
    else:
        print("  \u26a0  winget not found (requires Windows 10 1709+ or App Installer).")  # spellchecker: disable-line

    # --- Method 3: manual fallback ---
    print()
    print("  \u2717  Automatic install failed.  Enable SSH manually:")
    print("     Settings \u2192 Apps \u2192 Optional Features")
    print("             \u2192 Add a feature \u2192 OpenSSH Client")
    print()
    print("     Or run in an admin PowerShell:")
    print("     Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0")
    print()
    _warn_fallback()
    return False


def _install_macos() -> bool:
    """
    SSH ships with every macOS since forever; this branch is a last-resort
    safety net in case someone has an unusual setup.
    """
    print()
    print("  \u2139  SSH should be pre-installed on macOS.")
    print("     It may have been removed by a system policy.")
    print()

    if shutil.which("brew"):
        print("  \u25b6  Trying Homebrew: brew install openssh ...")  # spellchecker: disable-line
        brew_cmd: list[str] = ["brew", "install", "openssh"]   # spellchecker: disable-line
        try:
            # noinspection PyTypeChecker
            subprocess.run(brew_cmd)
            if shutil.which("ssh"):
                _print_ok()
                return True
        except Exception as exc:
            print("  \u26a0  Homebrew error: {}".format(exc))
    else:
        print("  \u26a0  Homebrew not found.")

    print()
    print("  \u2717  Could not install SSH automatically.")
    print("     Install Homebrew from https://brew.sh then run:")
    print("     brew install openssh")                          # spellchecker: disable-line
    print()
    _warn_fallback()
    return False


# Map package-manager binary  →  install command
_LINUX_PKG_MANAGERS: list[tuple[str, list[str]]] = [
    ("apt-get", ["sudo", "apt-get", "install", "-y", "openssh-client"]),   # spellchecker: disable-line
    ("apt",     ["sudo", "apt",     "install", "-y", "openssh-client"]),   # spellchecker: disable-line
    ("dnf",     ["sudo", "dnf",     "install", "-y", "openssh-clients"]),  # spellchecker: disable-line
    ("yum",     ["sudo", "yum",     "install", "-y", "openssh-clients"]),  # spellchecker: disable-line
    ("pacman",  ["sudo", "pacman",  "-S", "--noconfirm", "openssh"]),      # spellchecker: disable-line
    ("zypper",  ["sudo", "zypper",  "--non-interactive", "install", "openssh"]),  # spellchecker: disable-line
    ("apk",     ["sudo", "apk",     "add", "--no-cache", "openssh-client"]),      # spellchecker: disable-line
    ("emerge",  ["sudo", "emerge",  "--ask=n", "net-misc/openssh"]),       # spellchecker: disable-line
]


def _install_linux() -> bool:
    print()
    for mgr, cmd in _LINUX_PKG_MANAGERS:
        if not shutil.which(mgr):
            continue

        print("  \u25b6  Detected package manager: {}".format(mgr))
        print("     Running: {}\n".format(" ".join(cmd)))

        try:
            # noinspection PyTypeChecker
            proc = subprocess.run(cmd)
        except Exception as exc:
            print("  \u26a0  Command failed: {}".format(exc))
            break

        if proc.returncode == 0 and shutil.which("ssh"):
            _print_ok()
            return True

        print("  \u26a0  Install exited with code {}.".format(proc.returncode))
        print("     Try running the command above manually with sudo.\n")
        break
    else:
        # No known package manager found
        print("  \u2717  No supported package manager found.")
        print("     Please install openssh-client with your distro's package manager")  # spellchecker: disable-line
        print("     and re-run CodeAir.\n")

    _warn_fallback()
    return False


# ── Pretty helpers ────────────────────────────────────────────────────────────

def _print_banner() -> None:
    print()
    print("  \u250c" + "\u2500" * 48 + "\u2510")
    print("  \u2502  \u26a0   SSH not found on this system.               \u2502")
    print("  \u2502      SSH is needed for the public tunnel.         \u2502")
    print("  \u2502      Without it CodeAir falls back to LAN only.   \u2502")
    print("  \u2514" + "\u2500" * 48 + "\u2518")
    print()


def _print_ok() -> None:
    print()
    print("  \u2713  SSH installed successfully!\n")


def _warn_fallback() -> None:
    print("  \u2139  Continuing without SSH.")
    print("     CodeAir will use your local LAN IP as a fallback.")
    print("     (Both devices must be on the same Wi-Fi network.)\n")
