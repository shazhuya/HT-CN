@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN M1 AUDIT] Python environment missing. Run install first.
  pause
  exit /b 1
)

.venv\Scripts\python.exe scripts\m1_source_audit.py
if errorlevel 1 (
  echo.
  echo [HT-CN M1 AUDIT] SOURCE AUDIT FAILED.
  pause
  exit /b 1
)

echo.
echo [HT-CN M1 AUDIT] SOURCE AUDIT PASSED.
pause
