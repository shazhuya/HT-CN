import pytest

from htcn.app.decision_narrative import build_decision_narrative


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ("source_clock_unavailable", "evidence_insufficient"),
        ("source_prz_unresolved", "evidence_insufficient"),
        ("approaching_source_prz", "waiting"),
        ("entered_source_prz", "waiting"),
        ("waiting_terminal", "waiting"),
        ("source_terminal_complete", "reaction_observation"),
        ("t_plus_1", "reaction_observation"),
        ("type_i_early_reaction", "reaction_observation"),
        ("type_i_confirmed", "execution_evaluation"),
        ("type_i_failed", "waiting"),
        ("reaction_only", "waiting"),
        ("type_ii_retest_forming", "waiting"),
        ("type_ii_terminal", "execution_evaluation"),
        ("reversal_evidence", "execution_evaluation"),
        ("invalidated", "evidence_insufficient"),
    ],
)
def test_every_frozen_lifecycle_state_maps_to_one_action_state(state, expected) -> None:
    result = build_decision_narrative(
        source_lifecycle={"state": state},
        context_integrity={"layers": []},
    )
    assert result.action_state == expected
    assert result.lifecycle_state == state
    assert result.is_trade_instruction is False
