@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (
    py -3 "%~dp0ysm_metadata_editor.py"
) else (
    python "%~dp0ysm_metadata_editor.py"
)

if errorlevel 1 (
    echo.
    echo Failed to start the YSM metadata editor. Check that Python 3 is installed.
    pause
)
