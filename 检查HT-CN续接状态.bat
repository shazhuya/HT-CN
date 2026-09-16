@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  set "PY=.venv\Scripts\python.exe"
) else (
  set "PY=python"
)

echo [HT-CN CONTEXT] 检查跨对话续接状态...
"%PY%" scripts\context_pack.py --check
if errorlevel 1 goto :fail

echo.
echo [HT-CN CONTEXT] ========================================
echo [HT-CN CONTEXT] 续接机制结构检查通过。
echo [HT-CN CONTEXT] 若提示 checkpoint 落后于 HEAD，属于可接受状态，
echo [HT-CN CONTEXT] 但新会话必须先阅读这些 delta commits 再继续开发。
echo [HT-CN CONTEXT] ========================================
pause
exit /b 0

:fail
echo.
echo [HT-CN CONTEXT] FAILED. 续接元数据存在结构性问题，先修复再继续开发。
pause
exit /b 1
