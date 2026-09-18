from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WRAPPER = ROOT / "运行M4真实A股生命周期快照.bat"
MIN_SAFE_COMMIT = "3bd0c236d5f1318caf0b6125f9f99ef1f113e0af"
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


def test_capture_wrapper_fails_closed_before_authoritative_capture() -> None:
    text = _wrapper_text()
    assert "No M1 update or authoritative capture was started." in text
    assert "worktree is not clean before M1 update" in text
    assert "current HEAD predates or diverges from the frozen T1 protocol" in text
    assert "scripts\\m4_capture_lifecycle_snapshot.py" in text
