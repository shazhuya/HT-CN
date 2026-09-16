from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from htcn.research.terminal_bar import (
    audit_projected_terminal_price_bar,
    build_terminal_bar_calibration,
)


def _frame() -> pd.DataFrame:
    rows = [
        ("2024-01-02", 111.0, 108.0, 110.0),
        ("2024-01-03", 109.0, 105.0, 107.0),
        # First PRZ entry: overlaps 90-100 but does not test the bullish extreme 90.
        ("2024-01-04", 104.0, 95.0, 99.0),
        # Official T-Bar: low tests through the final/extreme PRZ measurement.
        ("2024-01-05", 98.0, 89.0, 96.0),
        ("2024-01-08", 105.0, 101.0, 104.0),
        ("2024-01-09", 110.0, 106.0, 109.0),
        ("2024-01-10", 112.0, 108.0, 111.0),
        ("2024-01-11", 113.0, 109.0, 112.0),
    ]
    return pd.DataFrame(rows, columns=["trade_date", "high", "low", "close"])


def _forming_record() -> dict:
    return {
        "pattern_id": "abcd",
        "schema": "ABCD",
        "direction": "bullish",
        "signal_bar": 1,
        "signal_trade_date": "2024-01-03",
        "source_scale": 3,
        "signal_scales": [3],
        "prefix_points": [
            {"label": "A", "index": 0, "price": 120.0, "trade_date": "2024-01-02"},
            {"label": "B", "index": 0, "price": 105.0, "trade_date": "2024-01-02"},
            {"label": "C", "index": 1, "price": 110.0, "trade_date": "2024-01-03"},
        ],
        "terminal_pivot_bar": 1,
        "confirmation_lag_bars": 0,
        "prz": {"price_low": 90.0, "price_high": 100.0, "width": 10.0},
        "quality_at_signal": {"reference_span": 15.0},
        "outcome": {
            "pre_signal_prz_touch_bar": None,
            "frontier_retired_at_bar": 6,
            "completion_terminal_bar": 3,
            "completion_confirmed_at_bar": 5,
        },
    }


def test_terminal_bar_requires_extreme_prz_test_not_first_overlap() -> None:
    audit = audit_projected_terminal_price_bar(
        _forming_record(),
        frame=_frame(),
        forming_horizon=6,
        reaction_horizon=3,
    )
    assert audit["status"] == "terminal_price_bar_observed"
    assert audit["first_prz_entry_bar"] == 2
    assert audit["terminal_bar"] == 3
    assert audit["terminal_price"] == pytest.approx(89.0)
    assert audit["t1_name"] == "38.2%"
    assert audit["t1_price"] == pytest.approx(100.842)
    assert audit["t2_price"] == pytest.approx(108.158)
    assert audit["bars_from_terminal_to_t1"] == 1
    assert audit["bars_from_terminal_to_t2"] == 2
    assert audit["first_full_prz_exit_bar"] == 4
    assert audit["same_terminal_bar_as_later_confirmed_completion"] is True
    assert audit["bars_from_terminal_to_later_pivot_confirmation"] == 2


def test_prz_overlap_without_extreme_test_is_not_official_terminal_bar() -> None:
    frame = _frame().copy()
    frame.loc[3:, "low"] = [92.0, 101.0, 106.0, 108.0, 109.0]
    audit = audit_projected_terminal_price_bar(
        _forming_record(),
        frame=frame,
        forming_horizon=2,
        reaction_horizon=3,
    )
    assert audit["status"] == "no_terminal_price_bar_within_active_horizon"
    assert audit["first_prz_entry_bar"] == 2


def test_pre_signal_prz_test_remains_ineligible_for_terminal_execution_clock() -> None:
    record = _forming_record()
    record["outcome"] = dict(record["outcome"])
    record["outcome"]["pre_signal_prz_touch_bar"] = 1
    audit = audit_projected_terminal_price_bar(
        record,
        frame=_frame(),
        forming_horizon=6,
        reaction_horizon=3,
    )
    assert audit["status"] == "projection_late_before_signal"


def _calibration_row(index: int) -> dict:
    signal = date(2020, 1, 2) + timedelta(days=index * 10)
    t1 = index % 3 != 2
    t2 = index % 3 == 0
    outcome_class = "t2_within_horizon" if t2 else "t1_only_within_horizon" if t1 else "no_t1_within_horizon"
    return {
        "instrument_id": f"SSE.60{index:04d}",
        "pattern_id": "abcd" if index % 2 == 0 else "shark",
        "schema": "ABCD" if index % 2 == 0 else "0XABC",
        "direction": "bullish",
        "source_scale": 3 if index % 2 == 0 else 5,
        "terminal_bar_audit": {
            "status": "terminal_price_bar_observed",
            "terminal_bar": index,
            "terminal_trade_date": signal.isoformat(),
            "reaction_observation_end_trade_date": (signal + timedelta(days=2)).isoformat(),
            "available_future_bars_after_terminal": 20,
            "outcome_class": outcome_class,
            "bars_from_terminal_to_full_prz_exit": 2,
            "same_terminal_bar_as_later_confirmed_completion": index % 4 == 0,
        },
    }


def test_terminal_bar_calibration_has_independent_purged_sealed_holdout() -> None:
    rows = [_calibration_row(index) for index in range(20)]
    report = build_terminal_bar_calibration(
        rows,
        reaction_horizon=20,
        minimum_actionable_records=10,
        minimum_train_records=5,
        minimum_validation_records=2,
        minimum_holdout_records=2,
    )
    assert report["status"] == "terminal_bar_calibration_holdout_sealed"
    assert report["train"]["records"] > 0
    assert report["validation"]["records"] > 0
    assert report["holdout"]["sealed"] is True
    assert report["holdout"]["outcomes_exposed"] is False
    assert "t1_rate" not in report["holdout"]
