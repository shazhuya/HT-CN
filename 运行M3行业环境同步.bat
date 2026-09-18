@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo [HT-CN M3] 同步行业映射，并用本地A股数据库重算行业强弱/广度/量能...
python scripts\m3_sync_industry_context.py
set EXIT_CODE=%ERRORLEVEL%
echo.
if %EXIT_CODE% EQU 0 (
  echo [HT-CN M3] 行业环境同步完成。
) else (
  echo [HT-CN M3] 行业环境同步失败；旧映射不会被半套数据覆盖。
)
echo 报告：artifacts\reports\m3-industry-context-sync.json
pause
exit /b %EXIT_CODE%
