from __future__ import annotations

import pytest

from htcn.app.operator_delta import build_operator_delta


def _item(
    *,
    key: str = "SSE.1:bat:XABCD:bullish:S5:2026-09-01",
    instrument_id: str = "SSE.1",
    action_state: str = "waiting",
    lifecycle_state: str = "approaching_source_prz",
    next_key_price: float | None = 100.0,
    next_key_price_role: str | None = "source_prz_entry_edge",
    gate: str = "tradable",
    cautions: list[str] | None = None,
) -> dict:
    return {
        "display_key": key,
        "instrument_id": instrument_id,
        "pattern_id": "bat",
        "schema": "XABCD",
        "direction": "bullish",
        "scale": 5,
        "pattern_state": "forming",
        "action_state": action_state,
        "workflow_bucket_order": 2,
        "lifecycle_state": lifecycle_state,
        "next_key_price": next_key_price,
        "next_key_price_role": next_key_price_role,
        "execution_context_gate": gate,
        "context_cautions": cautions or [],
        "current_position": "current",
        "first_watch": "first",
        "upgrade_blocker": "blocker",
    }


def _queue(
    as_of: str,
    items: list[dict],
    *,
    errors: list[dict] | None = None,
) -> dict:
    return {
        "schema_version": 2,
        "contract": {
            "predictive_score_used": False,
            "historical_outcome_used": False,
            "alpha_inference_allowed": False,
            "is_trade_instruction": False,
            "mutates_harmonic_identity": False,
            "mutates_source_raw_prz": False,
            "owns_lifecycle": False,
        },
        "as_of_trade_date": as_of,
        "observed_trade_dates": [as_of],
        "observation_integrity": "single_as_of",
        "items": items,
        "errors": errors or [],
    }


def test_operator_delta_detects_new_and_disappeared_candidates() -> None:
    old = _item(key="old", instrument_id="SSE.1")
    new = _item(key="new", instrument_id="SSE.2")

    payload = build_operator_delta(
        _queue("2026-09-17", [old]),
        _queue("2026-09-18", [new]),
    )

    assert payload["status"] == "ready"
    assert payload["change_count"] == 2
    assert payload["change_type_counts"] == {
        "disappeared_candidate": 1,
        "new_candidate": 1,
    }
    assert payload["contract"]["authoritative_transition"] is False
    assert payload["contract"]["writes_m4_evidence"] is False


def test_operator_delta_detects_lifecycle_action_and_next_key_changes() -> None:
    before = _item()
    after = _item(
        action_state="reaction_observation",
        lifecycle_state="t_plus_1",
        next_key_price=110.0,
        next_key_price_role="type_i_38_2_target",
    )

    payload = build_operator_delta(
        _queue("2026-09-17", [before]),
        _queue("2026-09-18", [after]),
    )

    change = payload["changes"][0]
    assert change["change_types"] == [
        "action_state_changed",
        "lifecycle_state_changed",
        "next_key_changed",
    ]
    assert change["previous"]["lifecycle_state"] == "approaching_source_prz"
    assert change["current"]["lifecycle_state"] == "t_plus_1"


def test_operator_delta_detects_context_changes() -> None:
    before = _item()
    after = _item(
        gate="execution_partial",
        cautions=["market:stale — old"],
    )

    payload = build_operator_delta(
        _queue("2026-09-17", [before]),
        _queue("2026-09-18", [after]),
    )

    assert payload["changes"][0]["change_types"] == [
        "execution_gate_changed",
        "context_cautions_changed",
    ]


def test_operator_delta_suppresses_disappearance_for_current_error() -> None:
    prior = _item(instrument_id="SSE.1")

    payload = build_operator_delta(
        _queue("2026-09-17", [prior]),
        _queue(
            "2026-09-18",
            [],
            errors=[{
                "instrument_id": "SSE.1",
                "error": "RuntimeError: local data unavailable",
            }],
        ),
    )

    assert payload["change_count"] == 0
    assert payload["comparison_incomplete_instruments"] == ["SSE.1"]
    assert payload["warnings"]


def test_operator_delta_same_as_of_does_not_create_changes() -> None:
    before = _item()
    after = _item(lifecycle_state="type_i_confirmed")

    payload = build_operator_delta(
        _queue("2026-09-18", [before]),
        _queue("2026-09-18", [after]),
    )

    assert payload["status"] == "same_as_of_no_delta"
    assert payload["changes"] == []


def test_operator_delta_rejects_reverse_chronology() -> None:
    with pytest.raises(ValueError, match="reverse chronology"):
        build_operator_delta(
            _queue("2026-09-18", []),
            _queue("2026-09-17", []),
        )


def test_operator_delta_rejects_mixed_as_of_snapshot() -> None:
    current = _queue("2026-09-18", [])
    current["observation_integrity"] = "mixed_as_of"
    current["as_of_trade_date"] = None

    with pytest.raises(ValueError, match="observation_integrity"):
        build_operator_delta(
            _queue("2026-09-17", []),
            current,
        )
