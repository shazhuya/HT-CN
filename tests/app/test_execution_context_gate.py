from htcn.app.decision_narrative import build_decision_narrative


def _integrity(state: str = "current"):
    return {"layers": [{"layer": "execution", "state": state, "reason": "execution"}]}


def test_execution_gate_reports_suspension_without_changing_action_state() -> None:
    result = build_decision_narrative(
        source_lifecycle={"state": "type_i_confirmed"},
        context_integrity=_integrity("current"),
        execution_context={"tradable_on_as_of_date": False},
    )
    assert result.action_state == "execution_evaluation"
    assert result.execution_context_gate == "blocked_suspended"


def test_execution_gate_reports_tradable_when_complete() -> None:
    result = build_decision_narrative(
        source_lifecycle={"state": "type_i_confirmed"},
        context_integrity=_integrity("current"),
        execution_context={"tradable_on_as_of_date": True},
    )
    assert result.action_state == "execution_evaluation"
    assert result.execution_context_gate == "tradable"


def test_execution_gate_preserves_integrity_problem_precedence() -> None:
    result = build_decision_narrative(
        source_lifecycle={"state": "type_i_confirmed"},
        context_integrity=_integrity("unresolved"),
        execution_context={"tradable_on_as_of_date": True},
    )
    assert result.execution_context_gate == "execution_unresolved"
