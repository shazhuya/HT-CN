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
echo HT-CN 每日收盘主流程
echo M1行情更新 ^> Context刷新 ^> M5全市场Operator队列
echo 然后独立尝试M4前瞻研究链。
echo M4 QFQ或研究门禁失败不会阻塞M5产品队列。
echo ============================================================
echo.

".venv\Scripts\python.exe" -u "scripts\m5_daily_close_pipeline.py"
set "PIPELINE_EXIT=%ERRORLEVEL%"

echo.
echo ============================================================
echo 每日收盘主流程结束，exit=%PIPELINE_EXIT%
echo 汇总报告: artifacts\reports\m5-daily-close-pipeline.json
echo M5队列缓存: data\product\m5\operator_queue
echo M5产品可用与M4研究就绪状态请看汇总报告，二者独立。
echo ============================================================
echo.
pause
exit /b %PIPELINE_EXIT%
