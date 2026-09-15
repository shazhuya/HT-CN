@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN QA] ERROR: Python virtual environment not found.
  echo [HT-CN QA] Run install script first.
  pause
  exit /b 2
)

.venv\Scripts\python.exe scripts\qa_local.py
if errorlevel 1 (
  echo.
  echo [HT-CN QA] TEST FAILED. Send the last error lines to ChatGPT.
  pause
  exit /b 1
)

echo.
echo [HT-CN QA] M0 TEST PASSED.
pause
exit /b 0
