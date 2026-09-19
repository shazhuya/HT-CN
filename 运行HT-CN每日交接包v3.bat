@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo HT-CN M5 每日交接包 v3
echo - v2 作为冻结基础包嵌套，不修改旧 v2
echo - 追加 Phase 11 history / Phase 12 digest / Phase 13 review state
echo - 运输失败不改写 product/history/digest/M4 readiness
echo - 外层 ZIP 不是 authoritative evidence，也不是交易指令
echo ============================================================
echo.

python -u scripts\m5_build_daily_handoff_v3.py
set EXIT_CODE=%ERRORLEVEL%

echo.
if "%EXIT_CODE%"=="0" (
    echo [HT-CN] 每日交接包 v3 已生成:
    echo artifacts\reports\htcn-daily-handoff-v3.zip
    echo.
    echo 详细报告:
    echo artifacts\reports\m5-daily-handoff-v3.json
) else (
    echo [HT-CN] v3 运输层生成失败。
    echo 这不会改写既有产品、历史、复盘或 M4 readiness。
    echo 旧的 v2 交接包也不会被覆盖。
    echo 查看 artifacts\reports\m5-daily-handoff-v3.json
)
echo.
exit /b %EXIT_CODE%
