# Human-ish Text Typer (Windows GUI)

This project provides a simple desktop GUI that types pasted text into the currently focused input field with configurable timing variability.

> Use this for legitimate automation tasks (demo scripting, accessibility assistance, QA/testing, repetitive data-entry workflows).

## Features

- Paste text and send it to any active input field after a countdown.
- Adjustable typing profile controls:
  - base WPM
  - per-keystroke timing variation
  - burst length (min/max chars)
  - micro pauses and longer thinking pauses
  - typo chance and correction chance
  - warmup effect and fatigue drift
- Start/Stop controls with status display.
- `PyInstaller` build script for Windows `.exe` packaging.

## Run locally

```bash
python -m pip install -r requirements.txt
python human_typer_gui.py
```

## Build Windows EXE

On Windows:

```bat
build_exe.bat
```

Or manually:

```bat
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --onefile --windowed --name HumanTyper human_typer_gui.py
```

Output binary:

- `dist/HumanTyper.exe`

## Usage

1. Launch the app.
2. Paste the text in the large text box.
3. Tune the sliders for the typing profile you want.
4. Set start delay (seconds).
5. Click **Start Typing**.
6. Quickly focus the target field in another application.
7. Press **Stop** to cancel.

## Safety notes

- `PyAutoGUI` fail-safe is enabled: moving mouse to the top-left corner can raise a fail-safe exception.
- Test in a safe text editor first before using in important applications.
