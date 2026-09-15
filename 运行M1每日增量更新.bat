@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN M1 DAILY] Environment missing. Run install script first.
  pause
  exit /b 1
)

.venv\Scripts\python.exe scripts\m1_daily_update.py --limit 0 --sleep 0.15
set EXITCODE=%ERRORLEVEL%

echo.
.venv\Scripts\python.exe scripts\m1_db_status.py

echo.
if "%EXITCODE%"=="130" (
  echo [HT-CN M1 DAILY] Safely interrupted.
  pause
  exit /b 0
)
if not "%EXITCODE%"=="0" (
  echo [HT-CN M1 DAILY] Update completed with failures. Exit code %EXITCODE%.
  pause
  exit /b %EXITCODE%
)

echo [HT-CN M1 DAILY] UPDATE PASSED.
pause
