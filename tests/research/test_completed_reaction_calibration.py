from __future__ import annotations

from datetime import date, timedelta

from htcn.research.completed_reaction_calibration import (
    actionable_completed_reaction_records,
    attach_completed_reaction_observation_windows,
    build_completed_reaction_calibration,
    redact_completed_reaction_holdout,
)


def _row(
    index: int,
    *,
    outcome_class: str = "t2_within_horizon",
    late: bool = False,
    available: int = 20,
    observation_days: int = 20,
    family: str = "ABCD",
) -> dict:
    signal = date(2020, 1, 1) + timedelta(days=index * 10)
    observation_end = signal + timedelta(days=observation_days)
    pattern_id = {
        "ABCD": "abcd",
        "SHARK": "shark",
        "FIVE_ZERO": "five_zero",
    }[family]
    return {
        "instrument_id": f"SSE.60{index:04d}",
        "pattern_id": pattern_id,
        "pattern_family": family,
        "schema": family,
        "direction": "bullish",
        "source_scale": 5,
        "geometry_score": 80.0,
        "signal_bar": index * 10,
        "signal_trade_date": signal.isoformat(),
        "observation_end_trade_date": observation_end.isoformat(),
        "outcome": {
            "outcome_class": outcome_class,
            "late_completion_signal": late,
            "available_future_bars_after_confirmation": available,
            "confirmation_lag_bars": 5,
        },
    }


def test_attach_observation_window_uses_trading_bar_horizon() -> None:
    dates = [date(2024, 1, 1) + timedelta(days=index) for index in range(8)]
    row = _row(0)
    row["signal_bar"] = 2
    enriched = attach_completed_reaction_observation_windows([row], trade_dates=dates, horizon=3)
    assert enriched[0]["observation_end_bar"] == 5
    assert enriched[0]["observation_end_trade_date"] == "2024-01-06"
    assert enriched[0]["confirmation_lag_bars"] == 5


def test_actionable_filter_excludes_late_and_immature() -> None:
    rows = [
        _row(0),
        _row(1, late=True, outcome_class="late_completion_signal"),
        _row(2, available=10, outcome_class="immature"),
        _row(3, outcome_class="no_t1_within_horizon"),
    ]
    selected = actionable_completed_reaction_records(rows, horizon=20)
    assert [row["signal_bar"] for row in selected] == [0, 30]


def test_calibration_seals_holdout_outcomes() -> None:
    rows = [
        _row(
            index,
            outcome_class=(
                "t2_within_horizon"
                if index % 3 == 0
                else "t1_only_within_horizon"
                if index % 3 == 1
                else "no_t1_within_horizon"
            ),
            family="ABCD" if index % 2 == 0 else "SHARK",
            observation_days=2,
        )
        for index in range(20)
    ]
    report = build_completed_reaction_calibration(
        rows,
        horizon=20,
        minimum_actionable_records=10,
        minimum_train_records=5,
        minimum_validation_records=2,
        minimum_holdout_records=2,
    )
    assert report["status"] == "completed_reaction_calibration_holdout_sealed"
    assert report["holdout"]["sealed"] is True
    assert report["holdout"]["outcomes_exposed"] is False
    assert "t1_rate" not in report["holdout"]
    assert "by_outcome" not in report["holdout"]
    assert report["train"]["records"] > 0
    assert report["validation"]["records"] > 0

    emitted = redact_completed_reaction_holdout(rows, report)
    holdout_start = report["boundaries"]["holdout_start"]
    for row in emitted:
        if row["signal_trade_date"] >= holdout_start:
            assert row["outcome"] == {"sealed": True}
            assert row["holdout_outcome_sealed"] is True
        else:
            assert row["holdout_outcome_sealed"] is False
            assert "outcome_class" in row["outcome"]


def test_sample_floor_reports_insufficient_without_opening_holdout() -> None:
    rows = [_row(index, observation_days=2) for index in range(12)]
    report = build_completed_reaction_calibration(
        rows,
        horizon=20,
        minimum_actionable_records=60,
        minimum_train_records=30,
        minimum_validation_records=10,
        minimum_holdout_records=10,
    )
    assert report["status"] == "completed_reaction_sample_insufficient_holdout_sealed"
    assert report["reason"] == "actionable_completed_reaction_sample_below_research_floor_after_purge"
    assert report["holdout"]["sealed"] is True
    assert report["holdout"]["outcomes_exposed"] is False


def test_purge_removes_labels_that_cross_next_split() -> None:
    rows = [_row(index, observation_days=2) for index in range(10)]
    rows[5]["observation_end_trade_date"] = "2030-01-01"
    report = build_completed_reaction_calibration(
        rows,
        horizon=20,
        minimum_actionable_records=1,
        minimum_train_records=1,
        minimum_validation_records=1,
        minimum_holdout_records=1,
    )
    assert report["purged_records"] >= 1
    assert sum(report["purge_reasons"].values()) == report["purged_records"]
