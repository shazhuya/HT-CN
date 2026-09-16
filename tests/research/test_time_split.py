from __future__ import annotations

from datetime import date, timedelta

from htcn.research.time_split import (
    SplitBoundaries,
    assign_purged_split,
    derive_boundaries,
    learn_numeric_thresholds,
    mature_forward_records,
    signal_features,
)


def _row(day: int, *, end_day: int | None = None, outcome_class: str = "x") -> dict:
    base = date(2020, 1, 1)
    signal_date = base + timedelta(days=day)
    observation_end = base + timedelta(days=end_day if end_day is not None else day + 5)
    return {
        "instrument_id": "SSE.600000",
        "pattern_id": "bat",
        "schema": "XABCD",
        "direction": "bullish",
        "signal_trade_date": signal_date.isoformat(),
        "observation_end_trade_date": observation_end.isoformat(),
        "signal_bar": day,
        "source_scale": 5,
        "signal_scales": [3, 5],
        "confirmation_lag_bars": float(day % 7),
        "quality_at_signal": {
            "prz_width_ratio": 0.01 * (day + 1),
            "distance_to_prz_ratio": 0.02 * (day + 1),
            "source_tolerance_used": False,
        },
        "outcome": {
            "pre_signal_prz_touch_bar": None,
            "available_future_bars": 100,
            "outcome_class": outcome_class,
            "touch_before_retirement": False,
            "completion_before_retirement": False,
            "bars_to_first_future_prz_touch": None,
            "bars_to_completion_confirmation": None,
            "bars_to_frontier_retirement": 10,
        },
    }


def test_mature_filter_excludes_late_and_immature() -> None:
    good = _row(1)
    late = _row(2)
    late["outcome"]["pre_signal_prz_touch_bar"] = 2
    immature = _row(3)
    immature["outcome"]["available_future_bars"] = 59
    assert mature_forward_records([good, late, immature], horizon=60) == [good]


def test_boundaries_depend_on_dates_not_outcomes() -> None:
    rows_a = [_row(i, outcome_class="A") for i in range(20)]
    rows_b = [_row(i, outcome_class="B") for i in range(20)]
    assert derive_boundaries(rows_a) == derive_boundaries(rows_b)


def test_purge_removes_label_windows_crossing_next_split() -> None:
    rows = [_row(i, end_day=i + 1) for i in range(12)]
    boundaries = SplitBoundaries(
        train_end=_row(4)["signal_trade_date"],
        validation_start=_row(5)["signal_trade_date"],
        validation_end=_row(8)["signal_trade_date"],
        holdout_start=_row(9)["signal_trade_date"],
    )
    # Force one train record and one validation record to leak across the next boundary.
    rows[4]["observation_end_trade_date"] = _row(5)["signal_trade_date"]
    rows[8]["observation_end_trade_date"] = _row(9)["signal_trade_date"]
    splits, purged = assign_purged_split(rows, boundaries)
    assert rows[4] not in splits["train"]
    assert rows[8] not in splits["validation"]
    assert len(purged) == 2
    assert {row["purge_reason"] for row in purged} == {
        "train_label_crosses_validation_start",
        "validation_label_crosses_holdout_start",
    }


def test_numeric_thresholds_are_train_only() -> None:
    train = [_row(i) for i in range(8)]
    validation = [_row(50 + i) for i in range(8)]
    thresholds = learn_numeric_thresholds(train)
    assert thresholds.prz_width_ratio[2] < validation[0]["quality_at_signal"]["prz_width_ratio"]
    features = signal_features(validation[0], thresholds)
    assert features["prz_width_bucket"] == "Q4_high"
    assert features["distance_to_prz_bucket"] == "Q4_high"


def test_outcome_changes_do_not_change_signal_features() -> None:
    row_a = _row(4, outcome_class="success")
    row_b = _row(4, outcome_class="failure")
    thresholds = learn_numeric_thresholds([_row(i) for i in range(10)])
    assert signal_features(row_a, thresholds) == signal_features(row_b, thresholds)
