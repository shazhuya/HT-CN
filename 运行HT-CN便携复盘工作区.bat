@echo off
setlocal
cd /d "%~dp0"
python scripts\m5_inspect_daily_handoff_v3.py
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
  echo.
  echo [HT-CN] Phase 15 portable inspector failed with exit code %ERR%.
  exit /b %ERR%
)
echo.
echo [HT-CN] Phase 15 portable review workspace ready.
echo JSON: artifacts\reports\m5-handoff-v3-inspector.json
echo HTML: artifacts\reports\m5-handoff-v3-workspace.html
exit /b 0
