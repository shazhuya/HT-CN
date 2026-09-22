from scripts.m4_methodology_freeze_guard import (
    EXPECTED_COMPONENT_COUNT,
    EXPECTED_CONTRACT_VERSION,
    FROZEN_METHODOLOGY_COMMIT,
    _release_attestation_errors as methodology_attestation_errors,
)
from scripts.m4_outcome_engine_freeze_guard import (
    EXPECTED_ACTIVE_OUTCOME_PROTOCOL_FINGERPRINT,
    EXPECTED_ACTIVE_OUTCOME_PROTOCOL_ID,
    EXPECTED_ENGINE_COMPONENT_COUNT,
    EXPECTED_ENGINE_CONTRACT_VERSION,
    FROZEN_OUTCOME_ENGINE_COMMIT,
    _release_attestation_errors as outcome_attestation_errors,
)


def test_release_methodology_attestation_contract() -> None:
    payload = {
        "status": "frozen_match",
        "frozen_methodology_commit": FROZEN_METHODOLOGY_COMMIT,
        "methodology_contract_version": EXPECTED_CONTRACT_VERSION,
        "methodology_component_count": EXPECTED_COMPONENT_COUNT,
        "changed_methodology_components": [],
    }
    assert methodology_attestation_errors(payload) == []
    payload["changed_methodology_components"] = ["src/changed.py"]
    assert "release_methodology_changed_components_not_empty" in methodology_attestation_errors(payload)


def test_release_outcome_attestation_contract() -> None:
    payload = {
        "status": "frozen_match",
        "frozen_outcome_engine_commit": FROZEN_OUTCOME_ENGINE_COMMIT,
        "outcome_engine_contract_version": EXPECTED_ENGINE_CONTRACT_VERSION,
        "outcome_engine_component_count": EXPECTED_ENGINE_COMPONENT_COUNT,
        "changed_outcome_engine_components": [],
        "active_outcome_protocol_id": EXPECTED_ACTIVE_OUTCOME_PROTOCOL_ID,
        "active_outcome_protocol_fingerprint": EXPECTED_ACTIVE_OUTCOME_PROTOCOL_FINGERPRINT,
    }
    assert outcome_attestation_errors(payload) == []
    payload["status"] = "blocked"
    assert "release_outcome_attestation_not_frozen_match" in outcome_attestation_errors(payload)
