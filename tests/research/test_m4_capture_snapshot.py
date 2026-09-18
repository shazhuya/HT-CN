from __future__ import annotations

from collections import Counter

from scripts.m4_capture_lifecycle_snapshot import _summary_counter


def test_snapshot_summary_is_transparent_raw_count_not_score() -> None:
    assert _summary_counter(["waiting", "waiting", "execution_evaluation"]) == {
        "execution_evaluation": 1,
        "waiting": 2,
    }


def test_counter_has_no_weighting_or_rank_semantics() -> None:
    values = ["type_i_confirmed", "waiting_terminal", "waiting_terminal"]
    summary = _summary_counter(values)
    assert summary == dict(sorted(Counter(values).items()))
    assert "score" not in summary


def test_partial_universe_is_diagnostic_only() -> None:
    # The authoritative capture contract must never treat max_symbols as full coverage.
    # This test intentionally checks the source-level contract without requiring M1.
    import inspect
    from scripts import m4_capture_lifecycle_snapshot as capture

    source = inspect.getsource(capture.run)
    assert 'diagnostic_partial_universe_no_commit' in source
    assert 'authoritative transaction/journal/manifest writes are disabled' in source
