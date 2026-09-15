@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN M1 FULL] Environment missing. Run install script first.
  pause
  exit /b 1
)

echo [HT-CN M1 FULL] Starting 50-symbol resumable validation batch for SSE+SZSE...
echo [HT-CN M1 FULL] BSE 920-code securities are temporarily deferred to the continuity adapter.
.venv\Scripts\python.exe scripts\m1_full_market_init.py --limit 50 --max-attempts 5 --retries 2 --sleep 0.25
set EXITCODE=%ERRORLEVEL%

echo.
.venv\Scripts\python.exe scripts\m1_db_status.py

echo.
if not "%EXITCODE%"=="0" (
  echo [HT-CN M1 FULL] Batch stopped with exit code %EXITCODE%.
  echo Re-run this file after any issue is fixed; completed symbols will be skipped.
  pause
  exit /b %EXITCODE%
)
echo [HT-CN M1 FULL] VALIDATION BATCH FINISHED.
pause
