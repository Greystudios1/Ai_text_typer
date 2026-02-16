@echo off
setlocal

python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --onefile --windowed --name HumanTyper human_typer_gui.py

echo Build complete. EXE is in dist\HumanTyper.exe
pause
