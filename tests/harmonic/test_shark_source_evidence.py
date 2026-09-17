import json
from pathlib import Path

import pytest

from htcn.harmonic.models import HarmonicPoint
from htcn.harmonic.shark_source import build_shark_source_contract
from htcn.harmonic.source_prz_evidence import source_prz_evidence


ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "research" / "book-source-prz-shark-cases-v1.json"


def _points(values):
    return tuple(
        HarmonicPoint(label=label, index=index, price=price)
        for index, (label, price) in enumerate(values)
    )


def test_shark_evidence_freezes_volume3_membership_and_market_cases() -> None:
    evidence = source_prz_evidence("shark")
    assert evidence is not None
    assert evidence.source_membership_authority == "carney_vol3_shark_prz"
    assert evidence.selection_authority == (
        "carney_alignment_of_0b_886_113_and_ab_impulse_1618_224"
    )
    assert "v3-shark-eurusd-15m-bullish" in evidence.market_case_ids
    assert "v3-shark-usdcad-daily-bearish" in evidence.market_case_ids


def test_shark_book_ledger_keeps_reaction_targets_outside_identity() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    contract = ledger["source_contract"]
    assert contract["a_0x"] == [0.382, 0.618]
    assert contract["b_xa"] == [1.13, 1.618]
    assert contract["ab_extreme_impulse"] == [1.618, 2.24]
    assert contract["zero_b_completion"] == [0.886, 1.13]
    assert contract["zero_b_typical_focus"] == 1.0
    assert contract["zero_b_maximum_limit"] == 1.13
    assert contract["raw_prz_selection"] == (
        "overlap/alignment of the 0B 0.886-1.13 completion corridor "
        "and the AB 1.618-2.24 impulse corridor"
    )
    management = ledger["reaction_management"]
    assert management["initial_target"] == (
        "lesser / first encountered of 50% BC retracement or Reciprocal AB=CD"
    )
    assert management["identity_membership"] is False


def test_shark_source_contract_uses_published_corridor_overlap() -> None:
    points = _points((("0", 100.0), ("X", 120.0), ("A", 110.0), ("B", 125.0)))
    contract = build_shark_source_contract(points)

    assert contract.has_source_prz is True
    assert contract.source_prz_low == pytest.approx(96.75)
    assert contract.source_prz_high == pytest.approx(100.73)
    assert contract.price_100_0b == pytest.approx(100.0)
    assert contract.stop_reference_price == pytest.approx(96.75)
    assert contract.prz.source_prz_component_names == (
        "0B 0.886-1.13 completion corridor",
        "AB impulse 1.618-2.24 completion corridor",
    )
    assert contract.prz.source_prz_selection_method == (
        "volume3_shark_overlap_0b_886_113_with_ab_impulse_1618_224"
    )


def test_shark_source_contract_fails_closed_when_published_corridors_do_not_converge() -> None:
    points = _points((("0", 100.0), ("X", 120.0), ("A", 110.0), ("B", 140.0)))
    contract = build_shark_source_contract(points)

    assert contract.has_source_prz is False
    assert contract.prz.has_source_prz is False
    assert contract.prz.source_prz_reason == "source_components_do_not_converge"
