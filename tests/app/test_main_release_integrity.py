from __future__ import annotations

from pathlib import Path

from htcn.app.main_release_integrity import (
    REQUIRED_RELEASE_ANCESTORS,
    MainReleaseSnapshot,
    evaluate_main_release_snapshot,
)


def _snapshot(**overrides) -> MainReleaseSnapshot:
    values = {
        "head": "f" * 40,
        "worktree_clean": True,
        "checkpoint_ancestry": {
            name: True
            for name, _ in REQUIRED_RELEASE_ANCESTORS
        },
    }
    values.update(overrides)
    return MainReleaseSnapshot(**values)


def test_release_snapshot_ready_when_all_required_ancestors_survive() -> None:
    payload = evaluate_main_release_snapshot(_snapshot())

    assert payload["status"] == "ready"
    assert payload["errors"] == []
    assert payload["contract"]["runs_on_main_push"] is True
    assert payload["contract"]["runs_on_pull_request_to_main"] is True
    assert payload["contract"]["full_history_required"] is True
    assert payload["contract"]["phase18_browser_acceptance_required"] is True
    assert payload["contract"]["phase21_browser_acceptance_required"] is True
    assert payload["contract"]["m4_methodology_freeze_required"] is True
    assert payload["contract"]["m4_outcome_engine_freeze_required"] is True


def test_release_snapshot_blocks_missing_phase21_merge_ancestry() -> None:
    ancestry = {
        name: True
        for name, _ in REQUIRED_RELEASE_ANCESTORS
    }
    ancestry["m5_phase21_main_merge"] = False

    payload = evaluate_main_release_snapshot(
        _snapshot(checkpoint_ancestry=ancestry)
    )

    assert payload["status"] == "blocked"
    assert (
        "required_release_checkpoint_not_ancestor:"
        "m5_phase21_main_merge"
    ) in payload["errors"]


def test_release_snapshot_blocks_methodology_or_outcome_ancestry_loss() -> None:
    ancestry = {
        name: True
        for name, _ in REQUIRED_RELEASE_ANCESTORS
    }
    ancestry["m4_methodology_freeze"] = False
    ancestry["m4_outcome_engine_anchor"] = False

    payload = evaluate_main_release_snapshot(
        _snapshot(checkpoint_ancestry=ancestry)
    )

    assert payload["status"] == "blocked"
    assert any(
        "m4_methodology_freeze" in error
        and "m4_outcome_engine_anchor" in error
        for error in payload["errors"]
    )


def test_release_snapshot_blocks_checkpoint_set_drift() -> None:
    ancestry = {
        name: True
        for name, _ in REQUIRED_RELEASE_ANCESTORS
    }
    ancestry.pop("m3_merge")
    ancestry["unexpected"] = True

    payload = evaluate_main_release_snapshot(
        _snapshot(checkpoint_ancestry=ancestry)
    )

    assert payload["status"] == "blocked"
    assert any(
        error.startswith("checkpoint_set_mismatch:")
        for error in payload["errors"]
    )


def test_release_snapshot_blocks_dirty_tracked_worktree() -> None:
    payload = evaluate_main_release_snapshot(
        _snapshot(worktree_clean=False)
    )

    assert payload["status"] == "blocked"
    assert "tracked_worktree_not_clean" in payload["errors"]


def test_release_snapshot_rejects_invalid_head_shape() -> None:
    payload = evaluate_main_release_snapshot(
        _snapshot(head="short")
    )

    assert payload["status"] == "blocked"
    assert "head_sha_invalid" in payload["errors"]


def test_main_release_workflow_contract_is_present_and_full_history() -> None:
    root = Path(__file__).resolve().parents[2]
    workflow = (
        root / ".github" / "workflows" / "ci.yml"
    ).read_text(encoding="utf-8")

    required_snippets = (
        "main-release-integrity:",
        "name: formal-main-release-integrity",
        "github.ref == 'refs/heads/main' || github.base_ref == 'main'",
        "needs: deterministic-tests",
        "fetch-depth: 0",
        "python scripts/m5_main_release_integrity.py",
        "tests/smoke.spec.ts",
        "tests/review-followup-journal.spec.ts",
        "python scripts/m5_build_portable_visual_browser_fixture.py",
        "tests/portable-visual-workspace.spec.ts",
        "python scripts/m5_verify_portable_visual_browser_evidence.py",
        "python scripts/m5_prepare_main_real_browser_audit.py --fixture",
        "tests/main-real-portable-delivery.spec.ts",
        "python scripts/m5_verify_main_real_browser_evidence.py",
        "python scripts/m4_methodology_freeze_guard.py",
        "python scripts/m4_outcome_engine_freeze_guard.py",
        "m5-main-release-integrity.json",
    )
    for snippet in required_snippets:
        assert snippet in workflow


def test_main_release_workflow_is_additive_not_replacement() -> None:
    root = Path(__file__).resolve().parents[2]
    workflow = (
        root / ".github" / "workflows" / "ci.yml"
    ).read_text(encoding="utf-8")

    assert "deterministic-tests:" in workflow
    assert "main-release-integrity:" in workflow
    assert workflow.index("deterministic-tests:") < workflow.index(
        "main-release-integrity:"
    )
