@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\qa_local.ps1"
if errorlevel 1 (
  echo.
  echo [HT-CN QA] 测试失败，请把本窗口截图发给 ChatGPT。
  pause
  exit /b 1
)
echo.
echo [HT-CN QA] M0 自动测试通过。
pause
