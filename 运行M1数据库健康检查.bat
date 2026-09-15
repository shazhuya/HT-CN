@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN M1 HEALTH] Environment missing. Run install script first.
  pause
  exit /b 1
)

.venv\Scripts\python.exe scripts\m1_health_check.py
set EXITCODE=%ERRORLEVEL%

echo.
if not "%EXITCODE%"=="0" (
  echo [HT-CN M1 HEALTH] CHECK FAILED.
  pause
  exit /b %EXITCODE%
)

echo [HT-CN M1 HEALTH] CHECK PASSED.
pause
