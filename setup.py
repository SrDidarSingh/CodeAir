# Copyright (c) 2025 Didar Singh. All rights reserved.
# Licensed under the CodeAir Source Available License v1.0
# See LICENSE file in the root of this repository.

from setuptools import setup, find_packages

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    # ── Identity ──────────────────────────────────────────────────────────────
    name="codeair",
    version="1.0.0",
    author="Didar Singh",
    author_email="codeairpy@gmail.com",                        # add your email if you want
    url="https://github.com/didarsingh/codeair",

    # ── Description ───────────────────────────────────────────────────────────
    description="✈ Wireless file transfer between PC and Phone via QR code — no cables, no accounts.",
    long_description=long_description,
    long_description_content_type="text/markdown",

    # ── License ───────────────────────────────────────────────────────────────
    license="CodeAir Source Available License v1.0",

    # ── Packages ──────────────────────────────────────────────────────────────
    packages=find_packages(exclude=["tests*", "docs*"]),
    include_package_data=True,

    # ── Python version ────────────────────────────────────────────────────────
    python_requires=">=3.10",

    # ── Dependencies ──────────────────────────────────────────────────────────
    install_requires=[
        "qrcode>=7.0",
    ],

    # ── CLI entry point (lets users run `codeair` directly in terminal) ───────
    entry_points={
        "console_scripts": [
            "codeair=codeair:_menu",
        ],
    },

    # ── PyPI classifiers ──────────────────────────────────────────────────────
    classifiers=[
        # License
        "License :: Other/Proprietary License",

        # Python versions
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",

        # Audience
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",

        # Topic
        "Topic :: Communications :: File Sharing",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
        "Topic :: Internet",

        # Environment
        "Environment :: Console",
        "Operating System :: OS Independent",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",

        # Maturity
        "Development Status :: 4 - Beta",
    ],

    # ── Keywords (helps people find it on PyPI) ───────────────────────────────
    keywords=[
        "qr-code", "file-transfer", "wireless", "phone", "terminal",
        "wifi", "localhost-run", "tunnel", "cli", "mobile",
    ],

    # ── Project links (shows on PyPI sidebar) ─────────────────────────────────
    project_urls={
        "Homepage":    "https://github.com/didarsingh/codeair",
        "Source":      "https://github.com/didarsingh/codeair",
        "Bug Tracker": "https://github.com/didarsingh/codeair/issues",
    },
)