@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN M6.2] ERROR: .venv not found.
  echo [HT-CN M6.2] No M1/product state has been changed.
  exit /b 1
)

echo ============================================================
echo HT-CN M6.2 REAL PRIVATE-M1 FINAL CLOSEOUT
echo.
echo ONE ACTION ONLY:
echo   Project OS check
echo   ^> frozen Phase23/21 real closeout
echo   ^> M6.2 end-of-run main identity audit
echo   ^> one self-verifying evidence ZIP
echo ============================================================
echo.

echo [0/3] Verify Project OS current state
".venv\Scripts\python.exe" -u "scripts\project_state.py"
if errorlevel 1 (
  echo [HT-CN M6.2] BLOCKED: Project OS state invalid.
  exit /b %ERRORLEVEL%
)

echo.
echo [1/3] Run frozen M5 Phase23/21 real current-market closeout
call "运行HT-CN主线真实A股最终验收.bat"
set "M5_EXIT=%ERRORLEVEL%"
if not "%M5_EXIT%"=="0" (
  echo [HT-CN M6.2] BLOCKED: underlying M5 real closeout failed.
  exit /b %M5_EXIT%
)

echo.
echo [2/3] Re-check remote main and independently bind every identity
".venv\Scripts\python.exe" -u "scripts\m6_private_m1_closeout.py"
set "M6_EXIT=%ERRORLEVEL%"
if not "%M6_EXIT%"=="0" (
  echo [HT-CN M6.2] BLOCKED: M6.2 identity/evidence closeout failed.
  echo Report: artifacts\reports\m6-private-m1-closeout.json
  exit /b %M6_EXIT%
)

echo.
echo [3/3] COMPLETE
echo ============================================================
echo HT-CN M6.2 PRIVATE-M1 FULL CLOSEOUT READY
echo Upload ONLY this file:
echo artifacts\reports\htcn-m6-private-m1-closeout-evidence.zip
echo ============================================================
exit /b 0
