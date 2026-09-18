@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo HT-CN M5 每日交接包 v2
echo - 只打包 Phase 9 最终产物
echo - 不改写 M5 product-ready / M4 research-ready
echo - 外层 ZIP 永远不是 authoritative evidence
echo ============================================================
echo.

python -u scripts\m5_build_daily_handoff.py
set EXIT_CODE=%ERRORLEVEL%

echo.
if "%EXIT_CODE%"=="0" (
    echo [HT-CN] 每日交接包已生成:
    echo artifacts\reports\htcn-daily-handoff-v2.zip
    echo.
    echo 详细报告:
    echo artifacts\reports\m5-daily-handoff.json
) else (
    echo [HT-CN] 交接包运输层生成失败。
    echo 这不会改写此前 Phase 9 的产品就绪状态。
    echo 查看 artifacts\reports\m5-daily-handoff.json
)
echo.
exit /b %EXIT_CODE%
