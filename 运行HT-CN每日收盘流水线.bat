@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN DAILY] ERROR: .venv not found.
  echo Please run the HT-CN installer first.
  pause
  exit /b 1
)

echo ============================================================
echo HT-CN 每日收盘流水线
echo M1数据更新 ^> M5产品队列预热 + M4权威前瞻证据
echo M4与M5结果独立，不互相伪造成功。
echo ============================================================
echo.

".venv\Scripts\python.exe" "scripts\m5_daily_close_pipeline.py"
set "PIPELINE_EXIT=%ERRORLEVEL%"

echo.
echo ============================================================
echo 每日收盘流水线结束，exit=%PIPELINE_EXIT%
echo 汇总报告: artifacts\reports\m5-daily-close-pipeline.json
echo M5工作台: data\product\m5\operator_queue
echo 每日上传包: artifacts\reports\htcn-daily-handoff.zip
echo M4证据子包: artifacts\reports\m4-evidence-bundle.zip
echo ============================================================
echo.
pause
exit /b %PIPELINE_EXIT%
