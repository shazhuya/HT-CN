import scripts.m4_methodology_freeze_guard as methodology_guard
import scripts.m4_outcome_engine_freeze_guard as outcome_guard


def test_release_methodology_attestation_contract() -> None:
    payload = {
        "status": "frozen_match",
        "frozen_methodology_commit": methodology_guard.FROZEN_METHODOLOGY_COMMIT,
        "methodology_contract_version": methodology_guard.EXPECTED_CONTRACT_VERSION,
        "methodology_component_count": methodology_guard.EXPECTED_COMPONENT_COUNT,
        "changed_methodology_components": [],
    }
    assert methodology_guard._release_attestation_errors(payload) == []
    payload["changed_methodology_components"] = ["src/changed.py"]
    assert (
        "release_methodology_changed_components_not_empty"
        in methodology_guard._release_attestation_errors(payload)
    )


def test_release_outcome_attestation_contract() -> None:
    payload = {
        "status": "frozen_match",
        "frozen_outcome_engine_commit": outcome_guard.FROZEN_OUTCOME_ENGINE_COMMIT,
        "outcome_engine_contract_version": outcome_guard.EXPECTED_ENGINE_CONTRACT_VERSION,
        "outcome_engine_component_count": outcome_guard.EXPECTED_ENGINE_COMPONENT_COUNT,
        "changed_outcome_engine_components": [],
        "active_outcome_protocol_id": outcome_guard.EXPECTED_ACTIVE_OUTCOME_PROTOCOL_ID,
        "active_outcome_protocol_fingerprint": (
            outcome_guard.EXPECTED_ACTIVE_OUTCOME_PROTOCOL_FINGERPRINT
        ),
    }
    assert outcome_guard._release_attestation_errors(payload) == []
    payload["status"] = "blocked"
    assert (
        "release_outcome_attestation_not_frozen_match"
        in outcome_guard._release_attestation_errors(payload)
    )
