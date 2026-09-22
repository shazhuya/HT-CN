from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from htcn.app.background_evidence_service import (
    BackgroundEvidenceStep,
    evaluate_background_evidence_schedule,
    execute_background_evidence_cycle,
    read_background_evidence_service_status,
    write_background_evidence_service_status,
)
from htcn.app.market_data_service import read_market_data_service_status
from htcn.app.operator_process_lock import OperatorCacheProcessLock

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "market"
RUNTIME_ROOT = DATA_ROOT / "runtime"
MARKET_DATA_STATUS_PATH = RUNTIME_ROOT / "m9-market-data-service.json"
STATUS_PATH = RUNTIME_ROOT / "m9-background-evidence-service.json"
LOCK_PATH = RUNTIME_ROOT / "m9-background-evidence-service.lock"
REPORT_ROOT = ROOT / "artifacts" / "reports"
LOG_ROOT = REPORT_ROOT / "m9-background-evidence-service"
ISSUES_PATH = ROOT / "governance" / "OPEN_ISSUES.json"
CALIBRATION_AUTHORIZATION_PATH = (
    ROOT / "governance" / "acceptance" / "M8-calibration-authorization.json"
)
DEFAULT_INTERVAL_SECONDS = 300

REPORT_PATHS = {
    "append_precheck": REPORT_ROOT / "m7-append-precheck.json",
    "evidence_health": REPORT_ROOT / "m4-evidence-health.json",
    "accumulation_status": REPORT_ROOT / "m7-accumulation-status.json",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="HT-CN M9.4 background evidence and observability service"
    )
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--run-now", action="store_true")
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=DEFAULT_INTERVAL_SECONDS,
        help="watch-mode polling interval; minimum 60 seconds",
    )
    return parser.parse_args()


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _run_step(step: BackgroundEvidenceStep) -> int:
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    log_path = LOG_ROOT / step.log_name
    command = [sys.executable, "-u", *step.command]
    with log_path.open("w", encoding="utf-8", newline="\n") as log:
        process = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    return int(process.returncode)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _read_report(name: str) -> dict[str, Any] | None:
    path = REPORT_PATHS.get(name)
    if path is None:
        return None
    return _read_json(path)


def _issue_0066_status() -> str:
    payload = _read_json(ISSUES_PATH)
    if payload is None:
        return "missing"
    for issue in payload.get("issues") or []:
        if isinstance(issue, dict) and issue.get("id") == "ISSUE-0066":
            return str(issue.get("status") or "missing")
    return "missing"


def _calibration_authorization() -> dict[str, Any] | None:
    return _read_json(CALIBRATION_AUTHORIZATION_PATH)


def _market_target(status: dict[str, object]) -> str | None:
    if not bool(status.get("healthy")):
        return None
    return _optional_text(status.get("last_success_trade_date"))


def _write_upstream_wait(
    *,
    previous: dict[str, object],
    started: datetime,
    next_check: datetime,
    market_status: dict[str, object],
) -> None:
    payload = {
        **previous,
        "schema_version": 1,
        "service": "m9_background_evidence_service",
        "status": "waiting_market_data",
        "healthy": False,
        "operational_state": "degraded",
        "operational_fault": True,
        "evidence_state": "blocked",
        "evidence_insufficient": False,
        "calibration_state": "disabled_operational_fault",
        "target_trade_date": None,
        "last_cycle_started_at_utc": _iso(started),
        "last_cycle_finished_at_utc": _iso(_utc_now()),
        "next_check_at_utc": _iso(next_check),
        "market_data_status": {
            "status": market_status.get("status"),
            "healthy": market_status.get("healthy"),
            "last_success_trade_date": market_status.get(
                "last_success_trade_date"
            ),
        },
        "schedule": None,
        "cycle": None,
        "diagnostics_zh": [
            "自动行情服务尚未形成健康的最新收盘水位；后台证据维护等待上游，不会写入权威证据。"
        ],
    }
    write_background_evidence_service_status(STATUS_PATH, payload)


