@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN M1 ACCEPT] Environment missing. Run install script first.
  pause
  exit /b 1
)

echo [HT-CN M1 ACCEPT] 1/5 Full QA: Python + Web build + API + Playwright...
.venv\Scripts\python.exe scripts\qa_local.py
if errorlevel 1 goto :fail

echo.
echo [HT-CN M1 ACCEPT] 2/5 Local database health...
.venv\Scripts\python.exe scripts\m1_health_check.py
if errorlevel 1 goto :fail

echo.
echo [HT-CN M1 ACCEPT] 3/5 Smart incremental update / market delta...
.venv\Scripts\python.exe scripts\m1_daily_update.py --limit 0 --sleep 0.02
if errorlevel 1 goto :fail

echo.
echo [HT-CN M1 ACCEPT] 4/5 QFQ live pilot with retry + provider failover...
.venv\Scripts\python.exe scripts\m1_adjustment_pilot.py
if errorlevel 1 goto :fail

echo.
echo [HT-CN M1 ACCEPT] 5/5 Coverage and final status...
.venv\Scripts\python.exe scripts\m1_coverage_report.py
if errorlevel 1 goto :fail
.venv\Scripts\python.exe scripts\m1_db_status.py
if errorlevel 1 goto :fail

echo.
echo [HT-CN M1 ACCEPT] ========================================
echo [HT-CN M1 ACCEPT] ALL M1 ACCEPTANCE CHECKS PASSED.
echo [HT-CN M1 ACCEPT] ========================================
pause
exit /b 0

:fail
echo.
echo [HT-CN M1 ACCEPT] FAILED. Send only the final error block to ChatGPT.
pause
exit /b 1
