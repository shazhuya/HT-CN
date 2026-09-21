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
  "m7-append-precheck.json"
  "m7-append-action.txt"
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
set "PRECHECK_EXIT=1"
set "APPEND_ACTION=blocked"
set "QFQ_EXIT=1"
set "CAPTURE_EXIT=1"
set "HEALTH_EXIT=1"
set "TRANSITION_EXIT=1"
set "OBSERVATION_EXIT=1"
set "OUTCOME_EXIT=1"
set "BUNDLE_EXIT=1"
set "M7_STATUS_EXIT=1"
set "ACCEPT_EXIT=1"

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
echo One run: M1 + append precheck + optional QFQ/capture/outcome + health + transition + observation + M7 status + bundle + acceptance.
echo ============================================================
echo.

echo [1/11] M1 smart daily update...
.venv\Scripts\python.exe scripts\m1_daily_update.py --limit 0 --sleep 0.05 > "artifacts\reports\m4-m1-update.log" 2>&1
set "M1_EXIT=!ERRORLEVEL!"
type "artifacts\reports\m4-m1-update.log"

echo.
echo [2/11] M7 append precheck...
if "!M1_EXIT!"=="0" (
  .venv\Scripts\python.exe scripts\m7_append_precheck.py
  set "PRECHECK_EXIT=!ERRORLEVEL!"
  if "!PRECHECK_EXIT!"=="0" if exist "artifacts\reports\m7-append-action.txt" set /p APPEND_ACTION=<"artifacts\reports\m7-append-action.txt"
) else (
  echo [HT-CN M7] SKIP: M1 update did not pass; append precheck was not attempted.
  set "PRECHECK_EXIT=1"
  set "APPEND_ACTION=blocked"
)

echo.
echo [3/11] Strict formal-QFQ universe readiness...
if "!PRECHECK_EXIT!"=="0" if /I "!APPEND_ACTION!"=="capture_due" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "& { & '.\.venv\Scripts\python.exe' -u 'scripts\m4_prepare_qfq_universe.py' '--retries' '1' '--sleep' '0.05' 2>&1 | Tee-Object -FilePath 'artifacts\reports\m4-qfq-readiness.log'; exit $LASTEXITCODE }"
  set "QFQ_EXIT=!ERRORLEVEL!"
) else if "!PRECHECK_EXIT!"=="0" if /I "!APPEND_ACTION!"=="idempotent_noop" (
  echo [HT-CN M7] NO-OP: latest closed session is already committed; QFQ append-readiness is not rerun.
  set "QFQ_EXIT=0"
) else (
  echo [HT-CN M7] SKIP: append precheck did not authorize a new capture.
  set "QFQ_EXIT=1"
)

echo.
echo [4/11] Authoritative lifecycle capture...
if "!PRECHECK_EXIT!"=="0" if /I "!APPEND_ACTION!"=="capture_due" if "!QFQ_EXIT!"=="0" (
  .venv\Scripts\python.exe scripts\m4_capture_lifecycle_snapshot.py
  set "CAPTURE_EXIT=!ERRORLEVEL!"
) else if "!PRECHECK_EXIT!"=="0" if /I "!APPEND_ACTION!"=="idempotent_noop" (
  echo [HT-CN M7] NO-OP: authoritative capture for the latest closed session already exists.
  set "CAPTURE_EXIT=0"
) else (
  echo [HT-CN M7] SKIP: precheck/QFQ did not authorize a new authoritative capture.
  set "CAPTURE_EXIT=1"
)

echo.
echo [5/11] Evidence-chain health...
.venv\Scripts\python.exe scripts\m4_evidence_health.py
set "HEALTH_EXIT=!ERRORLEVEL!"

echo.
echo [6/11] Lifecycle transition report...
.venv\Scripts\python.exe scripts\m4_build_transition_report.py
set "TRANSITION_EXIT=!ERRORLEVEL!"

echo.
echo [7/11] Prospective observation report...
.venv\Scripts\python.exe scripts\m4_build_observation_report.py
set "OBSERVATION_EXIT=!ERRORLEVEL!"

echo.
echo [8/11] Preregistered outcome-v2 report...
if "!PRECHECK_EXIT!"=="0" if /I "!APPEND_ACTION!"=="capture_due" if "!CAPTURE_EXIT!"=="0" if "!HEALTH_EXIT!"=="0" if "!OBSERVATION_EXIT!"=="0" (
  .venv\Scripts\python.exe scripts\m4_build_outcome_report.py
  set "OUTCOME_EXIT=!ERRORLEVEL!"
) else if "!PRECHECK_EXIT!"=="0" if /I "!APPEND_ACTION!"=="idempotent_noop" (
  echo [HT-CN M7] NO-OP: same closed session already has its immutable outcome snapshot state.
  set "OUTCOME_EXIT=0"
) else (
  echo [HT-CN M7] SKIP: capture/health/observation did not pass; no new outcome snapshot will be attempted.
  set "OUTCOME_EXIT=1"
)

