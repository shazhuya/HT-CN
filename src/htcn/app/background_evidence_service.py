from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class BackgroundEvidenceStep:
    name: str
    command: tuple[str, ...]
    log_name: str


@dataclass(frozen=True, slots=True)
class BackgroundEvidenceStepResult:
    name: str
    status: str
    exit_code: int | None
    reason: str | None = None

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BackgroundEvidenceScheduleDecision:
    due: bool
    reason: str
    target_trade_date: str
    last_success_trade_date: str | None

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


RunStep = Callable[[BackgroundEvidenceStep], int]
ReadReport = Callable[[str], Mapping[str, Any] | None]


METHODOLOGY_GUARD = BackgroundEvidenceStep(
    "methodology_freeze_guard",
    ("scripts/m4_methodology_freeze_guard.py",),
    "m4-methodology-freeze-guard.log",
)
OUTCOME_GUARD = BackgroundEvidenceStep(
    "outcome_engine_freeze_guard",
    ("scripts/m4_outcome_engine_freeze_guard.py",),
    "m4-outcome-engine-freeze-guard.log",
)
APPEND_PRECHECK = BackgroundEvidenceStep(
    "append_precheck",
    ("scripts/m7_append_precheck.py",),
    "m7-append-precheck.log",
)
QFQ_READINESS = BackgroundEvidenceStep(
    "qfq_readiness",
    ("scripts/m4_prepare_qfq_universe.py", "--retries", "1", "--sleep", "0.05"),
    "m4-qfq-readiness.log",
)
AUTHORITATIVE_CAPTURE = BackgroundEvidenceStep(
    "authoritative_capture",
    ("scripts/m4_capture_lifecycle_snapshot.py",),
    "m4-lifecycle-snapshot.log",
)
EVIDENCE_HEALTH = BackgroundEvidenceStep(
    "evidence_health",
    ("scripts/m4_evidence_health.py",),
    "m4-evidence-health.log",
)
TRANSITION_REPORT = BackgroundEvidenceStep(
    "transition_report",
    ("scripts/m4_build_transition_report.py",),
    "m4-lifecycle-transitions.log",
)
OBSERVATION_REPORT = BackgroundEvidenceStep(
    "observation_report",
    ("scripts/m4_build_observation_report.py",),
    "m4-prospective-observations.log",
)
OUTCOME_REPORT = BackgroundEvidenceStep(
    "outcome_report",
    ("scripts/m4_build_outcome_report.py",),
    "m4-outcome-v2.log",
)
ACCUMULATION_STATUS = BackgroundEvidenceStep(
    "accumulation_status",
    ("scripts/m7_accumulation_status.py",),
    "m7-accumulation-status.log",
)


def _text(value: object) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def evaluate_background_evidence_schedule(
    *,
    target_trade_date: object,
    last_success_trade_date: object = None,
    retry_required: bool = False,
    force: bool = False,
) -> BackgroundEvidenceScheduleDecision:
    target = _text(target_trade_date)
    if target is None:
        raise ValueError("background evidence target_trade_date is required")
    previous = _text(last_success_trade_date)
    if force:
        return BackgroundEvidenceScheduleDecision(
            due=True,
            reason="forced",
            target_trade_date=target,
            last_success_trade_date=previous,
        )
    if retry_required:
        return BackgroundEvidenceScheduleDecision(
            due=True,
            reason="retry_required",
            target_trade_date=target,
            last_success_trade_date=previous,
        )
    if previous != target:
        return BackgroundEvidenceScheduleDecision(
            due=True,
            reason="new_closed_trade_session",
            target_trade_date=target,
            last_success_trade_date=previous,
        )
    return BackgroundEvidenceScheduleDecision(
        due=False,
        reason="already_current",
        target_trade_date=target,
        last_success_trade_date=previous,
    )


