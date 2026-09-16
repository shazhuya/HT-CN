@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN M2 WF] Environment missing. Run install script first.
  pause
  exit /b 1
)

echo [HT-CN M2 WF] Running event-driven no-lookahead forming calibration...
.venv\Scripts\python.exe scripts\m2_walk_forward_calibration.py
if errorlevel 1 goto :fail

echo.
echo [HT-CN M2 WF] ========================================
echo [HT-CN M2 WF] WALK-FORWARD CALIBRATION PASSED.
echo [HT-CN M2 WF] JSON: artifacts\calibration\m2-forming-walk-forward.json
echo [HT-CN M2 WF] CSV : artifacts\calibration\m2-forming-walk-forward.csv
echo [HT-CN M2 WF] ========================================
pause
exit /b 0

:fail
echo.
echo [HT-CN M2 WF] FAILED. Send only the final error block to ChatGPT.
pause
exit /b 1
