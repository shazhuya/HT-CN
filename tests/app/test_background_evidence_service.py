from __future__ import annotations

from htcn.app.background_evidence_service import (
    BackgroundEvidenceStep,
    empty_background_evidence_service_status,
    evaluate_background_evidence_schedule,
    evaluate_calibration_gate,
    execute_background_evidence_cycle,
    read_background_evidence_service_status,
    write_background_evidence_service_status,
)


def _reports(
    *,
    action: str = "capture_due",
    blockers: int = 0,
    accumulation_status: str = "accumulating",
) -> dict[str, dict]:
    return {
        "append_precheck": {
            "status": "ready" if action != "blocked" else "blocked",
            "action": action,
            "latest_committed_capture_date": "2026-09-21",
        },
        "evidence_health": {
            "status": "ready" if blockers == 0 else "not_ready",
            "blocker_count": blockers,
            "warning_count": 0,
        },
        "accumulation_status": {
            "status": accumulation_status,
            "latest_committed_capture_date": "2026-09-22",
            "prospective_candidate_count": 14,
            "observation_count": 28,
            "outcome_snapshot_count": 2,
        },
    }


def _run_cycle(
    *,
    reports: dict[str, dict] | None = None,
    failures: set[str] | None = None,
    issue_status: str = "open",
    authorization: dict | None = None,
):
    report_map = reports or _reports()
    fail = failures or set()
    calls: list[str] = []

    def runner(step: BackgroundEvidenceStep) -> int:
        calls.append(step.name)
        return 2 if step.name in fail else 0

    payload = execute_background_evidence_cycle(
        run_step=runner,
        read_report=lambda name: report_map.get(name),
        issue_0066_status=issue_status,
        calibration_authorization=authorization,
    )
    return payload, calls


def test_schedule_is_idempotent_for_same_closed_session() -> None:
    decision = evaluate_background_evidence_schedule(
        target_trade_date="2026-09-22",
        last_success_trade_date="2026-09-22",
    )
    assert decision.due is False
    assert decision.reason == "already_current"


def test_schedule_runs_for_new_closed_session() -> None:
    decision = evaluate_background_evidence_schedule(
        target_trade_date="2026-09-22",
        last_success_trade_date="2026-09-21",
    )
    assert decision.due is True
    assert decision.reason == "new_closed_trade_session"


def test_schedule_retries_failed_cycle_even_when_success_watermark_is_same_day() -> None:
    decision = evaluate_background_evidence_schedule(
        target_trade_date="2026-09-22",
        last_success_trade_date="2026-09-22",
        retry_required=True,
    )
    assert decision.due is True
    assert decision.reason == "retry_required"


def test_capture_due_runs_authoritative_chain_without_transport_bundle() -> None:
    payload, calls = _run_cycle()

    assert payload["healthy"] is True
    assert payload["append_action"] == "capture_due"
    assert payload["operational_fault"] is False
    assert "qfq_readiness" in calls
    assert "authoritative_capture" in calls
    assert "outcome_report" in calls
    assert "evidence_bundle" not in calls
    assert payload["contract"]["transport_zip_required_for_daily_operation"] is False
    assert payload["contract"]["manual_ai_acceptance_required_for_daily_operation"] is False


def test_same_session_noop_skips_append_only_steps_but_refreshes_health() -> None:
    payload, calls = _run_cycle(reports=_reports(action="idempotent_noop"))

    assert payload["healthy"] is True
    assert payload["append_action"] == "idempotent_noop"
    assert "qfq_readiness" not in calls
    assert "authoritative_capture" not in calls
    assert "outcome_report" not in calls
    assert "evidence_health" in calls
    assert "transition_report" in calls
    assert "observation_report" in calls
    assert "accumulation_status" in calls


def test_capture_failure_is_operational_blocker_and_calibration_stays_disabled() -> None:
    payload, _ = _run_cycle(failures={"authoritative_capture"})

    assert payload["healthy"] is False
    assert payload["operational_state"] == "blocked"
    assert payload["operational_fault"] is True
    assert payload["retry_required"] is True
    assert payload["calibration_state"] == "disabled_operational_fault"
    assert payload["evidence_insufficient"] is False


def test_evidence_health_blocker_is_product_fault_not_sample_insufficiency() -> None:
    payload, _ = _run_cycle(reports=_reports(blockers=1))

    assert payload["operational_state"] == "blocked"
    assert payload["evidence_blocker_count"] == 1
    assert payload["evidence_state"] == "blocked"
    assert payload["calibration_state"] == "disabled_operational_fault"


def test_healthy_chain_with_open_issue_is_insufficient_evidence_not_fault() -> None:
    payload, _ = _run_cycle(issue_status="open")

    assert payload["healthy"] is True
    assert payload["operational_fault"] is False
    assert payload["evidence_state"] == "insufficient_evidence"
    assert payload["evidence_insufficient"] is True
    assert payload["calibration_state"] == "disabled_insufficient_evidence"
    assert any("产品运行正常" in item for item in payload["diagnostics_zh"])


def test_calibration_requires_issue_resolution_and_explicit_authorization() -> None:
    gate_without_auth = evaluate_calibration_gate(
        operational_state="healthy",
        issue_0066_status="closed",
        evidence_health={"blocker_count": 0},
        accumulation_status={"status": "accumulating"},
        authorization=None,
    )
    assert gate_without_auth["authorized"] is False
    assert "explicit_m8_authorization_missing" in gate_without_auth["reasons"]

    gate = evaluate_calibration_gate(
        operational_state="healthy",
        issue_0066_status="closed",
        evidence_health={"blocker_count": 0},
        accumulation_status={"status": "accumulating"},
        authorization={"authorized": True},
    )
    assert gate["state"] == "authorized"
    assert gate["authorized"] is True
    assert gate["win_rate_inference_allowed"] is True


def test_status_round_trip_preserves_chinese_observability(tmp_path) -> None:
    path = tmp_path / "runtime" / "evidence.json"
    payload = empty_background_evidence_service_status()
    payload["status"] = "healthy"
    payload["healthy"] = True
    payload["diagnostics_zh"] = ["后台证据链正常，但样本仍不足。"]

    write_background_evidence_service_status(path, payload)
    restored = read_background_evidence_service_status(path)

    assert restored["status"] == "healthy"
    assert restored["diagnostics_zh"] == ["后台证据链正常，但样本仍不足。"]
    assert not path.with_suffix(".json.tmp").exists()


def test_missing_status_is_explicit_and_keeps_m8_disabled(tmp_path) -> None:
    payload = read_background_evidence_service_status(tmp_path / "missing.json")
    assert payload["status"] == "not_started"
    assert payload["operational_fault"] is False
    assert payload["evidence_insufficient"] is True
    assert payload["calibration_state"] == "disabled_insufficient_evidence"
