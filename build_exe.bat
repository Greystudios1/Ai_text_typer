@echo off
setlocal EnableExtensions EnableDelayedExpansion

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

echo [0/5] Uninstalling old local builds and deleting old install media...

REM Best-effort stop of previously built executables.
taskkill /f /im HumanTyper.exe >nul 2>nul
taskkill /f /im HumanTyper_v2.exe >nul 2>nul

REM Remove old desktop shortcuts (legacy + current names).
if exist "%USERPROFILE%\Desktop\HumanTyper.lnk" del /f /q "%USERPROFILE%\Desktop\HumanTyper.lnk" >nul 2>nul
if exist "%USERPROFILE%\Desktop\HumanTyper_v2.lnk" del /f /q "%USERPROFILE%\Desktop\HumanTyper_v2.lnk" >nul 2>nul
if exist "%USERPROFILE%\Desktop\HumanTyper v2.lnk" del /f /q "%USERPROFILE%\Desktop\HumanTyper v2.lnk" >nul 2>nul

REM Remove previous build folders and spec files so old media cannot linger.
if exist "build" rmdir /s /q "build" >nul 2>nul
if exist "dist" rmdir /s /q "dist" >nul 2>nul
if exist "HumanTyper.spec" del /f /q "HumanTyper.spec" >nul 2>nul
if exist "HumanTyper_v2.spec" del /f /q "HumanTyper_v2.spec" >nul 2>nul

mkdir dist >nul 2>nul
if not exist "dist" (
    echo Could not create fresh dist folder. Check permissions.
    goto :fail
)

echo [1/5] Installing dependencies from requirements.txt...
%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 goto :fail

set "BUILT_BASE=0"
set "BUILT_V2=0"
set "FAILED_BASE=0"
set "FAILED_V2=0"

echo [2/5] Building available executable targets...

if "%HAS_BASE%"=="1" (
    echo - Building HumanTyper from human_typer_gui.py
    %PYTHON_CMD% -m PyInstaller --noconfirm --onefile --windowed --name HumanTyper human_typer_gui.py
    if errorlevel 1 (
        echo   ! Base build failed.
        set "FAILED_BASE=1"
    ) else (
        if exist "dist\HumanTyper.exe" (
            set "BUILT_BASE=1"
            echo   + Base build succeeded.
        ) else (
            echo   ! Base build finished but dist\HumanTyper.exe was not found.
            set "FAILED_BASE=1"
        )
    )
)

if "%HAS_V2%"=="1" (
    echo - Building HumanTyper_v2 from human_typer_gui_v2.py
    %PYTHON_CMD% -m PyInstaller --noconfirm --onefile --windowed --name HumanTyper_v2 human_typer_gui_v2.py
    if errorlevel 1 (
        echo   ! v2 build failed.
        set "FAILED_V2=1"
    ) else (
        if exist "dist\HumanTyper_v2.exe" (
            set "BUILT_V2=1"
            echo   + v2 build succeeded.
        ) else (
            echo   ! v2 build finished but dist\HumanTyper_v2.exe was not found.
            set "FAILED_V2=1"
        )
    )
)

if "!BUILT_BASE!!BUILT_V2!"=="00" (
    echo No executable targets were built successfully.
    goto :fail
)

echo [3/5] Creating Desktop shortcut(s) for successful builds...
if "!BUILT_BASE!"=="1" (
    set "SHORTCUT_TARGET=%~dp0dist\HumanTyper.exe"
    set "SHORTCUT_PATH=%USERPROFILE%\Desktop\HumanTyper.lnk"
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut('!SHORTCUT_PATH!'); $s.TargetPath='!SHORTCUT_TARGET!'; $s.WorkingDirectory='%~dp0dist'; $s.IconLocation='!SHORTCUT_TARGET!,0'; $s.Save()"
    if errorlevel 1 (
        echo   ! Failed to create shortcut: !SHORTCUT_PATH!
        goto :fail
    )
)
if "!BUILT_V2!"=="1" (
    set "SHORTCUT_TARGET=%~dp0dist\HumanTyper_v2.exe"
    set "SHORTCUT_PATH=%USERPROFILE%\Desktop\HumanTyper_v2.lnk"
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut('!SHORTCUT_PATH!'); $s.TargetPath='!SHORTCUT_TARGET!'; $s.WorkingDirectory='%~dp0dist'; $s.IconLocation='!SHORTCUT_TARGET!,0'; $s.Save()"
    if errorlevel 1 (
        echo   ! Failed to create shortcut: !SHORTCUT_PATH!
        goto :fail
    )
)

echo [4/5] Cleaning temporary build artifacts...
if exist "build" rmdir /s /q "build" >nul 2>nul
if exist "HumanTyper.spec" del /f /q "HumanTyper.spec" >nul 2>nul
if exist "HumanTyper_v2.spec" del /f /q "HumanTyper_v2.spec" >nul 2>nul

echo [5/5] Done.
if "!BUILT_BASE!"=="1" echo Build complete. EXE is in dist\HumanTyper.exe
if "!BUILT_V2!"=="1" echo Build complete. EXE is in dist\HumanTyper_v2.exe
if "!BUILT_BASE!"=="1" echo Desktop shortcut created: %USERPROFILE%\Desktop\HumanTyper.lnk
if "!BUILT_V2!"=="1" echo Desktop shortcut created: %USERPROFILE%\Desktop\HumanTyper_v2.lnk
if "!FAILED_BASE!"=="1" echo Warning: base target failed to build.
if "!FAILED_V2!"=="1" echo Warning: v2 target failed to build.
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
