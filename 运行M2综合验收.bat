@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN M2 ACCEPT] Environment missing. Run install script first.
  pause
  exit /b 1
)

echo [HT-CN M2 ACCEPT] 1/7 Deterministic QA + Web build + API + fixture/live browser acceptance...
.venv\Scripts\python.exe scripts\qa_local.py
if errorlevel 1 goto :fail

echo.
echo [HT-CN M2 ACCEPT] 2/7 Real local QFQ harmonic scan...
.venv\Scripts\python.exe scripts\m2_local_accept.py
if errorlevel 1 goto :fail

echo.
echo [HT-CN M2 ACCEPT] 3/7 Reaction / retest / RSI confirmation audit...
.venv\Scripts\python.exe scripts\m2_outcome_audit.py
if errorlevel 1 goto :fail

echo.
echo [HT-CN M2 ACCEPT] 4/7 Cross-scale Pivot robustness audit...
.venv\Scripts\python.exe scripts\m2_pivot_robustness_audit.py
if errorlevel 1 goto :fail

echo.
echo [HT-CN M2 ACCEPT] 5/7 Mine real A-share Golden Case candidates...
.venv\Scripts\python.exe scripts\m2_golden_candidate_miner.py
if errorlevel 1 goto :fail

echo.
echo [HT-CN M2 ACCEPT] 6/7 Verify frozen Type-I evidence integrity...
.venv\Scripts\python.exe scripts\m2_type_i_holdout_prereg_report.py
if errorlevel 1 goto :fail
.venv\Scripts\python.exe scripts\m2_type_i_holdout_result_report.py
if errorlevel 1 goto :fail
.venv\Scripts\python.exe scripts\m2_type_i_external_prereg_report.py
if errorlevel 1 goto :fail
.venv\Scripts\python.exe scripts\m2_type_i_external_result_report.py
if errorlevel 1 goto :fail

echo.
echo [HT-CN M2 ACCEPT] 7/7 Initialized-dataset health ^(coverage is reported separately^) ...
.venv\Scripts\python.exe scripts\m1_health_check.py
if errorlevel 1 goto :fail

echo.
echo [HT-CN M2 ACCEPT] ========================================
echo [HT-CN M2 ACCEPT] M2 AUTOMATED ACCEPTANCE PASSED.
echo [HT-CN M2 ACCEPT] Visual artifacts are generated automatically; no manual screenshot review is required.
echo [HT-CN M2 ACCEPT] Frozen historical Holdout/replication were verified only; they were NOT recomputed.
echo [HT-CN M2 ACCEPT] Prospective registry is intentionally NOT mutated by acceptance.
echo [HT-CN M2 ACCEPT] Fixture visual : artifacts\screenshots\m2-harmonic-workbench-fixture.png
echo [HT-CN M2 ACCEPT] Live visual    : artifacts\screenshots\m2-harmonic-workbench-live.png
echo [HT-CN M2 ACCEPT] Outcome report : artifacts\reports\m2-reaction-audit.json
echo [HT-CN M2 ACCEPT] Pivot report   : artifacts\reports\m2-pivot-robustness.json
echo [HT-CN M2 ACCEPT] Golden manifest: artifacts\golden_candidates\manifest.json
echo [HT-CN M2 ACCEPT] NOTE: M2 pass does not mean all 5218 symbols are initialized locally.
echo [HT-CN M2 ACCEPT] Start app with: 启动HT-CN.bat
echo [HT-CN M2 ACCEPT] Update prospective evidence separately with: 运行M2前瞻Type-I登记.bat
echo [HT-CN M2 ACCEPT] ========================================
pause
exit /b 0

:fail
echo.
echo [HT-CN M2 ACCEPT] FAILED. Keep the final error block; routine screenshots are not required.
pause
exit /b 1
