from htcn.research.baseline_audit import audit_t0_baseline


def _row(key: str, pattern_id: str = "abcd"):
    return {
        "code_head": "h",
        "instrument_id": "SSE.600000",
        "as_of_trade_date": "2026-09-17",
        "candidate_key": key,
        "pattern_id": pattern_id,
        "schema": "ABCD" if pattern_id == "abcd" else "XABCD",
        "direction": "bullish",
        "scale": 5,
        "pattern_state": "forming",
        "source_lifecycle_state": "waiting_terminal",
        "action_state": "waiting",
        "next_key_price": 90.0,
        "next_key_price_role": "source_prz_terminal_side",
        "execution_context_gate": "execution_unresolved",
        "context_integrity_summary": "issues_present",
        "source_prz_low": 90.0,
        "source_prz_high": 92.0,
        "source_terminal_trade_date": None,
        "eligible_for_validation": True,
        "evidence_only": True,
        "is_trade_instruction": False,
        "alpha_inference_allowed": False,
    }


def test_clean_t0_is_transition_ready_but_not_outcome_ready() -> None:
    rows = [_row("a"), _row("b")]
    snapshot = {
        "status": "pass",
        "candidate_count": 2,
        "instrument_count": 1,
        "failed_instruments": 0,
        "successful_instruments": 1,
        "code_head": "h",
        "expected_trade_date": "2026-09-17",
        "worktree_clean": True,
        "alpha_inference_allowed": False,
        "is_trade_instruction": False,
        "source_lifecycle_states": {"waiting_terminal": 2},
        "action_states": {"waiting": 2},
        "schemas": {"ABCD": 2},
    }
    result = audit_t0_baseline(rows, snapshot=snapshot)
    assert result["blocker_count"] == 0
    assert result["transition_ready"] is True
    assert result["prospective_outcome_ready"] is False


def test_action_state_mismatch_blocks_t0() -> None:
    row = _row("a")
    row["action_state"] = "execution_evaluation"
    result = audit_t0_baseline([row])
    assert result["transition_ready"] is False
    assert any(item["code"] == "action_state_mismatch" for item in result["blockers"])


def test_future_terminal_date_blocks_t0() -> None:
    row = _row("a")
    row["source_lifecycle_state"] = "type_i_confirmed"
    row["action_state"] = "execution_evaluation"
    row["next_key_price_role"] = "type_i_61_8_target"
    row["source_terminal_trade_date"] = "2026-09-18"
    result = audit_t0_baseline([row])
    assert any(item["code"] == "source_terminal_contract_error" for item in result["blockers"])


def test_alternate_bat_must_remain_fail_closed() -> None:
    row = _row("a", pattern_id="alternate_bat")
    result = audit_t0_baseline([row])
    assert any(item["code"] == "source_fidelity_boundary_error" for item in result["blockers"])


def test_pattern_concentration_is_warning_not_score() -> None:
    rows = [_row("a"), _row("b"), _row("c"), _row("d", pattern_id="crab")]
    result = audit_t0_baseline(rows)
    assert any(item["code"] == "pattern_concentration" for item in result["warnings"])
    assert result["interpretation"]["uses_score"] is False


def test_snapshot_count_drift_blocks_t0() -> None:
    rows = [_row("a")]
    snapshot = {
        "status": "pass",
        "candidate_count": 1,
        "instrument_count": 1,
        "failed_instruments": 0,
        "successful_instruments": 1,
        "code_head": "h",
        "expected_trade_date": "2026-09-17",
        "worktree_clean": True,
        "alpha_inference_allowed": False,
        "is_trade_instruction": False,
        "source_lifecycle_states": {"approaching_source_prz": 1},
        "action_states": {"waiting": 1},
        "schemas": {"ABCD": 1},
    }
    result = audit_t0_baseline(rows, snapshot=snapshot)
    codes = {item["code"] for item in result["blockers"]}
    assert "snapshot_lifecycle_count_mismatch" in codes


def test_mature_terminal_inventory_is_warning_not_blocker() -> None:
    row = _row("a")
    row["source_lifecycle_state"] = "type_i_confirmed"
    row["action_state"] = "execution_evaluation"
    row["next_key_price_role"] = "type_i_61_8_target"
    row["source_terminal_trade_date"] = "2026-01-01"
    result = audit_t0_baseline([row])
    assert result["blocker_count"] == 0
    assert any(
        item["code"] == "mature_baseline_inventory"
        for item in result["warnings"]
    )
