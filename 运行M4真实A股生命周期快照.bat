@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion
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
echo HT-CN M4 PROSPECTIVE EVIDENCE CAPTURE
echo Current closed day only. No historical backfill.
echo One run: M1 update + capture + health + transition + observation + handoff bundle.
echo ============================================================
echo.

if not exist "artifacts\reports" mkdir "artifacts\reports"

echo [1/6] M1 smart daily update...
.venv\Scripts\python.exe scripts\m1_daily_update.py --limit 0 --sleep 0.05 > "artifacts\reports\m4-m1-update.log" 2>&1
set "M1_EXIT=!ERRORLEVEL!"
type "artifacts\reports\m4-m1-update.log"

echo.
echo [2/6] Authoritative lifecycle capture...
if "!M1_EXIT!"=="0" (
  .venv\Scripts\python.exe scripts\m4_capture_lifecycle_snapshot.py
  set "CAPTURE_EXIT=!ERRORLEVEL!"
) else (
  echo [HT-CN M4] SKIP: M1 update did not pass; no new authoritative capture will be attempted.
  set "CAPTURE_EXIT=1"
)

echo.
echo [3/6] Evidence-chain health...
.venv\Scripts\python.exe scripts\m4_evidence_health.py
set "HEALTH_EXIT=!ERRORLEVEL!"

echo.
echo [4/6] Lifecycle transition report...
.venv\Scripts\python.exe scripts\m4_build_transition_report.py
set "TRANSITION_EXIT=!ERRORLEVEL!"

echo.
echo [5/6] Prospective observation report...
.venv\Scripts\python.exe scripts\m4_build_observation_report.py
set "OBSERVATION_EXIT=!ERRORLEVEL!"

echo.
echo [6/6] Evidence handoff bundle...
.venv\Scripts\python.exe scripts\m4_export_evidence_bundle.py
set "BUNDLE_EXIT=!ERRORLEVEL!"

set "FINAL_EXIT=0"
if not "!M1_EXIT!"=="0" set "FINAL_EXIT=1"
if not "!CAPTURE_EXIT!"=="0" set "FINAL_EXIT=1"
if not "!HEALTH_EXIT!"=="0" set "FINAL_EXIT=1"
if not "!TRANSITION_EXIT!"=="0" set "FINAL_EXIT=1"
if not "!OBSERVATION_EXIT!"=="0" set "FINAL_EXIT=1"
if not "!BUNDLE_EXIT!"=="0" set "FINAL_EXIT=1"

echo.
echo ============================================================
echo HT-CN M4 CAPTURE SUMMARY
echo m1=!M1_EXIT! capture=!CAPTURE_EXIT! health=!HEALTH_EXIT! transition=!TRANSITION_EXIT! observation=!OBSERVATION_EXIT! bundle=!BUNDLE_EXIT!
echo ============================================================

if "!FINAL_EXIT!"=="0" (
  echo [HT-CN M4] PASS: authoritative capture and derived evidence reports completed.
) else (
  echo [HT-CN M4] NOT PASS: one or more gates failed. Existing committed evidence is not overwritten.
)

echo.
echo M1 log:       artifacts\reports\m4-m1-update.log
echo Snapshot:     artifacts\reports\m4-lifecycle-snapshot.json
echo Health:       artifacts\reports\m4-evidence-health.json
echo Transitions:  artifacts\reports\m4-lifecycle-transitions.json
echo Observations: artifacts\reports\m4-prospective-observations.json
echo Bundle:       artifacts\reports\m4-evidence-bundle.zip
echo Transactions: data\research\m4\captures
echo Journal mirror: data\research\m4\lifecycle_journal.jsonl
echo Manifest mirror: data\research\m4\snapshot_manifest.jsonl
echo.
pause
exit /b !FINAL_EXIT!
