@echo off
setlocal EnableExtensions

REM Ensure script runs relative to its own folder (fixes missing requirements.txt when launched elsewhere)
cd /d "%~dp0"

set "PYTHON_CMD="
where py >nul 2>nul
if %ERRORLEVEL%==0 (
    set "PYTHON_CMD=py -3"
) else (
    set "PYTHON_CMD=python"
)

echo [1/3] Installing dependencies from requirements.txt...
%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo [2/3] Building executable with PyInstaller...
%PYTHON_CMD% -m PyInstaller --noconfirm --onefile --windowed --name HumanTyper human_typer_gui.py
if errorlevel 1 goto :fail

echo [3/3] Done.
if exist "dist\HumanTyper.exe" (
    echo Build complete. EXE is in dist\HumanTyper.exe
    exit /b 0
)

echo Build command finished but dist\HumanTyper.exe was not found.
exit /b 1

:fail
echo Build failed. Please review the error output above.
exit /b 1
