from __future__ import annotations

import pandas as pd

from htcn.research.quality_robustness import build_quality_robustness_report


def _records() -> list[dict]:
    rows: list[dict] = []
    dates = pd.date_range("2020-01-01", periods=120, freq="D")
    for symbol_index in range(8):
        symbol = f"SSE.{600000 + symbol_index:06d}"
        for index, signal_date in enumerate(dates):
            near = index % 2 == 0
            touched = near
            rows.append(
                {
                    "instrument_id": symbol,
                    "signal_trade_date": signal_date.date().isoformat(),
                    "observation_end_trade_date": (
                        signal_date + pd.Timedelta(3, unit="D")
                    ).date().isoformat(),
                    "signal_bar": index,
                    "pattern_id": "bat" if symbol_index % 2 == 0 else "gartley",
                    "schema": "XABCD",
                    "direction": "bullish" if symbol_index % 2 == 0 else "bearish",
                    "source_scale": 5,
                    "signal_scales": [3, 5],
                    "confirmation_lag_bars": 3,
                    "quality_at_signal": {
                        "prz_width_ratio": 0.02 if near else 0.20,
                        "distance_to_prz_ratio": 0.10 if near else 0.90,
                        "source_tolerance_used": False,
                    },
                    "outcome": {
                        "pre_signal_prz_touch_bar": None,
                        "available_future_bars": 10,
                        "bars_to_first_future_prz_touch": 1 if touched else None,
                        "touch_before_retirement": touched,
                        "bars_to_completion_confirmation": None,
                        "completion_before_retirement": False,
                        "bars_to_frontier_retirement": None if touched else 1,
                    },
                }
            )
    return rows


def test_robustness_keeps_holdout_sealed_and_rewards_broad_stability() -> None:
    report = build_quality_robustness_report(_records(), horizon=3, min_mature_records=100)
    assert report["status"] == "research_robustness_holdout_sealed"
    assert report["holdout_opened"] is False
    assert report["policy_frozen"] is False
    assert report["holdout_records_sealed"] > 0
    assert "near_prz_q1" in report["strong_candidates_in"]
    assert "near_prz_q1" in report["robust_research_candidates"]
    gate = next(row for row in report["gates"] if row["name"] == "near_prz_q1")
    assert gate["symbol_concentration_ok"] is True
    assert gate["cross_section_ok"] is True
    assert gate["leave_one_symbol_out_ok"] is True
    assert gate["temporal_stability_ok"] is True
