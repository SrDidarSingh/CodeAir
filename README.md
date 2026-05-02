<div align="center">

```
 ██████╗ ██████╗ ██████╗ ███████╗ █████╗ ██╗██████╗
██╔════╝██╔═══██╗██╔══██╗██╔════╝██╔══██╗██║██╔══██╗
██║     ██║   ██║██║  ██║█████╗  ███████║██║██████╔╝
██║     ██║   ██║██║  ██║██╔══╝  ██╔══██║██║██╔══██╗
╚██████╗╚██████╔╝██████╔╝███████╗██║  ██║██║██║  ██║
 ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝
```

**Wireless file transfer between your PC and Phone — via QR code.**  
No cables. No accounts. No cloud. Just scan and go.

[![Python](https://img.shields.io/badge/python-3.10+-00ffcc?style=flat-square&logo=python&logoColor=black)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-00ffcc?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-00ffcc?style=flat-square)]()

</div>

---

## ✈ What is CodeAir?

CodeAir turns your terminal into a file transfer station.  
Run it, scan the QR code with your phone — done.

- **Push** files from PC → Phone (over the internet via public URL)
- **Pull** files from Phone → PC (lands straight on your Desktop)
- No sign-up, no config, no third-party apps
- Works anywhere in the world via `localhost.run` SSH tunnel

---

## ⚡ Install

```bash
pip install codeair
```

That's it. `qrcode` is included automatically.

---

## 🚀 Usage

```python
import codeair
codeair()
```

A menu appears:

```
  ╔══════════════════════════════════════════╗
  ║   ✈  C O D E A I R   v1.0.0              ║
  ║      Wireless File Transfer              ║
  ╠══════════════════════════════════════════╣
  ║  [1]  Push  →  PC / Laptop  ─▶  Phone    ║
  ║  [2]  Pull  ←  Phone  ─▶  PC / Laptop    ║
  ║  [3]  Exit                               ║
  ╚══════════════════════════════════════════╝
```

---

## 📤 Push — PC → Phone

Send anything from your PC to any phone, anywhere in the world.

| Option | What it does |
|--------|-------------|
| `[1]` Current `.py` file | Auto-detects and serves the script you're running |
| `[2]` Custom text | Type/paste text → phone downloads as `.txt` |
| `[3]` Send by path | Type any file or folder path → served instantly |
| `[4]` Whole project | Recursively zips your entire project (skips `.venv`, `__pycache__`, `.git`) |

**Password protection:**
```python
from codeair import push
push(password="secret123")
# Phone must enter the password before the download button appears
```

**How it works:**
1. A local HTTP server starts on your machine
2. An SSH tunnel via `localhost.run` gives you a **public HTTPS URL**
3. A QR code prints in your terminal
4. Phone scans it → download page opens in browser
5. Press `ENTER` → server shuts down, QR expires instantly

> No same Wi-Fi required. Send to anyone, anywhere.

---

## 📥 Pull — Phone → PC

Receive any file from a phone directly to your Desktop.

```
  Scan with your phone camera → tap Choose File → Send
```

| Received file type | What happens |
|-------------------|-------------|
| `.py` `.txt` `.md` etc. | Printed live in terminal + option to save |
| `.zip` | Auto-extracted into a folder on Desktop |
| Images, PDFs, anything else | Saved directly to `~/Desktop/` |

---

## 🌐 Public Tunnel

CodeAir uses **[localhost.run](https://localhost.run)** — a free, zero-signup SSH tunnel:

```bash
ssh -R 80:localhost:<port> nokey@localhost.run
```

This gives you a live public URL like:
```
https://a3f91bc04d2e.lhr.life
```

Which you can screenshot, share via chat, or print as a QR — and your friend scans it from their phone anywhere in the world.

If the tunnel fails (no internet / SSH unavailable), CodeAir **automatically falls back** to your local LAN IP so it still works on the same Wi-Fi.

---

## 🗂 Project Structure

```
codeair/
├── codeair/
│   ├── __init__.py    ← callable module  (import codeair; codeair())
│   ├── push.py        ← PC → Phone logic
│   ├── pull.py        ← Phone → PC logic
│   ├── tunnel.py      ← localhost.run SSH tunnel
│   └── utils.py       ← QR, LAN IP, file helpers
├── main.py
├── setup.py
└── README.md
```

---

## 📋 Requirements

- Python **3.10+**
- `qrcode` (auto-installed with pip)
- `ssh` on your system (pre-installed on macOS and Linux; Windows: use Git Bash or WSL)
- For public links: internet connection

---

## 🔒 Security

- **Password protection** available on every push
- Tunnel closes the moment you press `ENTER` — URL is dead instantly
- Files are never stored on any server — direct stream from your machine
- No account, no data retained by any third party

---

## 💡 Tips

```python
# Use directly without the menu
from codeair import push, pull

push()                    # guided wizard
push(password="hello")    # password-protected
pull()                    # wait for phone upload
```

```bash
# Or just run main.py
python main.py
```

---

<div align="center">

### **✈ CodeAir**
*An Independent Project By **Didar Singh***\
*Scan. Transfer. Done.*

</div>