def run_service_cycle(*, force: bool, interval_seconds: int) -> int:
    started = _utc_now()
    next_check = started + timedelta(seconds=interval_seconds)
    previous = read_background_evidence_service_status(STATUS_PATH)
    market_status = read_market_data_service_status(MARKET_DATA_STATUS_PATH)
    target_trade_date = _market_target(market_status)

    if target_trade_date is None:
        _write_upstream_wait(
            previous=previous,
            started=started,
            next_check=next_check,
            market_status=market_status,
        )
        return 2

    decision = evaluate_background_evidence_schedule(
        target_trade_date=target_trade_date,
        last_success_trade_date=previous.get("last_success_trade_date"),
        force=force,
    )
    if not decision.due:
        payload = {
            **previous,
            "schema_version": 1,
            "service": "m9_background_evidence_service",
            "status": "idle_current",
            "healthy": bool(previous.get("healthy")),
            "target_trade_date": target_trade_date,
            "last_cycle_started_at_utc": _iso(started),
            "last_cycle_finished_at_utc": _iso(_utc_now()),
            "next_check_at_utc": _iso(next_check),
            "schedule": decision.as_payload(),
            "diagnostics_zh": [
                "后台证据维护水位已覆盖当前收盘交易日，本轮为幂等空操作。",
                *list(previous.get("diagnostics_zh") or [])[:1],
            ],
        }
        write_background_evidence_service_status(STATUS_PATH, payload)
        return 0 if bool(previous.get("healthy")) else 2

    cycle = execute_background_evidence_cycle(
        run_step=_run_step,
        read_report=_read_report,
        issue_0066_status=_issue_0066_status(),
        calibration_authorization=_calibration_authorization(),
    )
    healthy = bool(cycle["healthy"])
    payload: dict[str, Any] = {
        "schema_version": 1,
        "service": "m9_background_evidence_service",
        "status": cycle["overall_status"],
        "healthy": healthy,
        "operational_state": cycle["operational_state"],
        "operational_fault": cycle["operational_fault"],
        "evidence_state": cycle["evidence_state"],
        "evidence_insufficient": cycle["evidence_insufficient"],
        "calibration_state": cycle["calibration_state"],
        "target_trade_date": target_trade_date,
        "last_success_trade_date": (
            target_trade_date
            if healthy
            else previous.get("last_success_trade_date")
        ),
        "latest_committed_capture_date": cycle[
            "latest_committed_capture_date"
        ],
        "prospective_candidate_count": cycle["prospective_candidate_count"],
        "observation_count": cycle["observation_count"],
        "outcome_snapshot_count": cycle["outcome_snapshot_count"],
        "last_cycle_started_at_utc": _iso(started),
        "last_cycle_finished_at_utc": _iso(_utc_now()),
        "next_check_at_utc": _iso(next_check),
        "market_data_status": {
            "status": market_status.get("status"),
            "healthy": market_status.get("healthy"),
            "last_success_trade_date": market_status.get(
                "last_success_trade_date"
            ),
        },
        "schedule": decision.as_payload(),
        "cycle": cycle,
        "diagnostics_zh": cycle["diagnostics_zh"],
    }
    write_background_evidence_service_status(STATUS_PATH, payload)
    return 0 if healthy else 2


def main() -> int:
    args = parse_args()
    interval_seconds = max(60, int(args.interval_seconds))
    lock = OperatorCacheProcessLock(
        LOCK_PATH,
        timeout_seconds=1.0,
        poll_interval_seconds=0.05,
    )
    try:
        lock.acquire()
    except TimeoutError:
        print("[HT-CN M9.4] 后台前瞻证据服务已有实例在运行。", flush=True)
        return 3

    try:
        while True:
            code = run_service_cycle(
                force=bool(args.run_now),
                interval_seconds=interval_seconds,
            )
            if args.once:
                return code
            args.run_now = False
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("[HT-CN M9.4] 后台前瞻证据服务已停止。", flush=True)
        return 130
    finally:
        lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
