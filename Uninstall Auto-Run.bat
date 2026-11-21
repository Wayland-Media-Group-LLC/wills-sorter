@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0DownloadsOrganizer.ps1" -Uninstall
echo.
pause
