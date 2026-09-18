from htcn.app.decision_narrative import build_decision_narrative


def test_type_i_confirmed_maps_to_execution_evaluation_without_trade_instruction() -> None:
    item = build_decision_narrative(
        source_lifecycle={
            "state": "type_i_confirmed",
            "next_key_price": 114.0,
            "next_key_price_role": "type_i_61_8_target",
        },
        context_integrity={
            "layers": [
                {"layer": "execution", "state": "unresolved", "reason": "事件不完整"},
                {"layer": "market", "state": "current", "reason": "ok"},
            ]
        },
    )
    assert item.lifecycle_state == "type_i_confirmed"
    assert item.action_state == "execution_evaluation"
    assert item.next_key_price == 114.0
    assert item.execution_context_gate == "execution_unresolved"
    assert item.is_trade_instruction is False
    assert item.uses_score is False
    assert item.owns_lifecycle is False


def test_waiting_terminal_cannot_be_upgraded_by_context() -> None:
    item = build_decision_narrative(
        source_lifecycle={
            "state": "waiting_terminal",
            "next_key_price": 103.9,
            "next_key_price_role": "source_prz_terminal_side",
        },
        context_integrity={
            "layers": [
                {"layer": "execution", "state": "current", "reason": "ok"},
                {"layer": "market", "state": "current", "reason": "ok"},
                {"layer": "industry", "state": "current", "reason": "ok"},
                {"layer": "concept", "state": "current", "reason": "ok"},
            ]
        },
    )
    assert item.action_state == "waiting"
    assert "terminal" in item.next_key_price_role
    assert "不能升级" in item.upgrade_blocker
