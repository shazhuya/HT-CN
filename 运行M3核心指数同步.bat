@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo [HT-CN M3] 同步科创50、创业板指、沪深300、上证指数...
python scripts\m3_sync_core_benchmarks.py
set EXIT_CODE=%ERRORLEVEL%
echo.
if %EXIT_CODE% EQU 0 (
  echo [HT-CN M3] 四大核心指数同步完成。
) else (
  echo [HT-CN M3] 部分指数同步失败或为空；个股分析仍可运行，市场上下文将 fail-safe。
)
echo 报告：artifacts\reports\m3-core-benchmark-sync.json
pause
exit /b %EXIT_CODE%
