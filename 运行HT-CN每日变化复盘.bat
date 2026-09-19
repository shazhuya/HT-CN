@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo HT-CN M5 每日变化复盘
echo - 读取 Phase 11 append-only 产品历史
echo - 按既有工作流整理变化，不做收益/胜率/alpha排名
echo - 不写 M4 权威 evidence，不输出交易指令
echo ============================================================
echo.

python -u scripts\m5_build_daily_review_digest.py
exit /b %ERRORLEVEL%
