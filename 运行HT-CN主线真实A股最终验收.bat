@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN] ERROR: .venv not found.
  echo [HT-CN] No M1/product state has been changed.
  exit /b 1
)

echo ============================================================
echo HT-CN MAIN REAL A-SHARE FINAL CLOSEOUT
echo.
echo Single action: preflight first, then daily close + Phase19,
echo then exact latest Phase21 structural/browser closeout.
echo.
echo Phase23 preflight is read-only for Git/M1/product/research state.
echo It never git-pulls, installs dependencies, updates M1, or writes M4 evidence.
echo ============================================================
echo.

echo [0/7] Read-only safety preflight BEFORE any M1/product mutation
".venv\Scripts\python.exe" -u "scripts\m5_real_closeout_preflight.py"
set "PREFLIGHT_EXIT=%ERRORLEVEL%"
if not "%PREFLIGHT_EXIT%"=="0" (
  echo.
  echo [HT-CN] BLOCKED BY PREFLIGHT. No daily close / Phase19 was started.
  echo Report: artifacts\reports\m5-real-closeout-preflight.json
  exit /b %PREFLIGHT_EXIT%
)

echo.
echo [1/7] Run daily close product/research pipeline + verified Phase19 delivery
call "运行HT-CN每日收盘并生成便携复盘包.bat"
set "DAILY_EXIT=%ERRORLEVEL%"
if not "%DAILY_EXIT%"=="0" (
  echo [HT-CN] BLOCKED: daily close / Phase19 delivery failed.
  exit /b %DAILY_EXIT%
)

echo.
echo [2/7] Verify current main + Phase9 + Phase19 structural binding
".venv\Scripts\python.exe" -u "scripts\m5_main_real_closeout.py"
if errorlevel 1 exit /b %ERRORLEVEL%

echo.
echo [3/7] Prepare exact latest Phase19 workspace for Chromium
".venv\Scripts\python.exe" -u "scripts\m5_prepare_main_real_browser_audit.py"
if errorlevel 1 exit /b %ERRORLEVEL%

echo.
echo [4/7] Run dynamic Chromium audit over every transported candidate
pushd "apps\web"
call npx playwright test tests/main-real-portable-delivery.spec.ts --reporter=list
set "BROWSER_EXIT=%ERRORLEVEL%"
popd
if not "%BROWSER_EXIT%"=="0" (
  echo [HT-CN] BLOCKED: Chromium audit failed. exit=%BROWSER_EXIT%
  echo Phase23 preflight already verified installed Playwright/Chromium,
  echo so inspect runtime/browser evidence rather than installing during closeout.
  exit /b %BROWSER_EXIT%
)

echo.
echo [5/7] Independently verify browser evidence and screenshot hashes
".venv\Scripts\python.exe" -u "scripts\m5_verify_main_real_browser_evidence.py"
if errorlevel 1 exit /b %ERRORLEVEL%

echo.
echo [6/7] Finalize structural + browser identity-bound closeout
".venv\Scripts\python.exe" -u "scripts\m5_finalize_main_real_closeout.py"
if errorlevel 1 exit /b %ERRORLEVEL%

echo.
echo [7/7] Closeout complete
echo ============================================================
echo HT-CN MAIN REAL CLOSEOUT READY
echo Preflight      : artifacts\reports\m5-real-closeout-preflight.json
echo Final report   : artifacts\reports\m5-main-real-closeout-final.json
echo Browser evidence: artifacts\reports\playwright\phase21-real-delivery-browser-evidence.json
echo ============================================================
exit /b 0
