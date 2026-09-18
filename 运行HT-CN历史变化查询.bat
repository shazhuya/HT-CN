@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo HT-CN M5 跨日产品观察历史
echo - 默认显示最近60个交易日
echo - 可传入证券代码筛选，例如 SSE.688256
echo - 产品观察，不是M4权威证据，不做胜率/alpha排名
echo ============================================================
echo.

if "%~1"=="" (
    python -u scripts\m5_query_operator_history.py --limit 60
) else (
    python -u scripts\m5_query_operator_history.py --instrument "%~1" --limit 60
)

exit /b %ERRORLEVEL%
