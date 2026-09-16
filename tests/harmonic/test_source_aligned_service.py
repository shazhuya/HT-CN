import pandas as pd
import pytest

from htcn.app.source_aligned_service import SourceAlignedHarmonicService
from htcn.harmonic.abcd import project_forming_abcd
from htcn.harmonic.models import HarmonicPoint, PatternDirection
from htcn.harmonic.prz import PRZComponent, PotentialReversalZone


def _component(low: float = 90.0, high: float = 100.0) -> PRZComponent:
    return PRZComponent(
        name="source-test",
        price_low=low,
        price_high=high,
        ratio_low=1.0,
        ratio_high=1.0,
    )


def test_prz_api_contract_separates_three_static_layers_and_keeps_legacy_aliases() -> None:
    prz = PotentialReversalZone(
        pattern_id="test",
        direction=PatternDirection.BULLISH,
        components=(_component(),),
    )
    payload = SourceAlignedHarmonicService._prz_payload(prz)

    assert payload["semantics_version"] == 2
    assert payload["legacy_price_semantics"] == "ideal_core"
    assert payload["price_low"] == pytest.approx(payload["ideal_core"]["price_low"])
    assert payload["price_high"] == pytest.approx(payload["ideal_core"]["price_high"])
    assert payload["component_envelope"]["price_low"] == pytest.approx(90.0)
    assert payload["component_envelope"]["price_high"] == pytest.approx(100.0)
    assert payload["source_prz"]["available"] is False
    assert payload["source_prz"]["status"] == "unresolved_fail_closed"
    assert payload["source_prz"]["price_low"] is None
    assert payload["source_prz"]["price_high"] is None
    assert payload["source_prz"]["component_names"] == []
    assert payload["source_prz"]["unresolved_reason"] is None


def test_frozen_source_prz_is_explicit_and_not_inferred_from_ideal_core() -> None:
    prz = PotentialReversalZone(
        pattern_id="test",
        direction=PatternDirection.BULLISH,
        components=(_component(88.0, 102.0),),
        source_prz_low=90.0,
        source_prz_high=100.0,
    )
    payload = SourceAlignedHarmonicService._prz_payload(prz)
    source = payload["source_prz"]

    assert source["available"] is True
    assert source["price_low"] == pytest.approx(90.0)
    assert source["price_high"] == pytest.approx(100.0)
    assert source["width"] == pytest.approx(10.0)
    assert source["status"] == "frozen"
    assert source["component_names"] == []
    assert source["defining_component"] is None
    assert source["selection_method"] is None
    assert source["source_refs"] == []
    assert source["source_note"] is None
    assert source["unresolved_reason"] is None
    assert source["profile_version"] == 1
    assert payload["component_envelope"]["price_low"] == pytest.approx(88.0)
    assert payload["component_envelope"]["price_high"] == pytest.approx(102.0)


def _forming_payload(prz: PotentialReversalZone) -> dict:
    return {
        "pattern_id": "gartley",
        "schema": "XABCD",
        "direction": "bullish",
        "state": "forming",
        "scale": 1,
        "points": [
            {"label": "X", "index": 0, "price": 80.0},
            {"label": "A", "index": 1, "price": 120.0},
            {"label": "B", "index": 2, "price": 95.0},
            {"label": "C", "index": 3, "price": 110.0},
        ],
        "prz": SourceAlignedHarmonicService._prz_payload(prz),
    }


def _abcd_forming_payload() -> dict:
    points = (
        HarmonicPoint("A", 0, 200.0),
        HarmonicPoint("B", 1, 100.0),
        HarmonicPoint("C", 2, 161.8),
    )
    projection = project_forming_abcd(points)
    assert projection is not None
    return {
        "pattern_id": "abcd",
        "schema": "ABCD",
        "direction": projection.direction.value,
        "state": "forming",
        "scale": 1,
        "points": [
            {"label": point.label, "index": point.index, "price": point.price}
            for point in projection.points
        ],
        "prz": SourceAlignedHarmonicService._prz_payload(projection.prz),
        "metrics": {
            "c_ab": projection.c_ab,
            "reciprocal_c_target": projection.reciprocal_c_target,
            "reciprocal_bc_target": projection.reciprocal_bc_target,
        },
    }


