@echo off
setlocal
cd /d %~dp0

if not exist .venv\Scripts\python.exe (
  echo [HT-CN M2 EXPAND] FAIL: .venv\Scripts\python.exe not found.
  pause
  exit /b 1
)

echo [HT-CN M2 EXPAND] 1/4 Expand resumable QFQ universe...
.venv\Scripts\python.exe scripts\m2_qfq_expand.py
if errorlevel 1 goto :fail

echo.
echo [HT-CN M2 EXPAND] 2/4 Rebuild no-lookahead walk-forward calibration...
.venv\Scripts\python.exe scripts\m2_walk_forward_calibration.py
if errorlevel 1 goto :fail

echo.
echo [HT-CN M2 EXPAND] 3/4 Rebuild purged chronological split...
.venv\Scripts\python.exe scripts\m2_time_split_calibration.py
if errorlevel 1 goto :fail

echo.
echo [HT-CN M2 EXPAND] 4/4 Evaluate Train/Validation quality evidence with Holdout sealed...
.venv\Scripts\python.exe scripts\m2_quality_gate_calibration.py
if errorlevel 1 goto :fail

echo.
echo [HT-CN M2 EXPAND] ========================================
echo [HT-CN M2 EXPAND] SAMPLE EXPANSION + QUALITY CALIBRATION PASSED.
echo [HT-CN M2 EXPAND] Holdout remains sealed.
echo [HT-CN M2 EXPAND] ========================================
pause
exit /b 0

:fail
echo.
echo [HT-CN M2 EXPAND] FAILED. Send only the final error block to ChatGPT.
pause
exit /b 1
