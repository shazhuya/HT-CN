@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN M4] ERROR: .venv not found.
  pause
  exit /b 1
)

if not exist "data\market\catalog.duckdb" (
  echo [HT-CN M4] ERROR: real M1 catalog not found.
  pause
  exit /b 1
)

echo ============================================================
echo HT-CN M4 PROSPECTIVE LIFECYCLE SNAPSHOT
echo Current closed day only. No historical backfill.
echo ============================================================
echo.

.venv\Scripts\python.exe scripts\m4_capture_lifecycle_snapshot.py
set EXIT_CODE=%ERRORLEVEL%

echo.
if %EXIT_CODE% EQU 0 (
  echo [HT-CN M4] Authoritative capture committed and evidence health passed.
) else (
  echo [HT-CN M4] Capture did not reach authoritative PASS. Check the report.
)
echo Report:       artifacts\reports\m4-lifecycle-snapshot.json
echo Transactions: data\research\m4\captures
echo Journal mirror: data\research\m4\lifecycle_journal.jsonl
pause
exit /b %EXIT_CODE%
