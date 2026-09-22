from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from htcn.app.market_data_service import (
    DEFAULT_STEPS,
    MarketDataServiceStep,
    RetryPolicy,
    evaluate_market_data_schedule,
    execute_market_data_cycle,
    read_market_data_service_status,
    write_market_data_service_status,
)
from htcn.app.operator_process_lock import OperatorCacheProcessLock
from htcn.data.providers import (
    AkShareProvider,
    AkShareSinaProvider,
    BaoStockProvider,
    FailoverProvider,
)
from htcn.data.trading_clock import latest_closed_trade_clock

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "market"
CATALOG_PATH = DATA_ROOT / "catalog.duckdb"
RUNTIME_ROOT = DATA_ROOT / "runtime"
STATUS_PATH = RUNTIME_ROOT / "m9-market-data-service.json"
LOCK_PATH = RUNTIME_ROOT / "m9-market-data-service.lock"
LOG_ROOT = ROOT / "artifacts" / "reports" / "m9-market-data-service"
DEFAULT_INTERVAL_SECONDS = 900


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="HT-CN M9.1 automated A-share market-data scheduling service"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="evaluate one scheduling cycle and exit",
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="force a data cycle even when already current",
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=DEFAULT_INTERVAL_SECONDS,
        help="watch-mode polling interval; minimum 60 seconds",
    )
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--base-delay", type=float, default=1.0)
    return parser.parse_args()


def build_provider() -> FailoverProvider:
    return FailoverProvider(
        AkShareProvider(),
        FailoverProvider(AkShareSinaProvider(), BaoStockProvider()),
    )


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def _last_success_trade_date(status: dict[str, object]) -> str | None:
    value = status.get("last_success_trade_date")
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _run_step(step: MarketDataServiceStep) -> int:
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


def _write_calendar_failure(
    *,
    previous: dict[str, object],
    started: datetime,
    next_check: datetime,
    exc: Exception,
) -> None:
    payload = {
        **previous,
        "schema_version": 1,
        "service": "m9_market_data_service",
        "status": "calendar_unavailable",
        "healthy": False,
        "last_cycle_started_at_utc": _iso(started),
        "last_cycle_finished_at_utc": _iso(_utc_now()),
        "next_check_at_utc": _iso(next_check),
        "schedule": None,
        "cycle": None,
        "diagnostics_zh": [
            "交易日历暂时不可用；未启动行情写入，服务会在下一调度周期自动重试。",
            f"错误：{type(exc).__name__}: {exc}",
        ],
    }
    write_market_data_service_status(STATUS_PATH, payload)


def run_service_cycle(
    *,
    force: bool,
    retry_policy: RetryPolicy,
    interval_seconds: int,
) -> int:
    started = _utc_now()
    next_check = started + timedelta(seconds=interval_seconds)
    previous = read_market_data_service_status(STATUS_PATH)

    if not CATALOG_PATH.exists():
        payload = {
            **previous,
            "schema_version": 1,
            "service": "m9_market_data_service",
            "status": "catalog_missing",
            "healthy": False,
            "last_cycle_started_at_utc": _iso(started),
            "last_cycle_finished_at_utc": _iso(_utc_now()),
            "next_check_at_utc": _iso(next_check),
            "schedule": None,
            "cycle": None,
            "diagnostics_zh": ["本地 A 股数据库尚未初始化；自动服务不会创建不完整数据。"],
        }
        write_market_data_service_status(STATUS_PATH, payload)
        return 2

    try:
        clock = latest_closed_trade_clock(build_provider())
    except Exception as exc:  # noqa: BLE001 - provider/calendar service boundary
        _write_calendar_failure(
            previous=previous,
            started=started,
            next_check=next_check,
            exc=exc,
        )
        return 2

    decision = evaluate_market_data_schedule(
        target_trade_date=clock.target,
        last_success_trade_date=_last_success_trade_date(previous),
        force=force,
    )
    if not decision.due:
        payload = {
            **previous,
            "schema_version": 1,
            "service": "m9_market_data_service",
            "status": "idle_current",
            "healthy": bool(previous.get("healthy")),
            "target_trade_date": decision.target_trade_date,
            "last_cycle_started_at_utc": _iso(started),
            "last_cycle_finished_at_utc": _iso(_utc_now()),
            "next_check_at_utc": _iso(next_check),
            "calendar_source": clock.calendar_source,
            "schedule": decision.as_payload(),
            "diagnostics_zh": ["本地行情已覆盖最新收盘交易日，本轮为幂等空操作。"],
        }
        write_market_data_service_status(STATUS_PATH, payload)
        return 0

    cycle = execute_market_data_cycle(
        run_step=_run_step,
        retry_policy=retry_policy,
        steps=DEFAULT_STEPS,
    )
    healthy = bool(cycle["healthy"])
    last_success = decision.target_trade_date if healthy else _last_success_trade_date(previous)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "service": "m9_market_data_service",
        "status": cycle["overall_status"],
        "healthy": healthy,
        "target_trade_date": decision.target_trade_date,
        "last_success_trade_date": last_success,
        "last_cycle_started_at_utc": _iso(started),
        "last_cycle_finished_at_utc": _iso(_utc_now()),
        "next_check_at_utc": _iso(next_check),
        "calendar_source": clock.calendar_source,
        "schedule": decision.as_payload(),
        "cycle": cycle,
        "diagnostics_zh": cycle["diagnostics_zh"],
    }
    write_market_data_service_status(STATUS_PATH, payload)
    return 0 if healthy else 2


def main() -> int:
    args = parse_args()
    interval_seconds = max(60, int(args.interval_seconds))
    retry_policy = RetryPolicy(
        max_attempts=max(1, int(args.max_attempts)),
        base_delay_seconds=max(0.0, float(args.base_delay)),
    )
    lock = OperatorCacheProcessLock(
        LOCK_PATH,
        timeout_seconds=1.0,
        poll_interval_seconds=0.05,
    )
    try:
        lock.acquire()
    except TimeoutError:
        print("[HT-CN M9.1] 自动行情服务已有实例在运行。", flush=True)
        return 3

    try:
        while True:
            code = run_service_cycle(
                force=bool(args.run_now),
                retry_policy=retry_policy,
                interval_seconds=interval_seconds,
            )
            if args.once:
                return code
            args.run_now = False
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("[HT-CN M9.1] 自动行情服务已停止。", flush=True)
        return 130
    finally:
        lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
