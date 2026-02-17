# Human-ish Text Typer (Windows GUI)

Two GUI apps are included:

- **Base app**: `human_typer_gui.py` (plain text)
- **v2 app**: `human_typer_gui_v2.py` (formatted text + safety controls + logging)

## v2 major capabilities

### Formatted input
- `**bold**`
- `*italic*` or `_italic_`
- Bullets with `- ` or `* `
- Line breaks

### Safety and control
- Stop button
- **Pause/Resume** button
- Keyboard shortcuts: **F8 start**, **F9 pause/resume**, **F10 stop**
- Global emergency stop: **Ctrl+Alt+Esc** (when `pynput` is available)
- “Armed” state with 3-2-1 style countdown before typing
- Optional active-window guard/title display
- **Dark mode toggle** (dark/light)
- **Power user mode** toggle (shows debug panel + event log area)

### Reproducibility + profiles
- **Use seed** toggle (default ON with standard seed `12345`)
- Seed field
- Randomize seed button
- If Use seed is OFF, each run uses a stochastic auto-seed
- Seed included in run summary
- Presets: Careful, Fast, Fatigued, No typos
- Save/load profile JSON

### Observability
- Event log toggle
- Run summary with:
  - effective WPM
  - chars typed
  - typo/correction counts
  - pause totals
  - run duration
- Dry run mode (simulate only, no key output)
- Progress indicator (`Typed X / Y chars`)

### Robust key output
v2 includes a translation layer for uppercase and shift-modified symbols (`: ? { }` etc.) and handles newline/tab as named keys.

### In-app update helper
- **Update from Git** button runs `git pull --ff-only` and reports output in the log panel.

## Run locally

```bash
python -m pip install -r requirements.txt
python human_typer_gui.py
python human_typer_gui_v2.py
```

## Build Windows EXE

Use:

```bat
build_exe.bat
```

It auto-detects available sources and builds base, v2, or both.

Before each build, the script now automatically removes old local build media (previous `dist/`, `build/`, `.spec` files), deletes old desktop shortcuts, and attempts to terminate old running `HumanTyper*.exe` processes so stale versions are uninstalled/cleaned up first.

## Notes

- `PyAutoGUI` fail-safe is enabled; moving mouse to top-left can trigger fail-safe.
- Test in a safe editor first.
