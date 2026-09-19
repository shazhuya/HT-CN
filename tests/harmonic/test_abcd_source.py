from __future__ import annotations

import json
from pathlib import Path

import pytest

from htcn.harmonic.abcd import project_forming_abcd
from htcn.harmonic.abcd_source import abcd_bc_layering_example, with_abcd_source_prz
from htcn.harmonic.models import HarmonicPoint
from htcn.harmonic.source_prz_evidence import SOURCE_PRZ_EVIDENCE

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "research" / "book-source-prz-abcd-cases-v1.json"


def _perfect_bullish_618():
    return (
        HarmonicPoint("A", 0, 200.0),
        HarmonicPoint("B", 1, 100.0),
        HarmonicPoint("C", 2, 161.8),
    )


def test_abcd_source_raw_prz_is_equivalent_completion_plus_reciprocal_bc() -> None:
    projection = project_forming_abcd(_perfect_bullish_618())
    assert projection is not None
    prz = with_abcd_source_prz(projection.prz)
    assert prz.has_source_prz is True
    assert prz.source_prz_component_names == ("AB=CD x1", "BC reciprocal")
    assert prz.source_prz_defining_component == "AB=CD x1"
    assert prz.source_prz_selection_method == "abcd_equivalent_plus_reciprocal_bc"
    assert prz.source_prz_low == pytest.approx(61.8, abs=0.02)
    assert prz.source_prz_high == pytest.approx(61.8, abs=0.02)


def test_volume3_bc_layering_is_execution_only_and_not_raw_prz() -> None:
    points = _perfect_bullish_618()
    layer = abcd_bc_layering_example(points, reciprocal_bc_target=1.618)
    assert layer.available is True
    assert layer.ratio == pytest.approx(2.0)
    assert layer.role == "execution_tolerance_only"

    projection = project_forming_abcd(points)
    assert projection is not None
    prz = with_abcd_source_prz(projection.prz)
    assert all(component.ratio_low != pytest.approx(2.0) for component in prz.components)
    assert "BC reciprocal" in prz.source_prz_component_names


def test_bc_layering_does_not_invent_unpublished_universal_mapping() -> None:
    points = (
        HarmonicPoint("A", 0, 200.0),
        HarmonicPoint("B", 1, 100.0),
        HarmonicPoint("C", 2, 150.0),
    )
    layer = abcd_bc_layering_example(points, reciprocal_bc_target=2.0)
    assert layer.available is False
    assert layer.role == "not_source_cleared_for_this_reciprocal_pair"


def test_abcd_book_ledger_and_evidence_registry_agree() -> None:
    payload = json.loads(LEDGER.read_text(encoding="utf-8"))
    evidence = SOURCE_PRZ_EVIDENCE["abcd"]
    case_ids = {case["case_id"] for case in payload["cases"]}
    assert set(evidence.market_case_ids).issubset(case_ids)
    assert payload["source_contract"]["defining_measurement"] == "equivalent AB=CD completion"
    assert payload["source_contract"]["volume3_bc_layering_role"] == (
        "execution_tolerance_only_not_identity_or_raw_prz"
    )
    assert payload["volume3_execution_layer"]["universal_mapping_claimed"] is False
    assert all(case["coordinate_regression_eligible"] is False for case in payload["cases"])
