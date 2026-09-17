import pandas as pd
import pytest

from htcn.research.source_terminal_bar import (
    SOURCE_TERMINAL_RESEARCH_DEFINITION,
    audit_source_prz_terminal_price_bar,
)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.date_range("2026-01-01", periods=9, freq="D"),
            "open": [101, 199, 139, 182, 130, 121.0, 120.0, 124.0, 130.0],
            "high": [102, 201, 140, 184, 132, 123.0, 121.0, 126.0, 132.0],
            "low": [99, 198, 137, 181, 128, 120.0, 119.0, 122.0, 128.0],
            "close": [101, 200, 138, 183, 130, 121.5, 120.5, 125.0, 131.0],
        }
    )


def _gartley_record() -> dict:
    return {
        "pattern_id": "gartley",
        "schema": "XABCD",
        "direction": "bullish",
        "signal_bar": 4,
        "prefix_points": [
            {"label": "X", "index": 0, "price": 100.0},
            {"label": "A", "index": 1, "price": 200.0},
            {"label": "B", "index": 2, "price": 138.2},
            {"label": "C", "index": 3, "price": 183.2},
        ],
        "prz": {"price_low": 50.0, "price_high": 60.0, "width": 10.0},
        "outcome": {
            "pre_signal_prz_touch_bar": None,
            "frontier_retired_at_bar": None,
            "completion_terminal_bar": None,
            "completion_confirmed_at_bar": None,
        },
    }


def _abcd_record() -> dict:
    return {
        "pattern_id": "abcd",
        "schema": "ABCD",
        "direction": "bullish",
        "signal_bar": 3,
        "prefix_points": [
            {"label": "A", "index": 0, "price": 200.0},
            {"label": "B", "index": 1, "price": 100.0},
            {"label": "C", "index": 2, "price": 161.8},
        ],
        "prz": {"price_low": 10.0, "price_high": 20.0, "width": 10.0},
        "outcome": {
            "pre_signal_prz_touch_bar": None,
            "frontier_retired_at_bar": None,
            "completion_terminal_bar": None,
            "completion_confirmed_at_bar": None,
        },
    }


def _abcd_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.date_range("2026-02-01", periods=9, freq="D"),
            "open": [200, 100, 161.8, 120, 90, 63.0, 70, 80, 90],
            "high": [201, 102, 163, 122, 92, 65.0, 72, 82, 92],
            "low": [198, 99, 160, 118, 88, 61.7, 68, 78, 88],
            "close": [200, 101, 161, 121, 90, 64.0, 71, 81, 91],
        }
    )


def _five_zero_record() -> dict:
    return {
        "pattern_id": "five_zero",
        "schema": "FIVE_ZERO",
        "direction": "bullish",
        "signal_bar": 4,
        "prefix_points": [
            {"label": "X", "index": 0, "price": 100.0},
            {"label": "A", "index": 1, "price": 120.0},
            {"label": "B", "index": 2, "price": 90.0},
            {"label": "C", "index": 3, "price": 156.0},
        ],
        # Deliberately wrong legacy zone. v5 must reconstruct 123..126 from X/A/B/C.
        "prz": {"price_low": 10.0, "price_high": 20.0, "width": 10.0},
        "outcome": {
            "pre_signal_prz_touch_bar": None,
            "frontier_retired_at_bar": None,
            "completion_terminal_bar": None,
            "completion_confirmed_at_bar": None,
        },
    }


def _five_zero_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.date_range("2026-03-01", periods=10, freq="D"),
            "open": [100, 120, 90, 156, 140, 128, 124, 126, 130, 134],
            "high": [102, 122, 92, 158, 142, 130, 127, 129, 133, 136],
            "low": [98, 118, 88, 154, 138, 127, 122, 124, 128, 132],
            "close": [101, 121, 91, 155, 140, 128, 126, 128, 132, 135],
        }
    )


