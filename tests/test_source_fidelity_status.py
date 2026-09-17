from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "research" / "source-fidelity-status-v1.json"
LEDGER_PATH = ROOT / "specs" / "m2-book-golden-ledger.md"


def _status() -> dict:
    return json.loads(STATUS_PATH.read_text(encoding="utf-8"))


def test_source_truth_tracks_current_prz_freezes_and_quarantines() -> None:
    payload = _status()
    patterns = payload["patterns"]

    assert payload["as_of_milestone"] == "M2.31"
    assert patterns["gartley"]["source_raw_prz"] == "frozen_m2_27"
    assert patterns["bat"]["source_raw_prz"] == "frozen_m2_27"
    assert patterns["butterfly"]["source_raw_prz"] == "frozen_m2_27"
    assert patterns["crab"]["source_raw_prz"] == "frozen_m2_27"
    assert patterns["deep_crab"]["source_raw_prz"] == "frozen_m2_27"
    assert patterns["abcd"]["source_raw_prz"] == "frozen_m2_28"
    assert patterns["shark"]["source_raw_prz"] == "frozen_m2_30"
    assert patterns["alternate_bat"]["production"] == "fail_closed"
    assert patterns["five_zero"]["production"] == "quarantined"
    assert payload["global_contracts"]["five_zero_default_scanner_enabled"] is False


def test_rsi_bamm_truth_is_evidence_only_and_no_backdating() -> None:
    payload = _status()["rsi_bamm"]

    assert payload["role"] == "confirmation_execution_evidence_only"
    assert payload["identity_rule"] is False
    assert payload["source_raw_prz_rule"] is False
    assert payload["state_machine"] == "phase_3_frozen"
    assert payload["lifecycle_integration"] == "phase_4_in_validation"
    assert payload["no_backdating"] is True
    assert set(payload["profiles"]) == {
        "simple_confirmation",
        "complex_confirmation",
        "simple_divergence",
        "complex_divergence",
    }


def test_human_ledger_is_refreshed_to_m2_31_truth() -> None:
    text = LEDGER_PATH.read_text(encoding="utf-8")

    assert text.startswith("# M2.31 — Three-Volume Book Golden Ledger")
    assert "Gartley — source-cleared / Source Raw PRZ frozen M2.27" in text
    assert "Standalone AB=CD — Source Raw PRZ frozen M2.28" in text
    assert "Shark — Source Raw PRZ and reaction management frozen M2.30" in text
    assert "5-0 — structural Source Raw PRZ frozen / production quarantine retained" in text
    assert "forming[].execution_clock.rsi_bamm_evidence" in text
    assert "completed[].rsi_bamm_evidence" in text
