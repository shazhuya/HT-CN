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


def _abcd_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.date_range("2026-02-01", periods=8, freq="D"),
            "open": [200.0, 100.0, 161.8, 120.0, 80.0, 62.0, 78.0, 100.0],
            "high": [201.0, 101.0, 162.0, 122.0, 82.0, 63.0, 80.0, 102.0],
            "low": [199.0, 99.0, 160.0, 118.0, 78.0, 61.7, 76.0, 98.0],
            "close": [200.0, 100.0, 161.8, 120.0, 80.0, 62.2, 79.0, 101.0],
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
        # Deliberately wrong legacy/ideal-core payload. v4 must ignore it and rebuild Raw PRZ.
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
        # Deliberately wrong legacy/ideal-core payload. v4 must rebuild from A/B/C.
        "prz": {"price_low": 150.0, "price_high": 160.0, "width": 10.0},
        "outcome": {
            "pre_signal_prz_touch_bar": None,
            "frontier_retired_at_bar": None,
            "completion_terminal_bar": None,
            "completion_confirmed_at_bar": None,
        },
    }


def test_v4_terminal_audit_rebuilds_xabcd_source_raw_prz_instead_of_legacy_alias() -> None:
    audit = audit_source_prz_terminal_price_bar(
        _gartley_record(),
        frame=_frame(),
        forming_horizon=4,
        reaction_horizon=2,
    )

    assert audit["research_definition"] == SOURCE_TERMINAL_RESEARCH_DEFINITION
    assert SOURCE_TERMINAL_RESEARCH_DEFINITION == "m2-source-prz-v4"
    assert audit["prz_basis"] == "source_raw_prz"
    assert audit["status"] == "terminal_price_bar_observed"
    assert audit["first_prz_entry_bar"] == 5
    assert audit["terminal_bar"] == 6
    assert audit["terminal_price"] == pytest.approx(119.0)
    assert audit["prz"]["price_low"] > 100.0
    assert audit["prz"]["price_high"] > audit["prz"]["price_low"]
    assert audit["prz"]["basis"] == "source_raw_prz"
    assert audit["source_prz_component_names"] == [
        "XA completion",
        "BC projection x1.414",
        "AB=CD x1",
    ]
    assert audit["source_prz_defining_component"] == "XA completion"
    assert audit["prz"]["price_low"] != pytest.approx(50.0)
    assert audit["prz"]["price_high"] != pytest.approx(60.0)


def test_v4_terminal_audit_rebuilds_abcd_source_raw_prz_and_observes_tbar() -> None:
    audit = audit_source_prz_terminal_price_bar(
        _abcd_record(),
        frame=_abcd_frame(),
        forming_horizon=4,
        reaction_horizon=2,
    )
    assert audit["research_definition"] == "m2-source-prz-v4"
    assert audit["status"] == "terminal_price_bar_observed"
    assert audit["prz_basis"] == "source_raw_prz"
    assert audit["first_prz_entry_bar"] == 5
    assert audit["terminal_bar"] == 5
    assert audit["terminal_price"] == pytest.approx(61.7)
    assert audit["source_prz_component_names"] == ["AB=CD x1", "BC reciprocal"]
    assert audit["source_prz_defining_component"] == "AB=CD x1"
    assert audit["source_prz_selection_method"] == "exact_abcd_plus_primary_reciprocal_bc"
    assert audit["prz"]["price_low"] == pytest.approx(61.8)
    assert audit["prz"]["price_high"] < 62.0
    assert audit["prz"]["price_low"] != pytest.approx(150.0)


def test_v4_terminal_audit_fails_closed_for_unsupported_schema() -> None:
    record = _gartley_record()
    record.update({"pattern_id": "shark", "schema": "0XABC"})
    audit = audit_source_prz_terminal_price_bar(
        record,
        frame=_frame(),
        forming_horizon=4,
    )
    assert audit["status"] == "source_prz_unresolved"
    assert audit["research_definition"] == "m2-source-prz-v4"
    assert audit["prz_basis"] == "none_fail_closed"
    assert audit["reason"] == "source_prz_not_frozen_for_schema"


def test_v4_terminal_audit_fails_closed_for_alternate_bat_source_conflict() -> None:
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
