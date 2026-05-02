# Copyright (c) 2025 Didar Singh. All rights reserved.
# Licensed under the CodeAir Source Available License v1.0
# See LICENSE file in the root of this repository.
"""
codeair  —  Wireless file transfer between PC/Laptop and Phone via QR code.

Usage
-----
    import codeair
    codeair()          # launches the menu

Or call directly:
    from codeair import push, pull
    push()
    push(password="hello")
    pull()
"""

import sys
import types

__version__ = "1.0.0"

from .push import push   # noqa: F401
from .pull import pull   # noqa: F401


def _menu():
    print()
    print("  \u2554" + "\u2550" * 42 + "\u2557")
    print("  \u2551                                          \u2551")
    print("  \u2551   \u2708  C O D E A I R   v1.0.0              \u2551")
    print("  \u2551      Wireless File Transfer              \u2551")
    print("  \u2551                                          \u2551")
    print("  \u2560" + "\u2550" * 42 + "\u2563")
    print("  \u2551  [1]  Push  \u2192  PC / Laptop  \u2500\u25b6  Phone    \u2551")
    print("  \u2551  [2]  Pull  \u2190  Phone  \u2500\u25b6  PC / Laptop    \u2551")
    print("  \u2551  [3]  Exit                               \u2551")
    print("  \u255a" + "\u2550" * 42 + "\u255d")

    try:
        choice = input("  Choose (1/2/3): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  Bye!\n")
        return

    if choice == "1":
        push()
    elif choice == "2":
        pull()
    elif choice == "3":
        print("\n  Bye!\n")
    else:
        print("  \u2717  Invalid option.\n")
        _menu()


# Make the module callable:  codeair()  triggers the menu
class _CallableModule(types.ModuleType):
    def __call__(self):
        _menu()


sys.modules[__name__].__class__ = _CallableModule