@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  set "PY=.venv\Scripts\python.exe"
) else (
  set "PY=python"
)

echo [HT-CN CHAT CONTINUITY] 生成并校验普通 ChatGPT / 跨 AI 便携续接包...
"%PY%" scripts\build_chat_continuation_bundle.py
if errorlevel 1 goto :fail

echo.
echo [HT-CN CHAT CONTINUITY] ========================================
echo [HT-CN CHAT CONTINUITY] 续接包生成并校验成功。
echo [HT-CN CHAT CONTINUITY] 1. 上传：artifacts\reports\htcn-chat-continuation-bundle.zip
echo [HT-CN CHAT CONTINUITY] 2. ZIP 不可读时上传：logs\context\HTCN_CHAT_HANDOFF.md
echo [HT-CN CHAT CONTINUITY] 3. 粘贴：logs\context\HTCN_NEW_CHAT_PROMPT.md
echo [HT-CN CHAT CONTINUITY] 新 AI 必须先返回 Bootstrap Receipt，再开始工作。
echo [HT-CN CHAT CONTINUITY] ========================================
pause
exit /b 0

:fail
echo.
echo [HT-CN CHAT CONTINUITY] FAILED. 工作区不干净、状态漂移或 bundle 校验失败。
pause
exit /b 1