def evaluate_calibration_gate(
    *,
    operational_state: str,
    issue_0066_status: str,
    evidence_health: Mapping[str, Any] | None,
    accumulation_status: Mapping[str, Any] | None,
    authorization: Mapping[str, Any] | None,
) -> dict[str, object]:
    health = dict(evidence_health or {})
    accumulation = dict(accumulation_status or {})
    reasons: list[str] = []

    if operational_state != "healthy":
        reasons.append("background_evidence_operational_fault")
        return {
            "state": "disabled_operational_fault",
            "authorized": False,
            "reasons": reasons,
            "statistical_inference_allowed": False,
            "alpha_inference_allowed": False,
            "win_rate_inference_allowed": False,
            "profitability_inference_allowed": False,
        }

    if str(issue_0066_status).strip().lower() != "closed":
        reasons.append("ISSUE-0066_not_closed")
    if int(health.get("blocker_count") or 0) != 0:
        reasons.append("evidence_chain_has_blockers")
    if str(accumulation.get("status") or "") == "blocked":
        reasons.append("m7_accumulation_blocked")
    if not authorization or authorization.get("authorized") is not True:
        reasons.append("explicit_m8_authorization_missing")

    if reasons:
        return {
            "state": "disabled_insufficient_evidence",
            "authorized": False,
            "reasons": reasons,
            "statistical_inference_allowed": False,
            "alpha_inference_allowed": False,
            "win_rate_inference_allowed": False,
            "profitability_inference_allowed": False,
        }

    return {
        "state": "authorized",
        "authorized": True,
        "reasons": [],
        "statistical_inference_allowed": True,
        "alpha_inference_allowed": True,
        "win_rate_inference_allowed": True,
        "profitability_inference_allowed": True,
    }


def _run(step: BackgroundEvidenceStep, run_step: RunStep) -> BackgroundEvidenceStepResult:
    try:
        code = int(run_step(step))
    except Exception as exc:  # noqa: BLE001 - background service boundary
        return BackgroundEvidenceStepResult(
            name=step.name,
            status="failed",
            exit_code=None,
            reason=f"{type(exc).__name__}: {exc}",
        )
    return BackgroundEvidenceStepResult(
        name=step.name,
        status="passed" if code == 0 else "failed",
        exit_code=code,
        reason=None if code == 0 else f"exit_code={code}",
    )


def _skip(step: BackgroundEvidenceStep, reason: str) -> BackgroundEvidenceStepResult:
    return BackgroundEvidenceStepResult(
        name=step.name,
        status="skipped",
        exit_code=None,
        reason=reason,
    )


def _report(read_report: ReadReport, name: str) -> dict[str, Any]:
    value = read_report(name)
    return {} if value is None else dict(value)


