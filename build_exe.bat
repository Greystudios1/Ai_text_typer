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

echo [1/4] Installing dependencies from requirements.txt...
%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 goto :fail

set "BUILT_BASE=0"
set "BUILT_V2=0"
set "FAILED_BASE=0"
set "FAILED_V2=0"

echo [2/4] Building available executable targets...

if "%HAS_BASE%"=="1" (
    echo - Building HumanTyper from human_typer_gui.py
    if exist "dist\HumanTyper.exe" (
        del /f /q "dist\HumanTyper.exe" >nul 2>nul
        if exist "dist\HumanTyper.exe" (
            echo   ! Cannot overwrite dist\HumanTyper.exe. Close the running EXE and retry.
            set "FAILED_BASE=1"
            goto :after_base_build
        )
    )

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
:after_base_build

if "%HAS_V2%"=="1" (
    echo - Building HumanTyper_v2 from human_typer_gui_v2.py
    if exist "dist\HumanTyper_v2.exe" (
        del /f /q "dist\HumanTyper_v2.exe" >nul 2>nul
        if exist "dist\HumanTyper_v2.exe" (
            echo   ! Cannot overwrite dist\HumanTyper_v2.exe. Close the running EXE and retry.
            set "FAILED_V2=1"
            goto :after_v2_build
        )
    )

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
:after_v2_build

if "!BUILT_BASE!!BUILT_V2!"=="00" (
    echo No executable targets were built successfully.
    goto :fail
)

echo [3/4] Creating Desktop shortcut(s) for successful builds...
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

echo [4/4] Done.
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
