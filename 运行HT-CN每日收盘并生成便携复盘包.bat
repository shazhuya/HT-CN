@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN] ERROR: .venv not found.
  exit /b 1
)

echo ============================================================
echo HT-CN 每日收盘 + 便携复盘交付
echo 1. 每日收盘产品/研究流水线
echo 2. verified v3
echo 3. exact-identity v4
echo 4. Visual Semantics v2 Inspector + HTML
echo 5. 单文件 portable delivery ZIP + immutable archive
echo.
echo 任一便携交付阶段失败，都不会覆盖上一份 latest pointer。
echo Phase14/16 冻结别名不会被本流程覆盖。
echo ============================================================
echo.

".venv\Scripts\python.exe" -u "scripts\m5_daily_close_pipeline.py"
set "DAILY_EXIT=%ERRORLEVEL%"
if not "%DAILY_EXIT%"=="0" (
  echo.
  echo [HT-CN] 每日收盘产品未就绪，停止便携交付。exit=%DAILY_EXIT%
  exit /b %DAILY_EXIT%
)

echo.
echo ============================================================
echo 开始生成每日便携复盘交付包
echo ============================================================
".venv\Scripts\python.exe" -u "scripts\m5_build_daily_portable_delivery.py"
set "DELIVERY_EXIT=%ERRORLEVEL%"

echo.
if "%DELIVERY_EXIT%"=="0" (
  echo [HT-CN] 每日便携交付完成。
  echo ZIP : artifacts\reports\htcn-daily-portable-delivery-v1.zip
  echo HTML: artifacts\reports\m5-daily-portable-workspace.html
  echo Latest: artifacts\reports\m5-daily-portable-delivery-latest.json
) else (
  echo [HT-CN] 便携交付失败，上一份成功交付仍由 latest pointer 指向。
  echo Run report: artifacts\reports\m5-daily-portable-delivery-run.json
)
exit /b %DELIVERY_EXIT%
