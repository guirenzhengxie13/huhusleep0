@echo off
setlocal
cd /d "%~dp0"
python "%~dp0start_debug.py"
echo.
echo HuhuSleep debug launcher finished. You can close this window after the browser opens.
pause

