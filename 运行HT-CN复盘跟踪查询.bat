@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo HT-CN M5 复盘跟踪 Journal 查询
echo - 只读产品复盘记录
echo - 不修改 lifecycle/action，不写 M4 evidence
echo - 不做胜率/alpha/预测排名，不输出交易指令
echo ============================================================
echo.

if "%~1"=="" (
    python -u scripts\m5_query_review_journal.py --limit 200
) else (
    python -u scripts\m5_query_review_journal.py --instrument "%~1" --limit 200
)

exit /b %ERRORLEVEL%
