@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo [HT-CN M3] 同步概念/题材映射，并用本地A股数据库重算题材强弱...
python scripts\m3_sync_concept_context.py --workers 8
set EXIT_CODE=%ERRORLEVEL%
echo.
if %EXIT_CODE% EQU 0 (
  echo [HT-CN M3] 概念/题材环境同步完成。
) else (
  echo [HT-CN M3] 概念同步失败；旧完整映射将保留。
)
echo 报告：artifacts\reports\m3-concept-context-sync.json
pause
exit /b %EXIT_CODE%
