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
