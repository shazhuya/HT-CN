from __future__ import annotations

from htcn.app.daily_close_runner import evaluate_daily_close_preflight


def test_daily_close_preflight_accepts_clean_named_branch() -> None:
    result = evaluate_daily_close_preflight(
        branch="m5/daily-close-pipeline",
        head="abc123",
        porcelain="",
        repository_available=True,
        catalog_available=True,
    )

    assert result.passed is True
    assert result.errors == ()
    assert result.branch == "m5/daily-close-pipeline"


def test_daily_close_preflight_rejects_detached_head() -> None:
    result = evaluate_daily_close_preflight(
        branch=None,
        head="abc123",
        porcelain="",
        repository_available=True,
        catalog_available=True,
    )

    assert result.passed is False
    assert "named_branch_unavailable_or_detached_head" in result.errors


def test_daily_close_preflight_rejects_dirty_worktree() -> None:
    result = evaluate_daily_close_preflight(
        branch="m5/daily-close-pipeline",
        head="abc123",
        porcelain=" M tracked.txt\n",
        repository_available=True,
        catalog_available=True,
    )

    assert result.passed is False
    assert "worktree_not_clean" in result.errors


def test_daily_close_preflight_does_not_require_m4_branch_name() -> None:
    result = evaluate_daily_close_preflight(
        branch="m5/product-branch",
        head="abc123",
        porcelain="",
        repository_available=True,
        catalog_available=True,
    )

    assert result.passed is True


def test_daily_close_preflight_requires_real_m1_catalog() -> None:
    result = evaluate_daily_close_preflight(
        branch="m5/daily-close-pipeline",
        head="abc123",
        porcelain="",
        repository_available=True,
        catalog_available=False,
    )

    assert result.passed is False
    assert "m1_catalog_missing" in result.errors
