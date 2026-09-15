@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN M1] Python environment missing. Run install script first.
  pause
  exit /b 1
)

.venv\Scripts\python.exe -m pytest tests\data -q
if errorlevel 1 (
  echo.
  echo [HT-CN M1] TEST FAILED. Send the last error lines to ChatGPT.
  pause
  exit /b 1
)

echo.
echo [HT-CN M1] DATA ENGINE TESTS PASSED.
pause
