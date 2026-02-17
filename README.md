# Human-ish Text Typer (Windows GUI)

This project provides desktop GUIs that type pasted text into the currently focused input field with configurable timing variability.

> Use this for legitimate automation tasks (demo scripting, accessibility assistance, QA/testing, repetitive data-entry workflows).

## Versions

- **Base app**: `human_typer_gui.py` (plain text typing)
- **v2 app**: `human_typer_gui_v2.py` (formatted text support)

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
- Automatic Desktop shortcut creation after a successful build.

### v2 formatting support

`human_typer_gui_v2.py` accepts lightweight markdown-style formatting:

- `**bold**`
- `*italic*` or `_italic_`
- Bullet lines beginning with `- ` or `* `
- Line breaks

It can optionally use rich-text shortcuts while typing:

- Bold: `Ctrl+B`
- Italic: `Ctrl+I`
- Bullet list: `Ctrl+Shift+8`

If rich shortcuts are disabled, bullets are typed as plain `- `.

## Run locally

```bash
python -m pip install -r requirements.txt
python human_typer_gui.py
python human_typer_gui_v2.py
```

## Build Windows EXE

### Recommended (double-click or run in cmd)

```bat
build_exe.bat
```

The batch file:

- switches to the script directory automatically (so `requirements.txt` is always found)
- picks `py -3` when available, otherwise falls back to `python`
- detects available app sources and builds whichever exists:
  - `human_typer_gui.py` -> `dist\HumanTyper.exe`
  - `human_typer_gui_v2.py` -> `dist\HumanTyper_v2.exe`
- if one target fails (for example an EXE is locked), it still builds the other target when possible
- fails only when no target was built successfully
- creates matching Desktop shortcuts only for successful builds:
  - `%USERPROFILE%\Desktop\HumanTyper.lnk`
  - `%USERPROFILE%\Desktop\HumanTyper_v2.lnk`
- keeps the command window open with `pause` for debugging on both success and failure

### Manual build

```bat
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --onefile --windowed --name HumanTyper human_typer_gui.py
python -m PyInstaller --noconfirm --onefile --windowed --name HumanTyper_v2 human_typer_gui_v2.py
```

## Usage

1. Launch either app.
2. Paste the text in the text box.
3. Tune the sliders for the typing profile you want.
4. Set start delay (seconds).
5. Click **Start Typing**.
6. Quickly focus the target field in another application.
7. Press **Stop** to cancel.

## Safety notes

- `PyAutoGUI` fail-safe is enabled: moving mouse to the top-left corner can raise a fail-safe exception.
- Test in a safe text editor first before using in important applications.

## Troubleshooting (Windows)

- **`Could not open requirements file`**: run `build_exe.bat` from this repository and keep `requirements.txt` in the same folder.
- **`No module named PyInstaller`**: run `python -m pip install -r requirements.txt` first, then rerun `build_exe.bat`.
- **Shortcut creation failed**: ensure PowerShell is available and not blocked by local policy.
- If your machine has multiple Python installs, use explicit versioned commands (example: `py -3.12 -m pip install -r requirements.txt`).
