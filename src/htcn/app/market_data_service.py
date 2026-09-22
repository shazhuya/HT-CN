from __future__ import annotations

import json
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class MarketDataServiceStep:
    name: str
    command: tuple[str, ...]
    log_name: str
    blocks_following: bool = False


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0

    def delay_after_failure(self, attempt: int) -> float:
        if attempt < 1:
            raise ValueError("attempt must be >= 1")
        return min(
            max(0.0, float(self.max_delay_seconds)),
            max(0.0, float(self.base_delay_seconds)) * (2 ** (attempt - 1)),
        )


@dataclass(frozen=True, slots=True)
class MarketDataStepResult:
    name: str
    status: str
    attempts: int
    exit_code: int | None
    reason: str | None = None

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MarketDataScheduleDecision:
    due: bool
    reason: str
    target_trade_date: str
    last_success_trade_date: str | None

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


RunStep = Callable[[MarketDataServiceStep], int]
Sleep = Callable[[float], None]


DEFAULT_STEPS: tuple[MarketDataServiceStep, ...] = (
    MarketDataServiceStep(
        name="incremental_a_share_update",
        command=("scripts/m1_daily_update.py", "--limit", "0", "--sleep", "0.05"),
        log_name="m9-market-data-update.log",
        blocks_following=True,
    ),
    MarketDataServiceStep(
        name="qfq_readiness",
        command=("scripts/m4_prepare_qfq_universe.py", "--retries", "1", "--sleep", "0.05"),
        log_name="m9-market-data-qfq.log",
    ),
    MarketDataServiceStep(
        name="local_data_health",
        command=("scripts/m1_health_check.py",),
        log_name="m9-market-data-health.log",
    ),
)


def _date_text(value: date | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def evaluate_market_data_schedule(
    *,
    target_trade_date: date | str,
    last_success_trade_date: date | str | None,
    force: bool = False,
) -> MarketDataScheduleDecision:
    target = _date_text(target_trade_date)
    if target is None:
        raise ValueError("target_trade_date is required")
    last_success = _date_text(last_success_trade_date)
    if force:
        return MarketDataScheduleDecision(
            due=True,
            reason="forced",
            target_trade_date=target,
            last_success_trade_date=last_success,
        )
    if last_success is None or last_success < target:
        return MarketDataScheduleDecision(
            due=True,
            reason="new_closed_trade_session",
            target_trade_date=target,
            last_success_trade_date=last_success,
        )
    return MarketDataScheduleDecision(
        due=False,
        reason="already_current",
        target_trade_date=target,
        last_success_trade_date=last_success,
    )


def run_step_with_retry(
    step: MarketDataServiceStep,
    *,
    run_step: RunStep,
    retry_policy: RetryPolicy,
    sleep_fn: Sleep = time.sleep,
) -> MarketDataStepResult:
    attempts = max(1, int(retry_policy.max_attempts))
    last_code: int | None = None
    last_error: str | None = None

    for attempt in range(1, attempts + 1):
        try:
            code = int(run_step(step))
            last_code = code
            last_error = None if code == 0 else f"exit_code={code}"
            if code == 0:
                return MarketDataStepResult(
                    name=step.name,
                    status="passed",
                    attempts=attempt,
                    exit_code=0,
                )
        except Exception as exc:  # execution boundary: preserve failure for retry/status
            last_code = None
            last_error = f"{type(exc).__name__}: {exc}"

        if attempt < attempts:
            delay = retry_policy.delay_after_failure(attempt)
            if delay > 0:
                sleep_fn(delay)

    return MarketDataStepResult(
        name=step.name,
        status="failed",
        attempts=attempts,
        exit_code=last_code,
        reason=last_error or "unknown_failure",
    )


def execute_market_data_cycle(
    *,
    run_step: RunStep,
    retry_policy: RetryPolicy | None = None,
    steps: Sequence[MarketDataServiceStep] = DEFAULT_STEPS,
    sleep_fn: Sleep = time.sleep,
) -> dict[str, object]:
    policy = retry_policy or RetryPolicy()
    results: list[MarketDataStepResult] = []
    blocked = False
    blocked_by: str | None = None

    for step in steps:
        if blocked:
            results.append(
                MarketDataStepResult(
                    name=step.name,
                    status="skipped",
                    attempts=0,
                    exit_code=None,
                    reason=f"blocked_by:{blocked_by}",
                )
            )
            continue
        result = run_step_with_retry(
            step,
            run_step=run_step,
            retry_policy=policy,
            sleep_fn=sleep_fn,
        )
        results.append(result)
        if result.status != "passed" and step.blocks_following:
            blocked = True
            blocked_by = step.name

    by_name = {item.name: item for item in results}
    raw = by_name.get("incremental_a_share_update")
    qfq = by_name.get("qfq_readiness")
    health = by_name.get("local_data_health")

    raw_ready = raw is not None and raw.status == "passed"
    qfq_ready = qfq is not None and qfq.status == "passed"
    health_ready = health is not None and health.status == "passed"
    healthy = raw_ready and qfq_ready and health_ready

    if healthy:
        overall_status = "healthy"
        diagnostics_zh = ["行情、前复权与本地健康检查均已完成。"]
    elif not raw_ready:
        overall_status = "failed"
        diagnostics_zh = ["A股增量行情更新失败；本轮后续数据步骤已停止，将按调度周期重试。"]
    else:
        overall_status = "degraded"
        diagnostics_zh = ["原始行情已更新，但前复权或本地健康检查存在异常；服务将继续重试。"]

    failed_steps = [item.name for item in results if item.status == "failed"]
    if failed_steps:
        diagnostics_zh.append("失败步骤：" + "、".join(failed_steps))

    return {
        "schema_version": 1,
        "overall_status": overall_status,
        "healthy": healthy,
        "raw_market_data_ready": raw_ready,
        "qfq_ready": qfq_ready,
        "local_health_ready": health_ready,
        "steps": {item.name: item.as_payload() for item in results},
        "diagnostics_zh": diagnostics_zh,
    }


def empty_market_data_service_status() -> dict[str, object]:
    return {
        "schema_version": 1,
        "service": "m9_market_data_service",
        "status": "not_started",
        "healthy": False,
        "target_trade_date": None,
        "last_success_trade_date": None,
        "last_cycle_started_at_utc": None,
        "last_cycle_finished_at_utc": None,
        "next_check_at_utc": None,
        "schedule": None,
        "cycle": None,
        "diagnostics_zh": ["自动行情服务尚未产生运行状态。"],
    }


def read_market_data_service_status(path: str | Path) -> dict[str, object]:
    status_path = Path(path)
    if not status_path.exists():
        return empty_market_data_service_status()
    try:
        payload = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fallback = empty_market_data_service_status()
        fallback["status"] = "status_unreadable"
        fallback["diagnostics_zh"] = [f"自动行情服务状态文件不可读：{type(exc).__name__}"]
        return fallback
    if not isinstance(payload, dict):
        fallback = empty_market_data_service_status()
        fallback["status"] = "status_invalid"
        fallback["diagnostics_zh"] = ["自动行情服务状态文件格式无效。"]
        return fallback
    return payload


def write_market_data_service_status(path: str | Path, payload: dict[str, Any]) -> Path:
    status_path = Path(path)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = status_path.with_suffix(status_path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(status_path)
    return status_path
