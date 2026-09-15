@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN M2 ACCEPT] Environment missing. Run install script first.
  pause
  exit /b 1
)

echo [HT-CN M2 ACCEPT] 1/3 Deterministic QA + Web build + API + fixture/live browser acceptance...
.venv\Scripts\python.exe scripts\qa_local.py
if errorlevel 1 goto :fail

echo.
echo [HT-CN M2 ACCEPT] 2/3 Real local QFQ harmonic scan...
.venv\Scripts\python.exe scripts\m2_local_accept.py
if errorlevel 1 goto :fail

echo.
echo [HT-CN M2 ACCEPT] 3/3 Local market database health...
.venv\Scripts\python.exe scripts\m1_health_check.py
if errorlevel 1 goto :fail

echo.
echo [HT-CN M2 ACCEPT] ========================================
echo [HT-CN M2 ACCEPT] M2 WORKBENCH ACCEPTANCE PASSED.
echo [HT-CN M2 ACCEPT] Fixture screenshot: artifacts\screenshots\m2-harmonic-workbench-fixture.png
echo [HT-CN M2 ACCEPT] LIVE screenshot   : artifacts\screenshots\m2-harmonic-workbench-live.png
echo [HT-CN M2 ACCEPT] Start app with: 启动HT-CN.bat
echo [HT-CN M2 ACCEPT] ========================================
pause
exit /b 0

:fail
echo.
echo [HT-CN M2 ACCEPT] FAILED. Send only the final error block to ChatGPT.
pause
exit /b 1
