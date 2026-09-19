@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  set "PY=.venv\Scripts\python.exe"
) else (
  set "PY=python"
)

echo [HT-CN PROJECT OS] 检查 Project OS v2 状态完整性...
"%PY%" scripts\project_state.py
if errorlevel 1 goto :fail

echo.
echo [HT-CN PROJECT OS] ========================================
echo [HT-CN PROJECT OS] PROJECT STATE READY
echo [HT-CN PROJECT OS] 可以按 AGENTS.md Bootstrap 协议继续项目。
echo [HT-CN PROJECT OS] ========================================
pause
exit /b 0

:fail
echo.
echo [HT-CN PROJECT OS] FAILED. 状态漂移或 ledger 断链，先修复 Project OS。
pause
exit /b 1
