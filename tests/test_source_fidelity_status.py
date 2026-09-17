from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "research" / "source-fidelity-status-v1.json"
LEDGER_PATH = ROOT / "specs" / "m2-book-golden-ledger.md"
CLOSEOUT_PATH = ROOT / "research" / "m2-31-source-clock-closeout-v1.json"


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
    assert payload["global_contracts"]["completed_lifecycle_clock"] == "source_terminal_price_bar"
    assert payload["global_contracts"]["pez_overspill_allowed_without_mutating_source_raw_prz"] is True


def test_rsi_bamm_truth_is_evidence_only_source_clocked_and_no_backdating() -> None:
    payload = _status()["rsi_bamm"]

    assert payload["role"] == "confirmation_execution_evidence_only"
    assert payload["identity_rule"] is False
    assert payload["source_raw_prz_rule"] is False
    assert payload["state_machine"] == "phase_3_frozen"
    assert payload["lifecycle_integration"] == "phase_4_frozen"
    assert payload["completed_confluence_clock"] == "source_terminal_price_bar"
    assert payload["geometry_terminal_adapter"] == "compatibility_and_golden_tests_only"
    assert payload["source_confirmation_adapter"] == "confirm_rsi_bamm_with_source_execution"
    assert payload["source_execution_reconstruction"] == "observe_source_execution_for_match"
    assert payload["no_backdating"] is True
    assert payload["pez_overspill_allowed"] is True
    assert set(payload["profiles"]) == {
        "simple_confirmation",
        "complex_confirmation",
        "simple_divergence",
        "complex_divergence",
    }


def test_m2_31_closeout_is_frozen_observability_not_performance_inference() -> None:
    closeout = json.loads(CLOSEOUT_PATH.read_text(encoding="utf-8"))
    acceptance = closeout["acceptance"]

    assert closeout["status"] == "accepted_frozen"
    assert closeout["semantic_assertions"]["geometry_terminal_is_source_terminal"] is False
    assert closeout["semantic_assertions"]["completed_bamm_confluence_clock"] == "source_terminal_price_bar"
    assert acceptance["successful_symbols"] == 45
    assert acceptance["failed_symbols"] == 0
    assert acceptance["total_rsi_bamm_sequences"] == 686
    assert acceptance["completed_source_scannable_matches"] == 174
    assert acceptance["source_clock_observable_matches"] == 128
    assert acceptance["source_terminal_observed_matches"] == 23
    assert acceptance["source_confirmed_confluences"] == 2
    assert "do not estimate hit rate" in acceptance["interpretation_boundary"]


def test_human_ledger_is_refreshed_to_m2_31_truth() -> None:
    text = LEDGER_PATH.read_text(encoding="utf-8")

    assert text.startswith("# M2.31 — Three-Volume Book Golden Ledger")
    assert "Gartley — source-cleared / Source Raw PRZ frozen M2.27" in text
    assert "Standalone AB=CD — Source Raw PRZ frozen M2.28" in text
    assert "Shark — Source Raw PRZ and reaction management frozen M2.30" in text
    assert "5-0 — structural Source Raw PRZ frozen / production quarantine retained" in text
    assert "forming[].execution_clock.rsi_bamm_evidence" in text
    assert "completed[].rsi_bamm_evidence" in text
    assert "Source Terminal Price Bar" in text
