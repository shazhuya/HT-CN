@echo off
setlocal
cd /d %~dp0

echo [HT-CN M2 SPLIT] Building purged chronological train-validation-holdout calibration...

if not exist .venv\Scripts\python.exe (
  echo [HT-CN M2 SPLIT] FAIL: .venv\Scripts\python.exe not found.
  pause
  exit /b 1
)

.venv\Scripts\python.exe scripts\m2_time_split_calibration.py
if errorlevel 1 (
  echo.
  echo [HT-CN M2 SPLIT] CALIBRATION FAILED.
  pause
  exit /b 1
)

echo.
echo [HT-CN M2 SPLIT] ========================================
echo [HT-CN M2 SPLIT] TIME-SPLIT CALIBRATION PASSED.
echo [HT-CN M2 SPLIT] Holdout outcome remains sealed.
echo [HT-CN M2 SPLIT] ========================================
pause
