@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN] ERROR: .venv not found.
  exit /b 1
)

echo ============================================================
echo HT-CN MAIN REAL A-SHARE FINAL CLOSEOUT
echo.
echo This command is for the merged MAIN branch with private M1.
echo It does not install npm/Playwright dependencies.
echo ============================================================
echo.

call "运行HT-CN每日收盘并生成便携复盘包.bat"
if errorlevel 1 (
  echo [HT-CN] BLOCKED: daily close / Phase19 delivery failed.
  exit /b %ERRORLEVEL%
)

echo.
echo [1/5] Verify current main + Phase9 + Phase19 structural binding
".venv\Scripts\python.exe" -u "scripts\m5_main_real_closeout.py"
if errorlevel 1 exit /b %ERRORLEVEL%

echo.
echo [2/5] Prepare exact latest Phase19 workspace for Chromium
".venv\Scripts\python.exe" -u "scripts\m5_prepare_main_real_browser_audit.py"
if errorlevel 1 exit /b %ERRORLEVEL%

echo.
echo [3/5] Run dynamic Chromium audit over every transported candidate
pushd "apps\web"
call npx playwright test tests/main-real-portable-delivery.spec.ts --reporter=list
set "BROWSER_EXIT=%ERRORLEVEL%"
popd
if not "%BROWSER_EXIT%"=="0" (
  echo [HT-CN] BLOCKED: Chromium audit failed. exit=%BROWSER_EXIT%
  echo Ensure apps\web dependencies and Playwright Chromium are already installed.
  exit /b %BROWSER_EXIT%
)

echo.
echo [4/5] Independently verify browser evidence and screenshot hashes
".venv\Scripts\python.exe" -u "scripts\m5_verify_main_real_browser_evidence.py"
if errorlevel 1 exit /b %ERRORLEVEL%

echo.
echo [5/5] Finalize structural + browser identity-bound closeout
".venv\Scripts\python.exe" -u "scripts\m5_finalize_main_real_closeout.py"
if errorlevel 1 exit /b %ERRORLEVEL%

echo.
echo ============================================================
echo HT-CN MAIN REAL CLOSEOUT READY
echo Report: artifacts\reports\m5-main-real-closeout-final.json
echo Browser evidence: artifacts\reports\playwright\phase21-real-delivery-browser-evidence.json
echo ============================================================
exit /b 0
