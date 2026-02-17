# Human-ish Text Typer (Windows GUI)

This project provides a simple desktop GUI that types pasted text into the currently focused input field with configurable timing variability.

> Use this for legitimate automation tasks (demo scripting, accessibility assistance, QA/testing, repetitive data-entry workflows).

## Features

- Paste text and send it to any active input field after a countdown.
- Adjustable typing profile controls:
  - base WPM slider (10–160) plus manual Base WPM entry (any positive value)
  - per-keystroke timing variation
  - burst length (min/max chars)
  - micro pauses and longer thinking pauses
  - typo chance and correction chance
  - warmup effect and fatigue drift
- Start/Stop controls with status display.
- `PyInstaller` build script for Windows `.exe` packaging.
- Automatic Desktop shortcut creation (`HumanTyper.lnk`) after a successful build.
- Dark mode toggle (enabled by default).
- View menu toggles for Advanced mode controls and Debug panel.

## Run locally

```bash
python -m pip install -r requirements.txt
python human_typer_gui.py
```

## Build Windows EXE

### Recommended (double-click or run in cmd)

```bat
build_exe.bat
```

The batch file:

- switches to the script directory automatically (so `requirements.txt` is always found)
- picks `py -3` when available, otherwise falls back to `python`
- stops on install/build errors (no false "Build complete" message on failure)
- creates Desktop shortcut: `%USERPROFILE%\Desktop\HumanTyper.lnk`
- keeps the command window open with `pause` for debugging on both success and failure

### Manual build

```bat
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --onefile --windowed --name HumanTyper human_typer_gui.py
```

Output binary:

- `dist/HumanTyper.exe`


## Repository policy (to avoid branch update errors)

This repo tracks source files only. Generated/binary artifacts are intentionally not committed:

- `dist/`, `build/`, `*.spec`
- `*.ico`, `*.zip`, `*.lnk`

Generate these locally by running `build_exe.bat`. This avoids PR/branch tooling failures like **"Binary files are not supported"** when updating branches.


### Safe git update helper

If your automation currently runs `git pull --ff-only` and fails with:

- `[update-error] Command ['git', 'pull', '--ff-only'] returned non-zero exit status 128.`

use the included wrapper instead:

```bash
python safe_git_update.py
```

The wrapper avoids hard-failing on common local setup issues (no remote configured, no upstream tracking branch, detached HEAD) and prints clear status messages (`[update-ok]`, `[update-skip]`, `[update-error]`).

## Usage

1. Launch the app.
2. Paste the text in the large text box.
3. Set Base WPM using the slider and/or type an exact value in **Manual Base WPM** (manual entry supports uncapped values; slider visual range stays 10–160).
4. Tune the remaining sliders for the typing profile you want.
5. Optionally use **View** menu toggles for Dark mode, Advanced mode, and Debug mode.
6. Set start delay (seconds).
7. Click **Start Typing**.
8. Quickly focus the target field in another application.
9. Press **Stop** to cancel.

## Safety notes

- `PyAutoGUI` fail-safe is enabled: moving mouse to the top-left corner can raise a fail-safe exception.
- Test in a safe text editor first before using in important applications.

## Troubleshooting (Windows)

- **`Could not open requirements file`**: run `build_exe.bat` from this repository and keep `requirements.txt` in the same folder.
- **`No module named PyInstaller`**: run `python -m pip install -r requirements.txt` first, then rerun `build_exe.bat`.
- **Shortcut creation failed**: ensure PowerShell is available and not blocked by local policy.
- If your machine has multiple Python installs, use explicit versioned commands (example: `py -3.12 -m pip install -r requirements.txt`).
