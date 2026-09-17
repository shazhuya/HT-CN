import json
from pathlib import Path

from htcn.app.source_aligned_service import SourceAlignedHarmonicService
from htcn.harmonic.five_zero import evaluate_five_zero
from htcn.harmonic.models import HarmonicPoint
from htcn.harmonic.source_prz_evidence import source_prz_evidence


ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "research" / "book-source-prz-five-zero-cases-v1.json"


def _points(values):
    return tuple(
        HarmonicPoint(label=label, index=index, price=price)
        for index, (label, price) in enumerate(values)
    )


def test_five_zero_evidence_freezes_volume2_membership_and_records_v3_tension() -> None:
    evidence = source_prz_evidence("five_zero")
    assert evidence is not None
    assert evidence.source_membership_authority == "carney_vol2_structural_prz"
    assert evidence.selection_authority == "carney_50_bc_plus_reciprocal_abcd"
    assert "v2-five-zero-eur-a0-fx-5m" in evidence.market_case_ids
    assert "v3-five-zero-gld-15m" in evidence.market_case_ids
    assert evidence.known_tensions
    tension = " ".join(evidence.known_tensions)
    assert "Volume Two" in tension
    assert "Volume Three" in tension
    assert "XA and AB" in tension
    assert "execution-only" in tension


def test_five_zero_book_ledger_keeps_61_8_out_of_raw_prz_and_identity() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    contract = ledger["source_contract"]
    assert contract["raw_prz_members"] == ["50% BC retracement", "Reciprocal AB=CD"]
    assert contract["defining_measurement"] == "50% BC retracement"
    assert contract["volume3_61_8_raw_prz_membership"] is False
    assert contract["volume3_61_8_identity_membership"] is False
    assert ledger["source_label_reconciliation"]["status"] == "conflict_recorded_not_silently_resolved"
    case_ids = {case["case_id"] for case in ledger["cases"]}
    assert {
        "v2-five-zero-eur-a0-fx-5m",
        "v2-five-zero-xoi-5m",
        "v2-five-zero-adobe-daily",
        "v3-five-zero-aud-a0-fx-60m",
        "v3-five-zero-gld-15m",
    }.issubset(case_ids)


def test_source_aligned_prz_payload_exposes_five_zero_provenance_without_promoting_61_8() -> None:
    result = evaluate_five_zero(
        _points((("X", 100.0), ("A", 120.0), ("B", 90.0), ("C", 144.0), ("D", 114.0)))
    )
    payload = SourceAlignedHarmonicService._prz_payload(result.prz)
    source = payload["source_prz"]

    assert source["available"] is True
    assert source["component_names"] == [
        "BC 50% structural completion",
        "Reciprocal AB=CD x1",
    ]
    assert "BC 61.8% V3 execution boundary" not in source["component_names"]
    assert source["source_membership_authority"] == "carney_vol2_structural_prz"
    assert source["selection_authority"] == "carney_50_bc_plus_reciprocal_abcd"
    assert source["known_source_tensions"]
