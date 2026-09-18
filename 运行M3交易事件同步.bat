@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo [HT-CN M3] 同步最近已收盘交易日的已确认停牌事件...
python scripts\m3_sync_trading_events.py
set EXIT_CODE=%ERRORLEVEL%
echo.
if %EXIT_CODE% EQU 0 (
  echo [HT-CN M3] 交易事件同步完成。报告：artifacts\reports\m3-trading-event-sync.json
) else (
  echo [HT-CN M3] 交易事件同步失败，退出码 %EXIT_CODE%。
)
pause
exit /b %EXIT_CODE%
