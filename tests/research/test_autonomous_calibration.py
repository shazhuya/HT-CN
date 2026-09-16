from __future__ import annotations

import pandas as pd

from htcn.research.autonomous_calibration import (
    build_autonomous_quality_report,
    enrich_walk_forward_records,
)


def test_enrich_walk_forward_records_uses_exact_future_trade_date() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": pd.bdate_range("2024-01-02", periods=20),
            "high": range(20),
            "low": range(20),
            "close": range(20),
        }
    )
    records = [
        {
            "signal_bar": 5,
            "signal_trade_date": "2024-01-09",
            "outcome": {"available_future_bars": 14, "pre_signal_prz_touch_bar": None},
        }
    ]
    enriched = enrich_walk_forward_records(
        records,
        frame=frame,
        instrument_id="SSE.600519",
        horizon=5,
    )
    assert enriched[0]["instrument_id"] == "SSE.600519"
    assert enriched[0]["observation_end_bar"] == 10
    assert enriched[0]["observation_end_trade_date"] == frame.iloc[10]["trade_date"].date().isoformat()
    assert enriched[0]["terminal_bar_audit"]["status"] == "not_applicable_missing_projection_fields"
    assert set(enriched[0]["terminal_bar_audit"]["missing_fields"]) == {
        "pattern_id",
        "schema",
        "direction",
        "prz",
        "prefix_points",
    }


def _record(index: int) -> dict:
    signal = pd.Timestamp("2020-01-01") + pd.Timedelta(days=index)
    observation_end = signal + pd.Timedelta(days=3)
    touched = index % 3 == 0
    completed = index % 17 == 0
    retired = not touched
    return {
        "instrument_id": f"SSE.{600000 + (index % 4):06d}",
        "signal_trade_date": signal.date().isoformat(),
        "observation_end_trade_date": observation_end.date().isoformat(),
        "signal_bar": index,
        "pattern_id": "bat" if index % 2 == 0 else "gartley",
        "schema": "XABCD",
        "direction": "bullish" if index % 2 == 0 else "bearish",
        "source_scale": (3, 5, 8, 13)[index % 4],
        "signal_scales": [3, 5] if index % 5 == 0 else [3],
        "confirmation_lag_bars": index % 8,
        "quality_at_signal": {
            "prz_width_ratio": 0.01 + (index % 10) * 0.002,
            "distance_to_prz_ratio": 0.02 + (index % 7) * 0.003,
            "source_tolerance_used": index % 6 == 0,
        },
        "outcome": {
            "pre_signal_prz_touch_bar": None,
            "available_future_bars": 100,
            "bars_to_first_future_prz_touch": 2 if touched else None,
            "touch_before_retirement": touched,
            "bars_to_completion_confirmation": 3 if completed else None,
            "completion_before_retirement": completed,
            "bars_to_frontier_retirement": None if touched else 2,
        },
    }


def test_autonomous_report_keeps_holdout_sealed() -> None:
    report = build_autonomous_quality_report(
        [_record(index) for index in range(100)],
        horizon=3,
        minimum_mature_records=30,
    )
    assert report["status"] == "research_quality_evidence_holdout_sealed"
    assert report["holdout"]["sealed"] is True
    assert report["holdout"]["outcomes_reported"] is False
    assert report["policy_frozen"] is False
    assert report["anti_leakage"]["numeric_thresholds_train_only"] is True
    assert report["quality_gate"]["holdout_opened"] is False
    assert report["manifest"]["purged_boundary_records"] > 0
