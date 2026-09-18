from __future__ import annotations

from copy import deepcopy

import pytest

from htcn.research.outcome_protocol import (
    OUTCOME_PROTOCOL_V1_CANONICAL_SHA256,
    load_outcome_protocol_v1,
    validate_outcome_protocol_v1,
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
