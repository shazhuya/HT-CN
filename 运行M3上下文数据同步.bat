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
  echo [HT-CN M3] 四层上下文同步完成。
) else (
  echo [HT-CN M3] 同步存在降级或失败，请查看总报告；已成功的层不会回滚。
)
echo 总报告：artifacts\reports\m3-context-sync-summary.json
echo.
pause
exit /b %EXIT_CODE%
