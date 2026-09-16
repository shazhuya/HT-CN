from __future__ import annotations

import pandas as pd

from htcn.harmonic.models import PatternDirection
from htcn.research.completed_reaction import (
    audit_confirmed_reaction,
    completed_reaction_summary,
)


def _frame(highs: list[float], lows: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.date_range("2025-01-01", periods=len(highs), freq="D"),
            "open": [(h + l) / 2 for h, l in zip(highs, lows)],
            "high": highs,
            "low": lows,
            "close": [(h + l) / 2 for h, l in zip(highs, lows)],
            "volume": [1.0] * len(highs),
        }
    )


def test_confirmation_clock_does_not_credit_preconfirmation_reaction() -> None:
    frame = _frame(
        [100, 100, 100, 100, 112, 114, 108, 111, 121, 126, 127, 128],
        [99, 99, 99, 99, 100, 102, 101, 103, 105, 108, 109, 110],
    )
    audit = audit_confirmed_reaction(
        frame,
        d_index=3,
        confirmation_bar=5,
        direction=PatternDirection.BULLISH,
        t1_name="38.2%",
        t1_price=110.0,
        t2_name="61.8%",
        t2_price=120.0,
        horizon=4,
    )
    assert audit["pre_confirmation_t1_hit"] is True
    assert audit["late_completion_signal"] is True
    assert audit["bars_from_confirmation_to_t1"] == 3
    assert audit["bars_from_confirmation_to_t2"] == 3
    assert audit["outcome_class"] == "late_completion_signal"


def test_confirmation_clock_measures_only_future_bars() -> None:
    frame = _frame(
        [100, 100, 100, 100, 105, 108, 111, 116, 121, 126, 127, 128],
        [99, 99, 99, 99, 100, 102, 103, 106, 109, 112, 113, 114],
    )
    audit = audit_confirmed_reaction(
        frame,
        d_index=3,
        confirmation_bar=5,
        direction=PatternDirection.BULLISH,
        t1_name="38.2%",
        t1_price=110.0,
        t2_name="61.8%",
        t2_price=120.0,
        horizon=4,
    )
    assert audit["pre_confirmation_t1_hit"] is False
    assert audit["bars_from_confirmation_to_t1"] == 1
    assert audit["bars_from_confirmation_to_t2"] == 3
    assert audit["outcome_class"] == "t2_within_horizon"


def test_completed_reaction_summary_excludes_late_and_immature_from_actionable_rates() -> None:
    rows = [
        {
            "pattern_id": "bat",
            "pattern_family": "XABCD",
            "outcome": {"outcome_class": "t2_within_horizon"},
        },
        {
            "pattern_id": "abcd",
            "pattern_family": "ABCD",
            "outcome": {"outcome_class": "t1_only_within_horizon"},
        },
        {
            "pattern_id": "shark",
            "pattern_family": "SHARK",
            "outcome": {"outcome_class": "no_t1_within_horizon"},
        },
        {
            "pattern_id": "bat",
            "pattern_family": "XABCD",
            "outcome": {"outcome_class": "late_completion_signal"},
        },
        {
            "pattern_id": "five_zero",
            "pattern_family": "FIVE_ZERO",
            "outcome": {"outcome_class": "immature"},
        },
    ]
    report = completed_reaction_summary(rows)
    assert report["records"] == 5
    assert report["mature_actionable_records"] == 3
    assert report["late_completion_signals"] == 1
    assert report["immature_records"] == 1
    assert report["t1_within_horizon"] == 2
    assert report["t2_within_horizon"] == 1
    assert report["t1_rate_actionable"] == 2 / 3
    assert report["t2_rate_actionable"] == 1 / 3
