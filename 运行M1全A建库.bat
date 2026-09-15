@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN M1 FULL] Environment missing. Run install script first.
  pause
  exit /b 1
)

echo [HT-CN M1 FULL] Starting resumable full-market initialization.
echo [HT-CN M1 FULL] You may press Ctrl+C at any time. Re-run later to resume.
.venv\Scripts\python.exe scripts\m1_full_market_init.py --limit 0 --max-attempts 5 --retries 2 --sleep 0.25
set EXITCODE=%ERRORLEVEL%

echo.
.venv\Scripts\python.exe scripts\m1_db_status.py

echo.
if "%EXITCODE%"=="130" (
  echo [HT-CN M1 FULL] Safely interrupted. Re-run this file to resume.
  pause
  exit /b 0
)
if not "%EXITCODE%"=="0" (
  echo [HT-CN M1 FULL] Process exited with code %EXITCODE%.
  pause
  exit /b %EXITCODE%
)
echo [HT-CN M1 FULL] FULL-MARKET RUN FINISHED.
pause
