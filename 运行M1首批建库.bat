@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo [HT-CN M1 INIT] Building persistent pilot A-share database...
.venv\Scripts\python.exe scripts\m1_pilot_init.py
if errorlevel 1 (
  echo.
  echo [HT-CN M1 INIT] FAILED. Send the last error lines to ChatGPT.
  pause
  exit /b 1
)
echo.
echo [HT-CN M1 INIT] PILOT DATABASE PASSED.
pause
