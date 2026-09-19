from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WRAPPER = ROOT / "运行M4真实A股生命周期快照.bat"
MIN_SAFE_COMMIT = "d29870d3a2ef7b60dec4fd8f0dbef2d7a8f0b5a7"
REQUIRED_BRANCH = "m4/real-a-share-validation-workflow"


def _wrapper_text() -> str:
    return WRAPPER.read_text(encoding="utf-8")


def test_capture_wrapper_freezes_branch_and_minimum_safe_checkpoint() -> None:
    text = _wrapper_text()
    assert f'set "M4_REQUIRED_BRANCH={REQUIRED_BRANCH}"' in text
    assert f'set "M4_MIN_SAFE_COMMIT={MIN_SAFE_COMMIT}"' in text
    assert "git merge-base --is-ancestor !M4_MIN_SAFE_COMMIT! HEAD" in text


def test_capture_wrapper_preflight_runs_before_private_m1_update() -> None:
    text = _wrapper_text()
    m1_update = text.index("scripts\\m1_daily_update.py")
    assert text.index("git symbolic-ref --quiet --short HEAD") < m1_update
    assert text.index("git merge-base --is-ancestor") < m1_update
    assert text.index("git status --porcelain") < m1_update
    assert text.index("scripts\\m4_methodology_freeze_guard.py") < m1_update


def test_capture_wrapper_fails_closed_before_authoritative_capture() -> None:
    text = _wrapper_text()
    assert "No M1 update or authoritative capture was started." in text
    assert "worktree is not clean before M1 update" in text
    assert "current HEAD predates or diverges from the minimum safe hosted-CI-green Phase 3.1 workflow" in text
    assert "scripts\\m4_capture_lifecycle_snapshot.py" in text
    assert "methodology components differ from the frozen T1 protocol" in text
    assert "m4-methodology-freeze-guard.json" in text



def test_capture_wrapper_runs_outcome_only_after_capture_health_observation() -> None:
    text = _wrapper_text()
    outcome = text.index("scripts\\m4_build_outcome_report.py")
    bundle = text.index("scripts\\m4_export_evidence_bundle.py")
    assert text.index('if "!CAPTURE_EXIT!"=="0"') < outcome
    assert text.index('if "!HEALTH_EXIT!"=="0"') < outcome
    assert text.index('if "!OBSERVATION_EXIT!"=="0"') < outcome
    assert outcome < bundle
    assert "no new outcome snapshot will be attempted" in text


def test_capture_wrapper_treats_outcome_as_final_gate() -> None:
    text = _wrapper_text()
    assert 'if not "!OUTCOME_EXIT!"=="0" set "FINAL_EXIT=1"' in text
    assert "m4-outcome-v2.json" in text
    assert "data\\research\\m4\\outcomes" in text



def test_capture_wrapper_runs_outcome_engine_freeze_guard_before_m1() -> None:
    text = _wrapper_text()
    m1_update = text.index("scripts\\m1_daily_update.py")
    engine_guard = text.index(
        "scripts\\m4_outcome_engine_freeze_guard.py"
    )
    assert engine_guard < m1_update
    assert "m4-outcome-engine-freeze-guard.json" in text
    assert (
        "outcome engine or active outcome protocol differs"
        in text
    )



def test_capture_wrapper_avoids_cmd_caret_revision_suffix() -> None:
    text = _wrapper_text()
    assert "git cat-file -e !M4_MIN_SAFE_COMMIT! >nul 2>nul" in text
    assert "!M4_MIN_SAFE_COMMIT!^{commit}" not in text



def test_capture_wrapper_runs_strict_qfq_readiness_before_capture() -> None:
    text = _wrapper_text()
    m1 = text.index("scripts\\m1_daily_update.py")
    qfq = text.index("scripts\\m4_prepare_qfq_universe.py")
    capture = text.index("scripts\\m4_capture_lifecycle_snapshot.py")
    assert m1 < qfq < capture
    assert 'if "!M1_EXIT!"=="0" if "!QFQ_EXIT!"=="0"' in text
    assert 'if not "!QFQ_EXIT!"=="0" set "FINAL_EXIT=1"' in text
    assert "m4-qfq-readiness.json" in text
    assert "m4-qfq-readiness.log" in text
    assert "M1/QFQ readiness did not pass" in text



def test_capture_wrapper_streams_qfq_progress_live() -> None:
    text = _wrapper_text()
    assert "Tee-Object -FilePath 'artifacts\\reports\\m4-qfq-readiness.log'" in text
    assert "scripts\\m4_prepare_qfq_universe.py" in text
    assert "> \"artifacts\\reports\\m4-qfq-readiness.log\" 2>&1" not in text
