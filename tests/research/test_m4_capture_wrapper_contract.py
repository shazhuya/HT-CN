from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WRAPPER = ROOT / "运行M4真实A股生命周期快照.bat"
M7_ENTRY = ROOT / "运行M7前瞻证据积累.bat"
REQUIRED_BRANCH = "main"


def _wrapper_text() -> str:
    return WRAPPER.read_text(encoding="utf-8")


def test_capture_wrapper_requires_current_canonical_main() -> None:
    text = _wrapper_text()
    assert f'set "M7_REQUIRED_BRANCH={REQUIRED_BRANCH}"' in text
    assert "git fetch --quiet origin main" in text
    assert "git rev-parse HEAD" in text
    assert "git rev-parse origin/main" in text
    assert 'if /I not "!M7_HEAD!"=="!M7_ORIGIN_MAIN!"' in text
    assert "m4/real-a-share-validation-workflow" not in text


def test_capture_wrapper_preflight_runs_before_private_m1_update() -> None:
    text = _wrapper_text()
    m1_update = text.index(r"scripts\m1_daily_update.py")
    assert text.index("git symbolic-ref --quiet --short HEAD") < m1_update
    assert text.index("git fetch --quiet origin main") < m1_update
    assert text.index("git rev-parse origin/main") < m1_update
    assert text.index("git status --porcelain") < m1_update
    assert text.index(r"scripts\m4_methodology_freeze_guard.py") < m1_update
    assert text.index(r"scripts\m4_outcome_engine_freeze_guard.py") < m1_update


def test_capture_wrapper_fails_closed_before_authoritative_capture() -> None:
    text = _wrapper_text()
    assert "No M1 update or authoritative capture was started." in text
    assert "cannot refresh origin/main" in text
    assert "local main is not canonical origin/main" in text
    assert "worktree is not clean before M1 update" in text
    assert r"scripts\m4_capture_lifecycle_snapshot.py" in text
    assert "methodology components differ from the frozen T1 protocol" in text
    assert "outcome engine differs from the frozen Phase 3.1 contract" in text


def test_capture_wrapper_runs_outcome_only_after_capture_health_observation() -> None:
    text = _wrapper_text()
    outcome = text.index(r"scripts\m4_build_outcome_report.py")
    bundle = text.index(r"scripts\m4_export_evidence_bundle.py")
    assert text.index('if "!CAPTURE_EXIT!"=="0"') < outcome
    assert text.index('if "!HEALTH_EXIT!"=="0"') < outcome
    assert text.index('if "!OBSERVATION_EXIT!"=="0"') < outcome
    assert outcome < bundle
    assert "no new outcome snapshot will be attempted" in text


def test_capture_wrapper_treats_outcome_and_m7_status_as_final_gates() -> None:
    text = _wrapper_text()
    assert 'if not "!OUTCOME_EXIT!"=="0" set "FINAL_EXIT=1"' in text
    assert 'if not "!M7_STATUS_EXIT!"=="0" set "FINAL_EXIT=1"' in text
    assert "m4-outcome-v2.json" in text
    assert "m7-accumulation-status.json" in text
    assert r"data\research\m4\outcomes" in text


def test_capture_wrapper_runs_strict_qfq_readiness_before_capture() -> None:
    text = _wrapper_text()
    m1 = text.index(r"scripts\m1_daily_update.py")
    qfq = text.index(r"scripts\m4_prepare_qfq_universe.py")
    capture = text.index(r"scripts\m4_capture_lifecycle_snapshot.py")
    assert m1 < qfq < capture
    assert 'if "!M1_EXIT!"=="0" if "!QFQ_EXIT!"=="0"' in text
    assert 'if not "!QFQ_EXIT!"=="0" set "FINAL_EXIT=1"' in text
    assert "m4-qfq-readiness.json" in text
    assert "m4-qfq-readiness.log" in text
    assert "M1/QFQ readiness did not pass" in text


def test_capture_wrapper_streams_qfq_progress_live() -> None:
    text = _wrapper_text()
    assert (
        r"Tee-Object -FilePath 'artifacts\reports\m4-qfq-readiness.log'"
        in text
    )
    assert r"scripts\m4_prepare_qfq_universe.py" in text
    assert r'> "artifacts\reports\m4-qfq-readiness.log" 2>&1' not in text


def test_m7_operator_entry_delegates_to_guarded_capture_wrapper() -> None:
    text = M7_ENTRY.read_text(encoding="utf-8")
    assert 'call "运行M4真实A股生命周期快照.bat"' in text
    assert "exit /b %ERRORLEVEL%" in text
