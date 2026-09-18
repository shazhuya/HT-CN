@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN M3 CLOSEOUT] ERROR: .venv not found.
  pause
  exit /b 1
)

if not exist "data\market\catalog.duckdb" (
  echo [HT-CN M3 CLOSEOUT] ERROR: data\market\catalog.duckdb not found.
  pause
  exit /b 1
)

echo ============================================================
echo HT-CN M3 FINAL CLOSEOUT
echo 1/4 M1 smart daily update
echo 2/4 deterministic workbench acceptance
echo 3/4 real context synchronization
echo 4/4 current-HEAD merge readiness
echo ============================================================
echo.

.venv\Scripts\python.exe scripts\m1_daily_update.py
set M1_EXIT=%ERRORLEVEL%

echo.
echo [HT-CN M3 CLOSEOUT] Running strict workbench acceptance...
.venv\Scripts\python.exe scripts\qa_local.py
set QA_EXIT=%ERRORLEVEL%

echo.
echo [HT-CN M3 CLOSEOUT] Running context synchronization...
.venv\Scripts\python.exe scripts\m3_sync_all_contexts.py
set CONTEXT_EXIT=%ERRORLEVEL%

echo.
echo [HT-CN M3 CLOSEOUT] Building merge-readiness report...
.venv\Scripts\python.exe scripts\m3_pr_readiness.py
set READY_EXIT=%ERRORLEVEL%

echo.
echo ============================================================
echo M1 exit=%M1_EXIT% / QA exit=%QA_EXIT% / Context exit=%CONTEXT_EXIT% / Ready exit=%READY_EXIT%
echo Workbench report: artifacts\reports\m3-workbench-acceptance.json
echo Context report:   artifacts\reports\m3-context-sync-summary.json
echo Readiness JSON:   artifacts\reports\m3-pr-readiness.json
echo Readiness MD:     artifacts\reports\m3-pr-readiness.md
echo ============================================================
if %READY_EXIT% EQU 0 (
  echo [HT-CN M3 CLOSEOUT] READY - no hard blockers. Review warnings and frozen boundaries.
) else (
  echo [HT-CN M3 CLOSEOUT] NOT READY - fix blockers in m3-pr-readiness.md.
)
pause
exit /b %READY_EXIT%
