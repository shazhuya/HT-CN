@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN M1 ADJ] Environment missing. Run install script first.
  pause
  exit /b 1
)

.venv\Scripts\python.exe scripts\m1_adjustment_pilot.py
set EXITCODE=%ERRORLEVEL%

echo.
if not "%EXITCODE%"=="0" (
  echo [HT-CN M1 ADJ] PILOT FAILED.
  pause
  exit /b %EXITCODE%
)

echo [HT-CN M1 ADJ] PILOT PASSED.
pause
