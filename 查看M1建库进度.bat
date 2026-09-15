@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN M1 STATUS] Environment missing. Run install script first.
  pause
  exit /b 1
)

.venv\Scripts\python.exe scripts\m1_db_status.py
pause
