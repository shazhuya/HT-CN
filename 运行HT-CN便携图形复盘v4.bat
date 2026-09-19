@echo off
setlocal
cd /d "%~dp0"
python scripts\m5_build_portable_pattern_workspace_v4.py
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
  echo.
  echo [HT-CN] Phase 16 portable pattern workspace failed with exit code %ERR%.
  exit /b %ERR%
)
echo.
echo [HT-CN] Phase 16 portable pattern workspace ready.
echo V4 ZIP: artifacts\reports\htcn-daily-handoff-v4.zip
echo JSON: artifacts\reports\m5-handoff-v4-inspector.json
echo HTML: artifacts\reports\m5-handoff-v4-pattern-workspace.html
exit /b 0