def _finish_cycle(
    *,
    results: dict[str, BackgroundEvidenceStepResult],
    append_action: str,
    precheck: Mapping[str, Any] | None,
    health: Mapping[str, Any] | None,
    accumulation: Mapping[str, Any] | None,
    issue_0066_status: str,
    authorization: Mapping[str, Any] | None,
) -> dict[str, object]:
    health_payload = dict(health or {})
    accumulation_payload = dict(accumulation or {})

    critical = {
        "methodology_freeze_guard",
        "outcome_engine_freeze_guard",
        "append_precheck",
        "qfq_readiness",
        "authoritative_capture",
        "evidence_health",
    }
    failed = [item.name for item in results.values() if item.status == "failed"]
    critical_failed = [name for name in failed if name in critical]
    health_blockers = int(health_payload.get("blocker_count") or 0)
    accumulation_blocked = str(accumulation_payload.get("status") or "") == "blocked"

    if (
        append_action == "blocked"
        or critical_failed
        or health_blockers
        or accumulation_blocked
    ):
        operational_state = "blocked"
    elif failed:
        operational_state = "degraded"
    else:
        operational_state = "healthy"

    calibration = evaluate_calibration_gate(
        operational_state=operational_state,
        issue_0066_status=issue_0066_status,
        evidence_health=health_payload,
        accumulation_status=accumulation_payload,
        authorization=authorization,
    )
    operational_fault = operational_state != "healthy"
    evidence_insufficient = (
        not operational_fault and calibration["state"] == "disabled_insufficient_evidence"
    )
    evidence_state = (
        "blocked"
        if operational_fault
        else "calibration_authorized"
        if calibration["authorized"]
        else "insufficient_evidence"
    )

    diagnostics_zh: list[str] = []
    if operational_state == "healthy":
        diagnostics_zh.append("后台前瞻证据维护运行正常。")
    elif operational_state == "degraded":
        diagnostics_zh.append("后台证据维护部分步骤失败；成功水位不会推进，将自动重试。")
    else:
        diagnostics_zh.append("后台证据维护被完整性或执行故障阻断；不会覆盖既有权威证据。")
    if failed:
        diagnostics_zh.append("失败步骤：" + "、".join(failed) + "。")
    if evidence_insufficient:
        diagnostics_zh.append(
            "产品运行正常，但前瞻样本仍不足；M8、胜率、Alpha 与盈利能力统计保持禁用。"
        )
    elif calibration["authorized"]:
        diagnostics_zh.append("M8 已获得显式证据授权；统计校准边界可由后续阶段使用。")

    latest_capture = (
        accumulation_payload.get("latest_committed_capture_date")
        or dict(precheck or {}).get("latest_committed_capture_date")
    )
    return {
        "schema_version": 1,
        "overall_status": operational_state,
        "healthy": operational_state == "healthy",
        "retry_required": operational_state != "healthy",
        "operational_state": operational_state,
        "operational_fault": operational_fault,
        "append_action": append_action,
        "latest_committed_capture_date": latest_capture,
        "evidence_state": evidence_state,
        "evidence_insufficient": evidence_insufficient,
        "calibration_state": calibration["state"],
        "calibration": calibration,
        "prospective_candidate_count": int(
            accumulation_payload.get("prospective_candidate_count") or 0
        ),
        "observation_count": int(accumulation_payload.get("observation_count") or 0),
        "outcome_snapshot_count": int(
            accumulation_payload.get("outcome_snapshot_count") or 0
        ),
        "evidence_health_status": health_payload.get("status"),
        "evidence_blocker_count": health_blockers,
        "evidence_warning_count": int(health_payload.get("warning_count") or 0),
        "steps": {name: item.as_payload() for name, item in results.items()},
        "contract": {
            "reimplements_m4_capture_semantics": False,
            "reimplements_outcome_semantics": False,
            "historical_backfill_allowed": False,
            "transport_zip_required_for_daily_operation": False,
            "manual_ai_acceptance_required_for_daily_operation": False,
            "user_computer_required": False,
            "is_trade_instruction": False,
        },
        "diagnostics_zh": diagnostics_zh,
    }


