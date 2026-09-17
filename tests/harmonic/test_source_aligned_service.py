from types import SimpleNamespace

import pandas as pd
import pytest

import htcn.app.source_aligned_service as source_service
from htcn.app.source_aligned_service import SourceAlignedHarmonicService
from htcn.harmonic.models import PatternDirection
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

    assert payload["semantics_version"] == 3
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
    # Explicit source bounds constructed by older compatibility callers remain valid even
    # without pattern provenance. M2.28 keeps that compatibility while versioning the contract.
    assert source["component_names"] == []
    assert source["defining_component"] is None
    assert source["selection_method"] is None
    assert source["source_refs"] == []
    assert source["source_note"] is None
    assert source["unresolved_reason"] is None
    assert source["profile_version"] == 2
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


def _clock_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "close": [80, 120, 95, 110, 107, 99, 94, 106],
            "high": [82, 122, 97, 112, 111, 105, 101, 108],
            "low": [78, 118, 93, 108, 104, 95, 89, 102],
        }
    )


def test_forming_execution_clock_starts_after_confirmed_frontier_and_fails_closed_without_source_prz() -> None:
    unresolved = PotentialReversalZone(
        pattern_id="gartley",
        direction=PatternDirection.BULLISH,
        components=(_component(),),
    )
    clock = SourceAlignedHarmonicService._execution_clock_from_forming_payload(
        _forming_payload(unresolved),
        _clock_frame(),
    )

    assert clock is not None
    # C pivot index=3 with S1 is observable only at bar 4; observation starts after bar 4.
    assert clock["signal_bar"] == 4
    assert clock["signal_clock_basis"] == "last_frontier_pivot_confirmed_at=index+scale"
    assert clock["retrospective_d_clock_used"] is False
    assert clock["state"] == "source_prz_unresolved"
    assert clock["pez"]["available"] is False
    assert clock["rsi_bamm_evidence"]["status"] == "waiting_for_source_terminal_bar"
    assert clock["rsi_bamm_evidence"]["source_confirmed"] is False


def test_terminal_bar_creates_dynamic_pez_and_timestamped_bamm_channel() -> None:
    frozen = PotentialReversalZone(
        pattern_id="gartley",
        direction=PatternDirection.BULLISH,
        components=(_component(),),
        source_prz_low=90.0,
        source_prz_high=100.0,
    )
    clock = SourceAlignedHarmonicService._execution_clock_from_forming_payload(
        _forming_payload(frozen),
        _clock_frame(),
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
    # Eight bars are insufficient for Wilder RSI(14), therefore BAMM is visible as an
    # independent empty evidence channel rather than being manufactured from price geometry.
    assert clock["rsi_bamm_evidence"]["status"] == "no_completed_rsi_bamm_observed"
    assert clock["rsi_bamm_evidence"]["source_confirmed"] is False
    assert clock["rsi_bamm_evidence"]["mutates_harmonic_identity"] is False


def test_source_confirmed_bamm_is_never_backdated_to_pattern_terminal(monkeypatch) -> None:
    sequence = SimpleNamespace(
        completion_bar=8,
        profile=SimpleNamespace(value="simple_divergence"),
        relation=SimpleNamespace(value="divergence"),
        confirmation_extension_ratio=1.13,
        confirmation_projection_price=88.7,
        price_projection_tested=True,
    )
    confirmation = SimpleNamespace(pattern_precedence_used=False)
    confluence = SimpleNamespace(
        source_confirmed=True,
        sequence=sequence,
        status="source_confirmed",
        confirmation=confirmation,
    )
    item = SimpleNamespace(
        direction=PatternDirection.BULLISH,
        points=[SimpleNamespace(index=6)],
    )
    monkeypatch.setattr(
        source_service,
        "scan_rsi_bamm_frame",
        lambda frame, *, direction: [sequence],
    )
    monkeypatch.setattr(
        source_service,
        "confirm_rsi_bamm_with_match",
        lambda sequence_arg, item_arg: confluence,
    )

    payload = SourceAlignedHarmonicService._rsi_bamm_confluence_payload(
        item,
        pd.DataFrame(
            {
                "close": [100.0] * 12,
                "low": [99.0] * 12,
                "high": [101.0] * 12,
            }
        ),
    )

    assert payload["status"] == "source_confirmed"
    assert payload["source_confirmed_count"] == 1
    assert payload["pattern_terminal_bar"] == 6
    assert payload["bamm_completion_bar"] == 8
    assert payload["available_from_bar"] == 8
    assert payload["available_at_pattern_terminal"] is False
    assert payload["mutates_harmonic_identity"] is False
