@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN M1 LIVE] Python environment not found. Run install script first.
  pause
  exit /b 1
)

echo [HT-CN M1 LIVE] Syncing Python dependencies...
.venv\Scripts\python.exe -m pip install -e ".[dev]"
if errorlevel 1 goto :error

echo.
echo [HT-CN M1 LIVE] Running real A-share provider smoke test...
.venv\Scripts\python.exe scripts\m1_live_smoke.py
if errorlevel 1 goto :error

echo.
echo [HT-CN M1 LIVE] REAL DATA TEST PASSED.
pause
exit /b 0

:error
echo.
echo [HT-CN M1 LIVE] TEST FAILED. Send the last error lines to ChatGPT.
pause
exit /b 1