def execute_background_evidence_cycle(
    *,
    run_step: RunStep,
    read_report: ReadReport,
    issue_0066_status: str,
    calibration_authorization: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    results: dict[str, BackgroundEvidenceStepResult] = {}

    for guard in (METHODOLOGY_GUARD, OUTCOME_GUARD):
        result = _run(guard, run_step)
        results[guard.name] = result
        if result.status != "passed":
            return _finish_cycle(
                results=results,
                append_action="blocked",
                precheck=None,
                health=None,
                accumulation=None,
                issue_0066_status=issue_0066_status,
                authorization=calibration_authorization,
            )

    precheck_result = _run(APPEND_PRECHECK, run_step)
    results[APPEND_PRECHECK.name] = precheck_result
    precheck = _report(read_report, "append_precheck")
    action = str(precheck.get("action") or "blocked")
    if action not in {"capture_due", "idempotent_noop", "blocked"}:
        action = "blocked"

    if action == "capture_due" and precheck_result.status == "passed":
        qfq = _run(QFQ_READINESS, run_step)
        results[QFQ_READINESS.name] = qfq
        if qfq.status == "passed":
            results[AUTHORITATIVE_CAPTURE.name] = _run(AUTHORITATIVE_CAPTURE, run_step)
        else:
            results[AUTHORITATIVE_CAPTURE.name] = _skip(
                AUTHORITATIVE_CAPTURE,
                "blocked_by:qfq_readiness",
            )
    else:
        reason = (
            "idempotent_same_session"
            if action == "idempotent_noop"
            else "append_precheck_not_authorized"
        )
        results[QFQ_READINESS.name] = _skip(QFQ_READINESS, reason)
        results[AUTHORITATIVE_CAPTURE.name] = _skip(AUTHORITATIVE_CAPTURE, reason)

    results[EVIDENCE_HEALTH.name] = _run(EVIDENCE_HEALTH, run_step)
    results[TRANSITION_REPORT.name] = _run(TRANSITION_REPORT, run_step)
    results[OBSERVATION_REPORT.name] = _run(OBSERVATION_REPORT, run_step)
    health = _report(read_report, "evidence_health")

    capture_passed = results[AUTHORITATIVE_CAPTURE.name].status == "passed"
    health_passed = results[EVIDENCE_HEALTH.name].status == "passed"
    observation_passed = results[OBSERVATION_REPORT.name].status == "passed"
    if action == "capture_due" and capture_passed and health_passed and observation_passed:
        results[OUTCOME_REPORT.name] = _run(OUTCOME_REPORT, run_step)
    else:
        results[OUTCOME_REPORT.name] = _skip(
            OUTCOME_REPORT,
            "idempotent_same_session"
            if action == "idempotent_noop"
            else "capture_health_observation_not_ready",
        )

    results[ACCUMULATION_STATUS.name] = _run(ACCUMULATION_STATUS, run_step)
    accumulation = _report(read_report, "accumulation_status")

    return _finish_cycle(
        results=results,
        append_action=action,
        precheck=precheck,
        health=health,
        accumulation=accumulation,
        issue_0066_status=issue_0066_status,
        authorization=calibration_authorization,
    )


def empty_background_evidence_service_status() -> dict[str, object]:
    return {
        "schema_version": 1,
        "service": "m9_background_evidence_service",
        "status": "not_started",
        "healthy": False,
        "retry_required": False,
        "operational_state": "not_started",
        "operational_fault": False,
        "evidence_state": "insufficient_evidence",
        "evidence_insufficient": True,
        "calibration_state": "disabled_insufficient_evidence",
        "target_trade_date": None,
        "last_success_trade_date": None,
        "latest_committed_capture_date": None,
        "prospective_candidate_count": 0,
        "outcome_snapshot_count": 0,
        "last_cycle_started_at_utc": None,
        "last_cycle_finished_at_utc": None,
        "next_check_at_utc": None,
        "schedule": None,
        "cycle": None,
        "diagnostics_zh": ["后台前瞻证据服务尚未产生运行状态；M8 保持禁用。"],
    }


def read_background_evidence_service_status(path: str | Path) -> dict[str, object]:
    status_path = Path(path)
    if not status_path.exists():
        return empty_background_evidence_service_status()
    try:
        payload = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fallback = empty_background_evidence_service_status()
        fallback["status"] = "status_unreadable"
        fallback["operational_state"] = "blocked"
        fallback["operational_fault"] = True
        fallback["diagnostics_zh"] = [
            f"后台证据服务状态文件不可读：{type(exc).__name__}"
        ]
        return fallback
    if not isinstance(payload, dict):
        fallback = empty_background_evidence_service_status()
        fallback["status"] = "status_invalid"
        fallback["operational_state"] = "blocked"
        fallback["operational_fault"] = True
        fallback["diagnostics_zh"] = ["后台证据服务状态文件格式无效。"]
        return fallback
    return payload


def write_background_evidence_service_status(
    path: str | Path,
    payload: Mapping[str, Any],
) -> Path:
    status_path = Path(path)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = status_path.with_suffix(status_path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(
            dict(payload),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(status_path)
    return status_path