def test_v5_terminal_audit_rebuilds_xabcd_source_raw_prz_instead_of_legacy_alias() -> None:
    audit = audit_source_prz_terminal_price_bar(
        _gartley_record(),
        frame=_frame(),
        forming_horizon=4,
        reaction_horizon=2,
    )

    assert audit["research_definition"] == SOURCE_TERMINAL_RESEARCH_DEFINITION
    assert SOURCE_TERMINAL_RESEARCH_DEFINITION == "m2-source-prz-v5"
    assert audit["prz_basis"] == "source_raw_prz"
    assert audit["status"] == "terminal_price_bar_observed"
    assert audit["first_prz_entry_bar"] == 5
    assert audit["terminal_bar"] == 6
    assert audit["terminal_price"] == pytest.approx(119.0)
    assert audit["prz"]["price_low"] > 100.0
    assert audit["prz"]["price_high"] > audit["prz"]["price_low"]
    assert audit["source_prz_component_names"] == [
        "XA completion",
        "BC projection x1.414",
        "AB=CD x1",
    ]
    assert audit["source_prz_defining_component"] == "XA completion"
    assert audit["prz"]["price_low"] != pytest.approx(50.0)


def test_v5_terminal_audit_rebuilds_standalone_abcd_source_raw_prz() -> None:
    audit = audit_source_prz_terminal_price_bar(
        _abcd_record(),
        frame=_abcd_frame(),
        forming_horizon=5,
        reaction_horizon=2,
    )
    assert audit["research_definition"] == SOURCE_TERMINAL_RESEARCH_DEFINITION
    assert audit["prz_basis"] == "source_raw_prz"
    assert audit["status"] == "terminal_price_bar_observed"
    assert audit["source_prz_component_names"] == ["AB=CD x1", "BC reciprocal"]
    assert audit["source_prz_defining_component"] == "AB=CD x1"
    assert audit["source_prz_selection_method"] == "abcd_equivalent_plus_reciprocal_bc"
    assert audit["prz"]["price_low"] == pytest.approx(61.8, abs=0.02)
    assert audit["prz"]["price_high"] == pytest.approx(61.8, abs=0.02)
    assert audit["prz"]["price_low"] != pytest.approx(10.0)


def test_v5_terminal_audit_rebuilds_five_zero_volume2_raw_prz_and_excludes_61_8() -> None:
    audit = audit_source_prz_terminal_price_bar(
        _five_zero_record(),
        frame=_five_zero_frame(),
        forming_horizon=4,
        reaction_horizon=2,
    )
    assert audit["research_definition"] == "m2-source-prz-v5"
    assert audit["prz_basis"] == "source_raw_prz"
    assert audit["status"] == "terminal_price_bar_observed"
    assert audit["first_prz_entry_bar"] == 6
    assert audit["terminal_bar"] == 6
    assert audit["terminal_price"] == pytest.approx(122.0)
    assert audit["prz"]["price_low"] == pytest.approx(123.0)
    assert audit["prz"]["price_high"] == pytest.approx(126.0)
    assert audit["source_prz_component_names"] == [
        "BC 50% structural completion",
        "Reciprocal AB=CD x1",
    ]
    assert "61.8" not in " ".join(audit["source_prz_component_names"])
    assert audit["source_prz_defining_component"] == "BC 50% structural completion"
    assert audit["source_prz_selection_method"] == "volume2_50_bc_plus_reciprocal_abcd"
    assert audit["prz"]["price_low"] != pytest.approx(10.0)

    # 5-0 Type-I targets must use the C->Terminal completion leg, not standard XABCD A->Terminal.
    assert audit["automatic_target_basis"] == "five_zero_c_to_terminal"
    assert audit["automatic_target_anchor_price"] == pytest.approx(156.0)
    assert audit["t1_price"] == pytest.approx(122.0 + 0.382 * 34.0)
    assert audit["t2_price"] == pytest.approx(122.0 + 0.618 * 34.0)
    assert audit["bars_from_terminal_to_t1"] == 3
    assert audit["t1_within_horizon"] is False
    assert audit["outcome_class"] == "no_t1_within_horizon"
    assert "C-to-Terminal" in audit["source_semantics"]["targets"]


def test_v5_terminal_audit_fails_closed_for_alternate_bat_source_conflict() -> None:
    record = _gartley_record()
    record["pattern_id"] = "alternate_bat"
    record["prefix_points"] = [
        {"label": "X", "index": 0, "price": 100.0},
        {"label": "A", "index": 1, "price": 200.0},
        {"label": "B", "index": 2, "price": 170.0},
        {"label": "C", "index": 3, "price": 188.54},
    ]
    audit = audit_source_prz_terminal_price_bar(
        record,
        frame=_frame(),
        forming_horizon=4,
    )
    assert audit["status"] == "source_prz_unresolved"
    assert audit["prz_basis"] == "none_fail_closed"
    assert audit["reason"] == "source_conflict"
