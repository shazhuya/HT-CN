@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  set "PY=.venv\Scripts\python.exe"
) else (
  set "PY=python"
)

echo [HT-CN CHAT CONTINUITY] 校验便携续接包及当前 Git HEAD...
"%PY%" scripts\verify_chat_continuation_bundle.py artifacts\reports\htcn-chat-continuation-bundle.zip --require-current-head
if errorlevel 1 goto :fail

echo.
echo [HT-CN CHAT CONTINUITY] ========================================
echo [HT-CN CHAT CONTINUITY] BUNDLE VALID
echo [HT-CN CHAT CONTINUITY] 可以上传 ZIP 并粘贴新聊天提示词。
echo [HT-CN CHAT CONTINUITY] ========================================
pause
exit /b 0

:fail
echo.
echo [HT-CN CHAT CONTINUITY] FAILED. 请在最新、干净的仓库重新生成续接包。
pause
exit /b 1
