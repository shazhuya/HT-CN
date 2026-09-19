from __future__ import annotations

from htcn.app.integration_readiness import (
    ALLOWED_MAIN_ONLY_PATHS,
    EXPECTED_MAIN_HEAD,
    EXPECTED_MAIN_ONLY_COMMITS,
    EXPECTED_MERGE_BASE,
    REQUIRED_ANCESTOR_CHECKPOINTS,
    IntegrationSnapshot,
    evaluate_integration_snapshot,
)


def _snapshot(**overrides) -> IntegrationSnapshot:
    ancestry = {
        name: True
        for name, _ in REQUIRED_ANCESTOR_CHECKPOINTS
    }
    values = {
        "head": "f" * 40,
        "main_ref": "origin/main",
        "main_head": EXPECTED_MAIN_HEAD,
        "merge_base": EXPECTED_MERGE_BASE,
        "main_only_commit_count": 1,
        "lineage_only_commit_count": 630,
        "main_only_commits": EXPECTED_MAIN_ONLY_COMMITS,
        "main_only_paths": ALLOWED_MAIN_ONLY_PATHS,
        "main_readme_line_count": 1,
        "main_readme_sha256": "a" * 64,
        "checkpoint_ancestry": ancestry,
        "worktree_clean": True,
    }
    values.update(overrides)
    return IntegrationSnapshot(**values)


def test_ready_snapshot_requires_merge_commit_and_preserves_provenance() -> None:
    payload = evaluate_integration_snapshot(_snapshot())

    assert payload["status"] == "ready"
    assert payload["errors"] == []
    assert payload["merge_instruction"]["method"] == "merge"
    assert payload["merge_instruction"]["squash"] is False
    assert payload["merge_instruction"]["rebase"] is False
    assert payload["contract"]["squash_forbidden"] is True
    assert payload["contract"]["rebase_forbidden"] is True


def test_main_head_movement_blocks_integration() -> None:
    payload = evaluate_integration_snapshot(
        _snapshot(main_head="b" * 40)
    )

    assert payload["status"] == "blocked"
    assert any(
        error.startswith("main_head_moved:")
        for error in payload["errors"]
    )


def test_unexpected_main_only_path_blocks_integration() -> None:
    payload = evaluate_integration_snapshot(
        _snapshot(main_only_paths=("README.md", "src/htcn/core.py"))
    )

    assert payload["status"] == "blocked"
    assert any(
        error.startswith("main_only_paths_changed:")
        for error in payload["errors"]
    )


def test_missing_methodology_checkpoint_blocks_integration() -> None:
    ancestry = {
        name: True
        for name, _ in REQUIRED_ANCESTOR_CHECKPOINTS
    }
    ancestry["m4_methodology_freeze"] = False

    payload = evaluate_integration_snapshot(
        _snapshot(checkpoint_ancestry=ancestry)
    )

    assert payload["status"] == "blocked"
    assert any(
        "required_checkpoint_not_ancestor:m4_methodology_freeze"
        in error
        for error in payload["errors"]
    )


def test_suspiciously_short_lineage_blocks_integration() -> None:
    payload = evaluate_integration_snapshot(
        _snapshot(lineage_only_commit_count=100)
    )

    assert payload["status"] == "blocked"
    assert any(
        error.startswith("lineage_commit_count_too_small:")
        for error in payload["errors"]
    )


def test_dirty_tracked_worktree_blocks_integration() -> None:
    payload = evaluate_integration_snapshot(
        _snapshot(worktree_clean=False)
    )

    assert payload["status"] == "blocked"
    assert "tracked_worktree_not_clean" in payload["errors"]


def test_main_only_commit_set_is_exact_not_just_counted() -> None:
    payload = evaluate_integration_snapshot(
        _snapshot(main_only_commits=("c" * 40,))
    )

    assert payload["status"] == "blocked"
    assert any(
        error.startswith("main_only_commit_set_changed:")
        for error in payload["errors"]
    )
