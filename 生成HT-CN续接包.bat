@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  set "PY=.venv\Scripts\python.exe"
) else (
  set "PY=python"
)

echo [HT-CN CONTEXT] 生成跨对话续接包...
"%PY%" scripts\context_pack.py
if errorlevel 1 goto :fail

echo.
echo [HT-CN CONTEXT] ========================================
echo [HT-CN CONTEXT] 续接包生成成功。
echo [HT-CN CONTEXT] 文件：logs\context\HTCN_CONTEXT_PACK.md
echo [HT-CN CONTEXT] 新对话开始时，优先让 Agent 读取仓库 AGENTS.md；
echo [HT-CN CONTEXT] 若需要离线/手动交接，可直接提供上述续接包。
echo [HT-CN CONTEXT] ========================================
pause
exit /b 0

:fail
echo.
echo [HT-CN CONTEXT] FAILED. 请保留上面的错误信息。
pause
exit /b 1
