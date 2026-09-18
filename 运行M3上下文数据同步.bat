@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo ============================================================
echo HT-CN M3 上下文数据一键同步
echo 停牌事件 + 四大核心指数 + 行业 + 概念题材
echo ============================================================
echo.
python scripts\m3_sync_all_contexts.py
set EXIT_CODE=%ERRORLEVEL%
echo.
if %EXIT_CODE% EQU 0 (
  echo [HT-CN M3] Context synchronization completed. Review report for any degraded warnings.
) else (
  echo [HT-CN M3] Structural context failure detected. Review the combined report.
)
echo 总报告：artifacts\reports\m3-context-sync-summary.json
echo.
pause
exit /b %EXIT_CODE%
