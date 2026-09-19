@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  set "PY=.venv\Scripts\python.exe"
) else (
  set "PY=python"
)

echo [HT-CN PROJECT OS] 生成动态跨对话续接包...
"%PY%" scripts\project_state.py --resume --output logs\context\HTCN_RESUME_PACK.md
if errorlevel 1 goto :fail

echo.
echo [HT-CN PROJECT OS] ========================================
echo [HT-CN PROJECT OS] 续接包生成成功。
echo [HT-CN PROJECT OS] 文件：logs\context\HTCN_RESUME_PACK.md
echo [HT-CN PROJECT OS] 该文件由 PROJECT_STATE 动态生成，不再硬编码旧 Phase 规范。
echo [HT-CN PROJECT OS] ========================================
pause
exit /b 0

:fail
echo.
echo [HT-CN PROJECT OS] FAILED. Project state/ledger 存在不一致，禁止继续核心开发。
pause
exit /b 1
