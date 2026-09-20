@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "M7_REQUIRED_BRANCH=main"

where git >nul 2>nul
if errorlevel 1 (
  echo [HT-CN M7] ERROR: git is required for capture preflight.
  pause
  exit /b 1
)

for /f "delims=" %%B in ('git symbolic-ref --quiet --short HEAD 2^>nul') do set "M7_BRANCH=%%B"
if not defined M7_BRANCH (
  echo [HT-CN M7] ERROR: detached HEAD or branch cannot be resolved.
  echo No M1 update or authoritative capture was started.
  pause
  exit /b 1
)

if /I not "!M7_BRANCH!"=="!M7_REQUIRED_BRANCH!" (
  echo [HT-CN M7] ERROR: wrong branch.
  echo Expected: !M7_REQUIRED_BRANCH!
  echo Current:  !M7_BRANCH!
  echo No M1 update or authoritative capture was started.
  pause
  exit /b 1
)

git fetch --quiet origin main
if errorlevel 1 (
  echo [HT-CN M7] ERROR: cannot refresh origin/main.
  echo Network/canonical-main identity must be available before prospective capture.
  echo No M1 update or authoritative capture was started.
  pause
  exit /b 1
)

for /f "delims=" %%H in ('git rev-parse HEAD 2^>nul') do set "M7_HEAD=%%H"
for /f "delims=" %%H in ('git rev-parse origin/main 2^>nul') do set "M7_ORIGIN_MAIN=%%H"
if not defined M7_HEAD (
  echo [HT-CN M7] ERROR: local HEAD cannot be resolved.
  echo No M1 update or authoritative capture was started.
  pause
  exit /b 1
)
if not defined M7_ORIGIN_MAIN (
  echo [HT-CN M7] ERROR: origin/main cannot be resolved after fetch.
  echo No M1 update or authoritative capture was started.
  pause
  exit /b 1
)
if /I not "!M7_HEAD!"=="!M7_ORIGIN_MAIN!" (
  echo [HT-CN M7] ERROR: local main is not canonical origin/main.
  echo Local:  !M7_HEAD!
  echo Remote: !M7_ORIGIN_MAIN!
  echo Run: git pull --ff-only origin main
  echo No M1 update or authoritative capture was started.
  pause
  exit /b 1
)

set "M7_DIRTY=0"
for /f "delims=" %%S in ('git status --porcelain 2^>nul') do set "M7_DIRTY=1"
if "!M7_DIRTY!"=="1" (
  echo [HT-CN M7] ERROR: worktree is not clean before M1 update.
  echo Commit, stash, or remove local changes before prospective evidence capture.
  echo No M1 update or authoritative capture was started.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN M7] ERROR: .venv not found.
  pause
  exit /b 1
)

if not exist "artifacts\reports" mkdir "artifacts\reports"

rem Clear disposable per-run reports so a failed run cannot package stale files.
for %%F in (
  "m4-m1-update.log"
  "m4-qfq-readiness.json"
  "m4-qfq-readiness.log"
  "m4-lifecycle-snapshot.json"
  "m4-evidence-health.json"
  "m4-evidence-health.md"
  "m4-lifecycle-transitions.json"
  "m4-lifecycle-transitions.md"
  "m4-prospective-observations.json"
  "m4-prospective-observations.md"
  "m4-outcome-v2.json"
  "m4-outcome-v2.md"
  "m7-accumulation-status.json"
  "m7-accumulation-status.md"
  "m4-evidence-bundle.zip"
) do (
  if exist "artifacts\reports\%%~F" del /q "artifacts\reports\%%~F"
)

set "M1_EXIT=1"
set "QFQ_EXIT=1"
set "CAPTURE_EXIT=1"
set "HEALTH_EXIT=1"
set "TRANSITION_EXIT=1"
set "OBSERVATION_EXIT=1"
set "OUTCOME_EXIT=1"
set "BUNDLE_EXIT=1"
set "M7_STATUS_EXIT=1"

.venv\Scripts\python.exe scripts\m4_methodology_freeze_guard.py > "artifacts\reports\m4-methodology-freeze-guard.json" 2>&1
set "METHODOLOGY_GUARD_EXIT=!ERRORLEVEL!"
type "artifacts\reports\m4-methodology-freeze-guard.json"
if not "!METHODOLOGY_GUARD_EXIT!"=="0" (
  echo [HT-CN M7] ERROR: methodology components differ from the frozen T1 protocol.
  echo No M1 update or authoritative capture was started.
  pause
  exit /b 1
)

.venv\Scripts\python.exe scripts\m4_outcome_engine_freeze_guard.py > "artifacts\reports\m4-outcome-engine-freeze-guard.json" 2>&1
set "OUTCOME_ENGINE_GUARD_EXIT=!ERRORLEVEL!"
type "artifacts\reports\m4-outcome-engine-freeze-guard.json"
if not "!OUTCOME_ENGINE_GUARD_EXIT!"=="0" (
  echo [HT-CN M7] ERROR: outcome engine differs from the frozen Phase 3.1 contract.
  echo No M1 update or authoritative capture was started.
  pause
  exit /b 1
)

if not exist "data\market\catalog.duckdb" (
  echo [HT-CN M7] ERROR: real M1 catalog not found.
  pause
  exit /b 1
)

echo ============================================================
echo HT-CN M7 PROSPECTIVE EVIDENCE ACCUMULATION
echo Current closed day only. No historical backfill.
echo Origin: clean local main exactly equal to freshly fetched origin/main.
echo Frozen guards: M4 methodology 37/37 + Outcome Engine 4/4.
echo One run: M1 + QFQ + capture + health + transition + observation + outcome + bundle + M7 status.
echo ============================================================
echo.

