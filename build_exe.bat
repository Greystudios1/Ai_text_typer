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

set "HAS_BASE=0"
set "HAS_V2=0"
if exist "human_typer_gui.py" set "HAS_BASE=1"
if exist "human_typer_gui_v2.py" set "HAS_V2=1"

if "%HAS_BASE%"=="0" if "%HAS_V2%"=="0" (
    echo No build target found. Expected human_typer_gui.py and/or human_typer_gui_v2.py.
    goto :fail
)

echo [1/4] Installing dependencies from requirements.txt...
%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo [2/4] Building available executable targets...
if "%HAS_BASE%"=="1" (
    echo - Building HumanTyper from human_typer_gui.py
    %PYTHON_CMD% -m PyInstaller --noconfirm --onefile --windowed --name HumanTyper human_typer_gui.py
    if errorlevel 1 goto :fail
)
if "%HAS_V2%"=="1" (
    echo - Building HumanTyper_v2 from human_typer_gui_v2.py
    %PYTHON_CMD% -m PyInstaller --noconfirm --onefile --windowed --name HumanTyper_v2 human_typer_gui_v2.py
    if errorlevel 1 goto :fail
)

if "%HAS_BASE%"=="1" if not exist "dist\HumanTyper.exe" (
    echo Build command finished but dist\HumanTyper.exe was not found.
    goto :fail
)
if "%HAS_V2%"=="1" if not exist "dist\HumanTyper_v2.exe" (
    echo Build command finished but dist\HumanTyper_v2.exe was not found.
    goto :fail
)

echo [3/4] Creating Desktop shortcut(s)...
if "%HAS_BASE%"=="1" (
    set "SHORTCUT_TARGET=%~dp0dist\HumanTyper.exe"
    set "SHORTCUT_PATH=%USERPROFILE%\Desktop\HumanTyper.lnk"
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath='%SHORTCUT_TARGET%'; $s.WorkingDirectory='%~dp0dist'; $s.IconLocation='%SHORTCUT_TARGET%,0'; $s.Save()"
    if errorlevel 1 goto :fail
)
if "%HAS_V2%"=="1" (
    set "SHORTCUT_TARGET=%~dp0dist\HumanTyper_v2.exe"
    set "SHORTCUT_PATH=%USERPROFILE%\Desktop\HumanTyper_v2.lnk"
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath='%SHORTCUT_TARGET%'; $s.WorkingDirectory='%~dp0dist'; $s.IconLocation='%SHORTCUT_TARGET%,0'; $s.Save()"
    if errorlevel 1 goto :fail
)

echo [4/4] Done.
if "%HAS_BASE%"=="1" echo Build complete. EXE is in dist\HumanTyper.exe
if "%HAS_V2%"=="1" echo Build complete. EXE is in dist\HumanTyper_v2.exe
if "%HAS_BASE%"=="1" echo Desktop shortcut created: %USERPROFILE%\Desktop\HumanTyper.lnk
if "%HAS_V2%"=="1" echo Desktop shortcut created: %USERPROFILE%\Desktop\HumanTyper_v2.lnk
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
