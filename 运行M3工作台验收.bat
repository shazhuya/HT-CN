@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN M3 ACCEPT] 未找到 .venv，请先运行安装脚本。
  pause
  exit /b 1
)

if not exist "apps\web\node_modules" (
  echo [HT-CN M3 ACCEPT] 未找到 Web 依赖，请先运行安装脚本。
  pause
  exit /b 1
)

echo [HT-CN M3 ACCEPT] ========================================
echo [HT-CN M3 ACCEPT] M3 工作台自动验收开始
echo [HT-CN M3 ACCEPT] 覆盖：Python 回归 / Web build / API / 固定样本浏览器 / 真实本地 QFQ 浏览器

echo [HT-CN M3 ACCEPT] 不需要人工截图确认；失败时保留最后错误块即可。
echo [HT-CN M3 ACCEPT] ========================================
echo.

.venv\Scripts\python.exe scripts\qa_local.py
if errorlevel 1 goto :fail

echo.
echo [HT-CN M3 ACCEPT] ========================================
echo [HT-CN M3 ACCEPT] M3 WORKBENCH ACCEPTANCE PASSED.
echo [HT-CN M3 ACCEPT] 固定样本截图：artifacts\screenshots\m2-harmonic-workbench-fixture.png
echo [HT-CN M3 ACCEPT] 真实数据截图：artifacts\screenshots\m2-harmonic-workbench-live.png
echo [HT-CN M3 ACCEPT] Playwright 报告：artifacts\reports\playwright\index.html
echo [HT-CN M3 ACCEPT] 无需把常规截图发给我；只有失败时发送最后错误块。
echo [HT-CN M3 ACCEPT] ========================================
pause
exit /b 0

:fail
echo.
echo [HT-CN M3 ACCEPT] ========================================
echo [HT-CN M3 ACCEPT] FAILED.
echo [HT-CN M3 ACCEPT] 请保留窗口最后的错误块；无需额外人工截图。
echo [HT-CN M3 ACCEPT] ========================================
pause
exit /b 1
