@echo off
setlocal
cd /d %~dp0

if not exist .venv\Scripts\python.exe (
  echo [HT-CN M2 PROSPECTIVE] FAIL: .venv\Scripts\python.exe not found.
  pause
  exit /b 1
)

echo [HT-CN M2 PROSPECTIVE] Updating append-only Type-I prospective registry...
.venv\Scripts\python.exe scripts\m2_type_i_prospective_update.py %*
if errorlevel 1 goto :fail

echo.
echo [HT-CN M2 PROSPECTIVE] ========================================
echo [HT-CN M2 PROSPECTIVE] REGISTRY UPDATE PASSED.
echo [HT-CN M2 PROSPECTIVE] No interim significance test was run.
echo [HT-CN M2 PROSPECTIVE] ========================================
pause
exit /b 0

:fail
echo.
echo [HT-CN M2 PROSPECTIVE] FAILED. Send only the final error block to ChatGPT.
pause
exit /b 1
