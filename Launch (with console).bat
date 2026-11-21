@echo off
REM Starts the sorter with a console, so any error is visible.
cd /d "%~dp0"
python src\app.py
if errorlevel 1 (
    echo.
    echo Could not start. Make sure Python 3.9+ is installed from python.org
    echo with "Add python.exe to PATH" ticked.
)
pause