def test_forming_execution_clock_starts_after_confirmed_frontier_and_fails_closed_without_source_prz() -> None:
    frame = pd.DataFrame(
        {
            "high": [82, 122, 97, 112, 111, 105, 101, 108],
            "low": [78, 118, 93, 108, 104, 95, 89, 102],
        }
    )
    unresolved = PotentialReversalZone(
        pattern_id="gartley",
        direction=PatternDirection.BULLISH,
        components=(_component(),),
    )
    clock = SourceAlignedHarmonicService._execution_clock_from_forming_payload(
        _forming_payload(unresolved),
        frame,
    )

    assert clock is not None
    assert clock["signal_bar"] == 4
    assert clock["signal_clock_basis"] == "last_frontier_pivot_confirmed_at=index+scale"
    assert clock["retrospective_d_clock_used"] is False
    assert clock["state"] == "source_prz_unresolved"
    assert clock["pez"]["available"] is False


def test_terminal_bar_creates_dynamic_pez_only_after_source_prz_is_frozen() -> None:
    frame = pd.DataFrame(
        {
            "high": [82, 122, 97, 112, 111, 105, 101, 108],
            "low": [78, 118, 93, 108, 104, 95, 89, 102],
        }
    )
    frozen = PotentialReversalZone(
        pattern_id="gartley",
        direction=PatternDirection.BULLISH,
        components=(_component(),),
        source_prz_low=90.0,
        source_prz_high=100.0,
    )
    clock = SourceAlignedHarmonicService._execution_clock_from_forming_payload(
        _forming_payload(frozen),
        frame,
    )

    assert clock is not None
    assert clock["signal_bar"] == 4
    assert clock["first_prz_entry_bar"] == 5
    assert clock["terminal_bar"] == 6
    assert clock["terminal_price"] == pytest.approx(89.0)
    assert clock["execution_start_bar"] == 7
    assert clock["pez"] == {
        "available": True,
        "price_low": 89.0,
        "price_high": 100.0,
        "status": "terminal_integrated_execution_zone",
    }
    assert clock["target_382"] > 89.0
    assert clock["target_618"] > clock["target_382"]


def test_abcd_product_payload_exposes_source_prz_separate_layer_and_execution_clock() -> None:
    pattern = _abcd_forming_payload()
    source = pattern["prz"]["source_prz"]
    assert source["available"] is True
    assert source["status"] == "frozen"
    assert source["component_names"] == ["AB=CD x1", "BC reciprocal"]
    assert source["defining_component"] == "AB=CD x1"
    assert source["selection_method"] == "exact_abcd_plus_primary_reciprocal_bc"
    assert source["evidence_level"].startswith("source_specification_plus_market_examples")
    assert source["selection_authority"] == "carney_exact_abcd_plus_primary_reciprocal_bc"

    SourceAlignedHarmonicService._attach_abcd_execution_tolerance_layer(pattern)
    layer = pattern["execution_tolerance_layer"]
    assert layer["available"] is True
    assert layer["primary_bc_target"] == pytest.approx(1.618)
    assert layer["secondary_bc_target"] == pytest.approx(2.0)
    assert layer["affects_identity"] is False
    assert layer["included_in_source_raw_prz"] is False
    assert layer["role"] == "execution_tolerance_layer"
    assert layer["price"] < source["price_low"]

    frame = pd.DataFrame(
        {
            "high": [201.0, 101.0, 162.0, 122.0, 82.0, 63.0, 80.0, 102.0],
            "low": [199.0, 99.0, 160.0, 118.0, 78.0, 61.7, 76.0, 98.0],
        }
    )
    clock = SourceAlignedHarmonicService._execution_clock_from_forming_payload(pattern, frame)
    assert clock is not None
    assert clock["signal_bar"] == 3
    assert clock["first_prz_entry_bar"] == 5
    assert clock["terminal_bar"] == 5
    assert clock["terminal_price"] == pytest.approx(61.7)
    assert clock["execution_start_bar"] == 6
    assert clock["retrospective_d_clock_used"] is False
    assert clock["pez"]["available"] is True
