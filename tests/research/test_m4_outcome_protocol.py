from __future__ import annotations

from copy import deepcopy

import pytest

from htcn.research.outcome_protocol import (
    ACTIVE_OUTCOME_PROTOCOL_ID,
    OUTCOME_PROTOCOL_V1_CANONICAL_SHA256,
    OUTCOME_PROTOCOL_V2_CANONICAL_SHA256,
    load_outcome_protocol,
    load_outcome_protocol_v1,
    load_outcome_protocol_v2,
    validate_outcome_protocol_v1,
    validate_outcome_protocol_v2,
)


def test_outcome_protocol_v1_matches_preregistered_fingerprint() -> None:
    payload, identity = load_outcome_protocol_v1()
    assert identity.protocol_id == "m4-outcome-v1"
    assert identity.schema_version == 1
    assert identity.fingerprint == OUTCOME_PROTOCOL_V1_CANONICAL_SHA256
    assert payload["capture_contract"] == {
        "methodology_contract_version": 4,
        "capture_transaction_schema_version": 5,
        "prospective_observation_schema_version": 4,
        "methodology_component_count": 37,
        "exact_methodology_freeze_commit": (
            "c774c54928c33361952bf1a612a8555633449625"
        ),
    }


def test_outcome_protocol_v1_fails_closed_on_post_preregistration_drift() -> None:
    payload, _ = load_outcome_protocol_v1()
    changed = deepcopy(payload)
    changed["descriptive_path_metrics"]["windows_traded_bars"] = [5, 10, 21]
    with pytest.raises(ValueError, match="changed after preregistration"):
        validate_outcome_protocol_v1(changed)


def test_outcome_protocol_v1_prohibits_trade_pnl_and_alpha() -> None:
    payload, _ = load_outcome_protocol_v1()
    prohibited = set(payload["prohibited_in_v1"])
    assert {
        "execution_pnl",
        "win_loss_label",
        "win_rate",
        "alpha",
        "benchmark_excess_return",
        "buy_sell_ranking",
    }.issubset(prohibited)



def test_outcome_protocol_v2_is_active_and_zero_floors_excursions() -> None:
    payload, identity = load_outcome_protocol_v2()
    assert ACTIVE_OUTCOME_PROTOCOL_ID == "m4-outcome-v2"
    assert identity.protocol_id == "m4-outcome-v2"
    assert identity.fingerprint == OUTCOME_PROTOCOL_V2_CANONICAL_SHA256
    assert payload["supersedes_protocol_id"] == "m4-outcome-v1"
    metrics = payload["descriptive_path_metrics"]
    assert metrics["excursion_representation"] == "nonnegative_magnitude"
    assert metrics["zero_floor"] is True
    active, active_identity = load_outcome_protocol()
    assert active == payload
    assert active_identity == identity


def test_outcome_protocol_v2_fails_closed_on_zero_floor_drift() -> None:
    payload, _ = load_outcome_protocol_v2()
    changed = deepcopy(payload)
    changed["descriptive_path_metrics"]["zero_floor"] = False
    with pytest.raises(ValueError, match="changed after preregistration"):
        validate_outcome_protocol_v2(changed)
