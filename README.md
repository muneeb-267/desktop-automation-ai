# Desktop Automation Using AI

**Group ID:** S26CS089  
**Product Owner:** Mam Saadia Aslam

A no-code desktop assistant that runs **on your own computer**. You type or speak plain English (for example: *Open Chrome and search weather*), and the app:

1. Understands your command (NLP)
2. Looks at the screen to find buttons/text (Computer Vision + OCR)
3. Moves the mouse / types for you (Automation)
4. Saves multi-step workflows and keeps logs in a local database

No cloud account is required for the core app. Everything important is stored locally in SQLite.

---

## What you need

- Windows 10/11 or Linux
- Python 3.10+ (3.12 recommended)
- A microphone (only if you want voice commands)
- Optional for best screen text reading: [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)

---

## Quick start (easiest)

### 1) Open a terminal in this project folder

### 2) Run the setup script (Linux / macOS)

```bash
chmod +x scripts/setup_env.sh
./scripts/setup_env.sh
source .venv/bin/activate
python main.py
```

### 3) Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python main.py
```

### Default login

- **Username:** `demo`
- **Password:** `demo123`

---

## Extra system installs (recommended)

### Linux (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr libportaudio2 portaudio19-dev
```

### Windows

1. Install Python from python.org (tick “Add Python to PATH”).
2. Install Tesseract OCR and note its install path.
3. If needed, set the path in code or PATH environment variable so `tesseract` is found.
4. For microphone support, `PyAudio` may need a wheel matching your Python version.

---

## How to use the app

1. Sign in with `demo` / `demo123`.
2. On the **Dashboard**, type a command and press **Run command**.
3. Or click **Mic**, speak, and wait for the transcript.
4. Watch the **Screen recognition** panel and the **Activity log**.
5. Keep **Dry-run (safe mode)** checked while you practice — the app will plan actions without moving your real mouse.
6. Uncheck dry-run only when you are ready for live automation.
7. Open the **Workflows** tab to replay saved macros, rename/delete them, or **Save last actions** after a successful run.

### Example commands

- `Open notepad`
- `Open Chrome and search weather`
- `Type hello from my project`
- `Click Login`
- `Scroll down 5`
- `Wait 2 seconds`
- `Run workflow Open Notepad Demo`

---

## Project structure

```
main.py                 → start the app
config/default.yaml     → settings
src/db/                 → SQLite database (8 tables)
src/nlp/                → understands English commands
src/speech/             → microphone → text
src/vision/             → screenshot, OCR, template match
src/automation/         → mouse/keyboard actions
src/workflows/          → save / replay macros
src/logging_audit/      → execution logs + screenshot records
src/gui/                → PyQt5 windows
tests/                  → automated tests
data/                   → local database + captures (created on first run)
```

---

## Database tables

`User`, `User_Conf`, `Workflow`, `AutomationRule`, `Task`, `NLP_Command`, `Execution_log`, `Screen_capture`

---

## Run tests

```bash
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pytest -q
```

---

## Safety notes

- **Dry-run is ON by default.** Turn it off only when you intend to control the desktop for real.
- With fail-safe enabled, shove the mouse into a screen corner to abort PyAutoGUI actions.
- The app can control mouse and keyboard — close important work before live demos.

---

## Troubleshooting

| Problem | What to try |
|--------|-------------|
| App won’t start | Activate `.venv`, then `pip install -r requirements.txt` |
| “Could not understand command” | Use clearer phrases like the examples above |
| OCR finds nothing | Install Tesseract; make sure text on screen is large/clear |
| Mic fails | Type instead; install PortAudio / PyAudio |
| spaCy model missing | `python -m spacy download en_core_web_sm` (rules still work without it) |

---

## Academic note

This project follows a 3-tier local architecture:

**Presentation (PyQt5) → Logic (NLP + Vision + Automation) → Data (SQLite)**
