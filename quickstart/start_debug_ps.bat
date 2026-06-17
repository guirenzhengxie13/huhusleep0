@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_debug.ps1"
echo.
echo HuhuSleep debug launcher finished. You can close this window after the browser opens.
pause