echo.
echo [9/11] M7 accumulation status...
.venv\Scripts\python.exe scripts\m7_accumulation_status.py
set "M7_STATUS_EXIT=!ERRORLEVEL!"

echo.
echo [10/11] Evidence handoff bundle...
.venv\Scripts\python.exe scripts\m4_export_evidence_bundle.py
set "BUNDLE_EXIT=!ERRORLEVEL!"

echo.
echo [11/11] Read-only M7 evidence acceptance...
if "!BUNDLE_EXIT!"=="0" (
  .venv\Scripts\python.exe scripts\m7_evidence_acceptance.py "artifacts\reports\m4-evidence-bundle.zip" --expected-baseline-trade-date 2026-09-17 --output "artifacts\reports\m7-evidence-acceptance.json"
  set "ACCEPT_EXIT=!ERRORLEVEL!"
) else (
  echo [HT-CN M7] SKIP: evidence bundle was not produced; acceptance was not attempted.
  set "ACCEPT_EXIT=1"
)

set "FINAL_EXIT=0"
if not "!M1_EXIT!"=="0" set "FINAL_EXIT=1"
if not "!PRECHECK_EXIT!"=="0" set "FINAL_EXIT=1"
if not "!QFQ_EXIT!"=="0" set "FINAL_EXIT=1"
if not "!CAPTURE_EXIT!"=="0" set "FINAL_EXIT=1"
if not "!HEALTH_EXIT!"=="0" set "FINAL_EXIT=1"
if not "!TRANSITION_EXIT!"=="0" set "FINAL_EXIT=1"
if not "!OBSERVATION_EXIT!"=="0" set "FINAL_EXIT=1"
if not "!OUTCOME_EXIT!"=="0" set "FINAL_EXIT=1"
if not "!BUNDLE_EXIT!"=="0" set "FINAL_EXIT=1"
if not "!M7_STATUS_EXIT!"=="0" set "FINAL_EXIT=1"
if not "!ACCEPT_EXIT!"=="0" set "FINAL_EXIT=1"

echo.
echo ============================================================
echo HT-CN M7 ACCUMULATION SUMMARY
echo m1=!M1_EXIT! precheck=!PRECHECK_EXIT! action=!APPEND_ACTION! qfq=!QFQ_EXIT! capture=!CAPTURE_EXIT! health=!HEALTH_EXIT! transition=!TRANSITION_EXIT! observation=!OBSERVATION_EXIT! outcome=!OUTCOME_EXIT! m7_status=!M7_STATUS_EXIT! bundle=!BUNDLE_EXIT! acceptance=!ACCEPT_EXIT!
echo ============================================================

if "!FINAL_EXIT!"=="0" (
  if /I "!APPEND_ACTION!"=="idempotent_noop" (
    echo [HT-CN M7] PASS NO-OP: latest closed session was already committed; authoritative evidence stayed unchanged.
  ) else (
    echo [HT-CN M7] PASS: new authoritative capture and M7 accumulation status completed.
  )
) else (
  echo [HT-CN M7] NOT PASS: one or more gates failed. Existing committed evidence is not overwritten.
)

echo.
echo Canonical HEAD: !M7_HEAD!
echo Methodology:   artifacts\reports\m4-methodology-freeze-guard.json
echo Outcome guard: artifacts\reports\m4-outcome-engine-freeze-guard.json
echo M1 log:        artifacts\reports\m4-m1-update.log
echo Append check:   artifacts\reports\m7-append-precheck.json
echo QFQ report:    artifacts\reports\m4-qfq-readiness.json
echo QFQ log:       artifacts\reports\m4-qfq-readiness.log
echo Snapshot:      artifacts\reports\m4-lifecycle-snapshot.json
echo Health:        artifacts\reports\m4-evidence-health.json
echo Transitions:   artifacts\reports\m4-lifecycle-transitions.json
echo Observations:  artifacts\reports\m4-prospective-observations.json
echo Outcome v2:    artifacts\reports\m4-outcome-v2.json
echo Bundle:        artifacts\reports\m4-evidence-bundle.zip
echo M7 status:     artifacts\reports\m7-accumulation-status.json
echo Acceptance:     artifacts\reports\m7-evidence-acceptance.json
echo Transactions: data\research\m4\captures
echo Outcomes:     data\research\m4\outcomes
echo.
pause
exit /b !FINAL_EXIT!
