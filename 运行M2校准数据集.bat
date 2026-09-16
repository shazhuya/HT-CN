@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN M2 CAL] Python environment missing. Run install script first.
  pause
  exit /b 1
)

echo [HT-CN M2 CAL] Building completed-case calibration dataset...
.venv\Scripts\python.exe scripts\m2_case_calibration_dataset.py
if errorlevel 1 goto :fail

echo.
echo [HT-CN M2 CAL] ========================================
echo [HT-CN M2 CAL] CALIBRATION DATASET PASSED.
echo [HT-CN M2 CAL] JSON: artifacts\calibration\m2-case-calibration.json
echo [HT-CN M2 CAL] CSV : artifacts\calibration\m2-case-calibration.csv
echo [HT-CN M2 CAL] This dataset separates Carney identity from later outcome.
echo [HT-CN M2 CAL] Send the final summary block for the next walk-forward stage.
echo [HT-CN M2 CAL] ========================================
pause
exit /b 0

:fail
echo.
echo [HT-CN M2 CAL] FAILED. Send the final error block.
pause
exit /b 1
