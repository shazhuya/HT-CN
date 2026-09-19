from htcn.app.product_contract import assert_product_payload, audit_product_payload


def _analysis():
    lifecycle = {
        "state": "type_i_confirmed",
        "next_key_price": 111.0,
        "next_key_price_role": "type_i_61_8_target",
    }
    execution = {"board": "STAR"}
    integrity = {
        "layers": [
            {"layer": "execution", "state": "unresolved", "reason": "event incomplete"},
            {"layer": "market", "state": "current", "reason": "ok"},
        ]
    }
    narrative = {
        "lifecycle_state": "type_i_confirmed",
        "action_state": "execution_evaluation",
        "next_key_price": 111.0,
        "next_key_price_role": "type_i_61_8_target",
        "execution_context_gate": "execution_unresolved",
        "context_cautions": ["execution:unresolved — event incomplete"],
        "is_trade_instruction": False,
        "uses_score": False,
        "mutates_harmonic_identity": False,
        "mutates_source_raw_prz": False,
        "owns_lifecycle": False,
    }
    return {
        "a_share_execution_context": execution,
        "context_integrity": integrity,
        "source_lifecycle_contract": {
            "canonical_clock": "source_terminal_price_bar",
            "geometry_terminal_promotes_live_state": False,
            "market_context_owns_lifecycle": False,
            "sector_context_owns_lifecycle": False,
            "concept_context_owns_lifecycle": False,
            "decision_narrative_is_trade_instruction": False,
            "mutates_harmonic_identity": False,
            "mutates_source_raw_prz": False,
            "no_backdating": True,
        },
        "completed": [{
            "pattern_id": "gartley",
            "state": "completed",
            "scale": 5,
            "schema": "XABCD",
            "points": [{"index": 20}],
            "source_lifecycle": lifecycle,
            "decision_narrative": narrative,
            "a_share_execution_context": execution,
        }],
        "forming": [],
    }


def test_product_contract_accepts_consistent_payload() -> None:
    analysis = _analysis()
    audit = audit_product_payload(analysis)
    assert audit.passed is True
    assert audit.issue_count == 0
    assert_product_payload(analysis)


def test_product_contract_detects_narrative_clock_drift() -> None:
    analysis = _analysis()
    analysis["completed"][0]["decision_narrative"]["lifecycle_state"] = "waiting_terminal"
    audit = audit_product_payload(analysis)
    assert audit.passed is False
    assert any(item.code == "narrative_lifecycle_mismatch" for item in audit.issues)


def test_product_contract_detects_execution_copy_drift() -> None:
    analysis = _analysis()
    analysis["completed"][0]["a_share_execution_context"] = {"board": "MAIN"}
    audit = audit_product_payload(analysis)
    assert any(item.code == "execution_context_copy_mismatch" for item in audit.issues)
