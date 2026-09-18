from __future__ import annotations

from htcn.app.daily_close_runner import evaluate_daily_close_preflight


def test_dirty_worktree_blocks_research_but_not_product_lane() -> None:
    result = evaluate_daily_close_preflight(
        branch="m5/daily-close-product-pipeline",
        head="abc123",
        porcelain=" M tracked.txt\n",
        repository_available=True,
        catalog_available=True,
    )

    assert result.product_lane_ready is True
    assert result.research_lane_ready is False
    assert "worktree_not_clean" in result.research_errors


def test_detached_head_blocks_research_but_not_product_lane() -> None:
    result = evaluate_daily_close_preflight(
        branch=None,
        head="abc123",
        porcelain="",
        repository_available=True,
        catalog_available=True,
    )

    assert result.product_lane_ready is True
    assert result.research_lane_ready is False
    assert (
        "named_branch_unavailable_or_detached_head"
        in result.research_errors
    )


def test_missing_catalog_blocks_both_lanes() -> None:
    result = evaluate_daily_close_preflight(
        branch="m5/daily-close-product-pipeline",
        head="abc123",
        porcelain="",
        repository_available=True,
        catalog_available=False,
    )

    assert result.product_lane_ready is False
    assert result.research_lane_ready is False
    assert "m1_catalog_missing" in result.product_errors


def test_clean_named_branch_allows_both_lanes() -> None:
    result = evaluate_daily_close_preflight(
        branch="m5/daily-close-product-pipeline",
        head="abc123",
        porcelain="",
        repository_available=True,
        catalog_available=True,
    )

    assert result.product_lane_ready is True
    assert result.research_lane_ready is True
