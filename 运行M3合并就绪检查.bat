@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN M3 READY] 未找到 .venv。
  pause
  exit /b 1
)

echo [HT-CN M3 READY] 检查当前 HEAD 的正式验收证据...
.venv\Scripts\python.exe scripts\m3_pr_readiness.py
set EXIT_CODE=%ERRORLEVEL%

echo.
if %EXIT_CODE% EQU 0 (
  echo [HT-CN M3 READY] PR READY 条件已满足。
  echo [HT-CN M3 READY] 仍请查看 warnings；warning 不会被静默隐藏。
) else (
  echo [HT-CN M3 READY] NOT READY。请按 blockers 修复后重新运行对应验收。
)
echo 报告：artifacts\reports\m3-pr-readiness.json
pause
exit /b %EXIT_CODE%
