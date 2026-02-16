@echo off
setlocal EnableExtensions

REM Ensure script runs relative to its own folder
cd /d "%~dp0"

set "PYTHON_CMD="
where py >nul 2>nul
if %ERRORLEVEL%==0 (
    set "PYTHON_CMD=py -3"
) else (
    set "PYTHON_CMD=python"
)

echo [1/4] Installing dependencies from requirements.txt...
%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo [2/4] Building executable with PyInstaller...
%PYTHON_CMD% -m PyInstaller --noconfirm --onefile --windowed --name HumanTyper human_typer_gui.py
if errorlevel 1 goto :fail

if not exist "dist\HumanTyper.exe" (
    echo Build command finished but dist\HumanTyper.exe was not found.
    goto :fail
)

echo [3/4] Creating Desktop shortcut...
set "SHORTCUT_TARGET=%~dp0dist\HumanTyper.exe"
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\HumanTyper.lnk"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath='%SHORTCUT_TARGET%'; $s.WorkingDirectory='%~dp0dist'; $s.IconLocation='%SHORTCUT_TARGET%,0'; $s.Save()"
if errorlevel 1 goto :fail

echo [4/4] Done.
echo Build complete. EXE is in dist\HumanTyper.exe
echo Desktop shortcut created: %SHORTCUT_PATH%
echo.
echo Debug window intentionally left open.
pause
exit /b 0

:fail
echo.
echo Build/install failed. Please review the error output above.
echo Debug window intentionally left open.
pause
exit /b 1