echo [1/9] M1 smart daily update...
.venv\Scripts\python.exe scripts\m1_daily_update.py --limit 0 --sleep 0.05 > "artifacts\reports\m4-m1-update.log" 2>&1
set "M1_EXIT=!ERRORLEVEL!"
type "artifacts\reports\m4-m1-update.log"

echo.
echo [2/9] Strict formal-QFQ universe readiness...
if "!M1_EXIT!"=="0" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "& { & '.\.venv\Scripts\python.exe' -u 'scripts\m4_prepare_qfq_universe.py' '--retries' '1' '--sleep' '0.05' 2>&1 | Tee-Object -FilePath 'artifacts\reports\m4-qfq-readiness.log'; exit $LASTEXITCODE }"
  set "QFQ_EXIT=!ERRORLEVEL!"
) else (
  echo [HT-CN M7] SKIP: M1 update did not pass; QFQ readiness was not attempted.
  set "QFQ_EXIT=1"
)

echo.
echo [3/9] Authoritative lifecycle capture...
if "!M1_EXIT!"=="0" if "!QFQ_EXIT!"=="0" (
  .venv\Scripts\python.exe scripts\m4_capture_lifecycle_snapshot.py
  set "CAPTURE_EXIT=!ERRORLEVEL!"
) else (
  echo [HT-CN M7] SKIP: M1/QFQ readiness did not pass; no new authoritative capture will be attempted.
  set "CAPTURE_EXIT=1"
)

echo.
echo [4/9] Evidence-chain health...
.venv\Scripts\python.exe scripts\m4_evidence_health.py
set "HEALTH_EXIT=!ERRORLEVEL!"

echo.
echo [5/9] Lifecycle transition report...
.venv\Scripts\python.exe scripts\m4_build_transition_report.py
set "TRANSITION_EXIT=!ERRORLEVEL!"

echo.
echo [6/9] Prospective observation report...
.venv\Scripts\python.exe scripts\m4_build_observation_report.py
set "OBSERVATION_EXIT=!ERRORLEVEL!"

echo.
echo [7/9] Preregistered outcome-v2 report...
if "!CAPTURE_EXIT!"=="0" if "!HEALTH_EXIT!"=="0" if "!OBSERVATION_EXIT!"=="0" (
  .venv\Scripts\python.exe scripts\m4_build_outcome_report.py
  set "OUTCOME_EXIT=!ERRORLEVEL!"
) else (
  echo [HT-CN M7] SKIP: capture/health/observation did not pass; no new outcome snapshot will be attempted.
  set "OUTCOME_EXIT=1"
)

echo.
echo [8/9] Evidence handoff bundle...
.venv\Scripts\python.exe scripts\m4_export_evidence_bundle.py
set "BUNDLE_EXIT=!ERRORLEVEL!"

echo.
echo [9/9] M7 accumulation status...
.venv\Scripts\python.exe scripts\m7_accumulation_status.py
set "M7_STATUS_EXIT=!ERRORLEVEL!"

set "FINAL_EXIT=0"
if not "!M1_EXIT!"=="0" set "FINAL_EXIT=1"
if not "!QFQ_EXIT!"=="0" set "FINAL_EXIT=1"
if not "!CAPTURE_EXIT!"=="0" set "FINAL_EXIT=1"
if not "!HEALTH_EXIT!"=="0" set "FINAL_EXIT=1"
if not "!TRANSITION_EXIT!"=="0" set "FINAL_EXIT=1"
if not "!OBSERVATION_EXIT!"=="0" set "FINAL_EXIT=1"
if not "!OUTCOME_EXIT!"=="0" set "FINAL_EXIT=1"
if not "!BUNDLE_EXIT!"=="0" set "FINAL_EXIT=1"
if not "!M7_STATUS_EXIT!"=="0" set "FINAL_EXIT=1"

echo.
echo ============================================================
echo HT-CN M7 ACCUMULATION SUMMARY
echo m1=!M1_EXIT! qfq=!QFQ_EXIT! capture=!CAPTURE_EXIT! health=!HEALTH_EXIT! transition=!TRANSITION_EXIT! observation=!OBSERVATION_EXIT! outcome=!OUTCOME_EXIT! bundle=!BUNDLE_EXIT! m7_status=!M7_STATUS_EXIT!
echo ============================================================

if "!FINAL_EXIT!"=="0" (
  echo [HT-CN M7] PASS: authoritative capture and M7 accumulation status completed.
) else (
  echo [HT-CN M7] NOT PASS: one or more gates failed. Existing committed evidence is not overwritten.
)

echo.
echo Canonical HEAD: !M7_HEAD!
echo Methodology:   artifacts\reports\m4-methodology-freeze-guard.json
echo Outcome guard: artifacts\reports\m4-outcome-engine-freeze-guard.json
echo M1 log:        artifacts\reports\m4-m1-update.log
echo QFQ report:    artifacts\reports\m4-qfq-readiness.json
echo QFQ log:       artifacts\reports\m4-qfq-readiness.log
echo Snapshot:      artifacts\reports\m4-lifecycle-snapshot.json
echo Health:        artifacts\reports\m4-evidence-health.json
echo Transitions:   artifacts\reports\m4-lifecycle-transitions.json
echo Observations:  artifacts\reports\m4-prospective-observations.json
echo Outcome v2:    artifacts\reports\m4-outcome-v2.json
echo Bundle:        artifacts\reports\m4-evidence-bundle.zip
echo M7 status:     artifacts\reports\m7-accumulation-status.json
echo Transactions: data\research\m4\captures
echo Outcomes:     data\research\m4\outcomes
echo.
pause
exit /b !FINAL_EXIT!
