from __future__ import annotations

import argparse
import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from htcn.app.harmonic_analysis_runtime import (
    evaluate_harmonic_analysis_schedule,
    execute_harmonic_analysis_cycle,
    read_harmonic_analysis_runtime_status,
    write_harmonic_analysis_runtime_status,
)
from htcn.app.market_data_service import read_market_data_service_status
from htcn.app.operator_input_identity import build_operator_cache_input_identity
from htcn.app.operator_process_lock import OperatorCacheProcessLock
from htcn.app.operator_queue import discover_local_instruments
from htcn.app.operator_snapshot import latest_local_trade_date
from htcn.app.source_clock_lifecycle_service import M3SourceClockHarmonicService

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "market"
CATALOG_PATH = DATA_ROOT / "catalog.duckdb"
RUNTIME_ROOT = DATA_ROOT / "runtime"
MARKET_DATA_STATUS_PATH = RUNTIME_ROOT / "m9-market-data-service.json"
STATUS_PATH = RUNTIME_ROOT / "m9-harmonic-analysis-runtime.json"
LOCK_PATH = RUNTIME_ROOT / "m9-harmonic-analysis-runtime.lock"
OPERATOR_CACHE_ROOT = ROOT / "data" / "product" / "m5" / "operator_queue"
DEFAULT_INTERVAL_SECONDS = 300
DEFAULT_BARS = 420
DEFAULT_SCALES = (3, 5, 8, 13)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="HT-CN M9.2 automated harmonic analysis runtime"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="evaluate one analysis cycle and exit",
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="force harmonic analysis even when the runtime watermark is current",
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=DEFAULT_INTERVAL_SECONDS,
        help="watch-mode polling interval; minimum 60 seconds",
    )
    parser.add_argument("--bars", type=int, default=DEFAULT_BARS)
    parser.add_argument(
        "--scales",
        default=",".join(str(value) for value in DEFAULT_SCALES),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, min(16, int(os.getenv("HTCN_OPERATOR_WORKERS", "4")))),
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


def _input_identity():
    return build_operator_cache_input_identity(
        data_root=DATA_ROOT,
        project_root=ROOT,
    )


def _service_factory() -> M3SourceClockHarmonicService:
    return M3SourceClockHarmonicService(DATA_ROOT)


def _target_trade_date(market_status: dict[str, object]) -> str | None:
    market_success = _optional_text(market_status.get("last_success_trade_date"))
    if market_success is not None:
        return market_success
    return latest_local_trade_date(CATALOG_PATH)


def _write_failure(
    *,
    previous: dict[str, object],
    started: datetime,
    next_check: datetime,
    status: str,
    diagnostics_zh: list[str],
    target_trade_date: str | None = None,
    schedule: dict[str, object] | None = None,
) -> None:
    payload = {
        **previous,
        "schema_version": 1,
        "service": "m9_harmonic_analysis_runtime",
        "status": status,
        "healthy": False,
        "target_trade_date": target_trade_date,
        "last_cycle_started_at_utc": _iso(started),
        "last_cycle_finished_at_utc": _iso(_utc_now()),
        "next_check_at_utc": _iso(next_check),
        "schedule": schedule,
        "cycle": None,
        "diagnostics_zh": diagnostics_zh,
    }
    write_harmonic_analysis_runtime_status(STATUS_PATH, payload)


def run_service_cycle(
    *,
    force: bool,
    interval_seconds: int,
    bars: int,
    scales: tuple[int, ...],
    workers: int,
) -> int:
    started = _utc_now()
    next_check = started + timedelta(seconds=interval_seconds)
    previous = read_harmonic_analysis_runtime_status(STATUS_PATH)
    market_status = read_market_data_service_status(MARKET_DATA_STATUS_PATH)

    if not CATALOG_PATH.exists():
        _write_failure(
            previous=previous,
            started=started,
            next_check=next_check,
            status="catalog_missing",
            diagnostics_zh=[
                "本地 A 股数据库尚未初始化；自动谐波运行时不会在缺失 canonical 数据时启动。"
            ],
        )
        return 2

    instruments = discover_local_instruments(DATA_ROOT, limit=0)
    if not instruments:
        _write_failure(
            previous=previous,
            started=started,
            next_check=next_check,
            status="universe_empty",
            diagnostics_zh=["本地初始化标的为空；自动谐波运行时等待数据服务完成初始化。"],
        )
        return 2

    target_trade_date = _target_trade_date(market_status)
    if target_trade_date is None:
        _write_failure(
            previous=previous,
            started=started,
            next_check=next_check,
            status="target_trade_date_unresolved",
            diagnostics_zh=["无法确定最新 canonical 交易日；本轮不执行谐波分析。"],
        )
        return 2

    try:
        input_identity = _input_identity()
    except (FileNotFoundError, OSError, ValueError) as exc:
        _write_failure(
            previous=previous,
            started=started,
            next_check=next_check,
            status="input_identity_unavailable",
            target_trade_date=target_trade_date,
            diagnostics_zh=[
                "无法建立谐波分析输入身份；本轮不会推进成功水位。",
                f"错误：{type(exc).__name__}: {exc}",
            ],
        )
        return 2

    decision = evaluate_harmonic_analysis_schedule(
        target_trade_date=target_trade_date,
        input_identity_fingerprint=input_identity.fingerprint,
        last_success_trade_date=previous.get("last_success_trade_date"),
        last_success_input_identity_fingerprint=previous.get(
            "last_success_input_identity_fingerprint"
        ),
        force=force,
    )
    if not decision.due:
        payload = {
            **previous,
            "schema_version": 1,
            "service": "m9_harmonic_analysis_runtime",
            "status": "idle_current",
            "healthy": bool(previous.get("healthy")),
            "target_trade_date": target_trade_date,
            "last_cycle_started_at_utc": _iso(started),
            "last_cycle_finished_at_utc": _iso(_utc_now()),
            "next_check_at_utc": _iso(next_check),
            "schedule": decision.as_payload(),
            "diagnostics_zh": [
                "谐波分析水位已覆盖当前 canonical 数据身份，本轮为幂等空操作。"
            ],
        }
        write_harmonic_analysis_runtime_status(STATUS_PATH, payload)
        return 0

    retrying_degraded = str(previous.get("status") or "") in {
        "degraded",
        "analysis_failed",
        "runtime_contract_failed",
    }
    try:
        cycle = execute_harmonic_analysis_cycle(
            _service_factory(),
            instruments,
            cache_root=OPERATOR_CACHE_ROOT,
            expected_trade_date=target_trade_date,
            input_identity=input_identity,
            input_identity_factory=_input_identity,
            bars=bars,
            scales=scales,
            force_refresh=bool(force or retrying_degraded),
            max_workers=workers,
            service_factory=_service_factory,
        )
    except Exception as exc:  # noqa: BLE001 - product runtime service boundary
        _write_failure(
            previous=previous,
            started=started,
            next_check=next_check,
            status="analysis_failed",
            target_trade_date=target_trade_date,
            schedule=decision.as_payload(),
            diagnostics_zh=[
                "自动谐波分析失败；成功水位保持不变，服务会在下一调度周期重试。",
                f"错误：{type(exc).__name__}: {exc}",
            ],
        )
        return 2

    healthy = bool(cycle["healthy"])
    payload: dict[str, Any] = {
        "schema_version": 1,
        "service": "m9_harmonic_analysis_runtime",
        "status": cycle["overall_status"],
        "healthy": healthy,
        "target_trade_date": target_trade_date,
        "last_success_trade_date": (
            target_trade_date
            if healthy
            else previous.get("last_success_trade_date")
        ),
        "last_success_input_identity_fingerprint": (
            input_identity.fingerprint
            if healthy
            else previous.get("last_success_input_identity_fingerprint")
        ),
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
    write_harmonic_analysis_runtime_status(STATUS_PATH, payload)
    return 0 if healthy else 2


def _parse_scales(raw: str) -> tuple[int, ...]:
    values = tuple(
        sorted(
            {
                int(part.strip())
                for part in str(raw).split(",")
                if part.strip()
            }
        )
    )
    if not values or any(value <= 0 for value in values):
        raise ValueError("--scales must contain positive comma-separated integers")
    return values


def main() -> int:
    args = parse_args()
    interval_seconds = max(60, int(args.interval_seconds))
    bars = max(80, int(args.bars))
    workers = max(1, min(16, int(args.workers)))
    try:
        scales = _parse_scales(args.scales)
    except ValueError as exc:
        print(f"[HT-CN M9.2] 参数错误：{exc}", flush=True)
        return 2

    lock = OperatorCacheProcessLock(
        LOCK_PATH,
        timeout_seconds=1.0,
        poll_interval_seconds=0.05,
    )
    try:
        lock.acquire()
    except TimeoutError:
        print("[HT-CN M9.2] 自动谐波分析运行时已有实例在运行。", flush=True)
        return 3

    try:
        while True:
            code = run_service_cycle(
                force=bool(args.run_now),
                interval_seconds=interval_seconds,
                bars=bars,
                scales=scales,
                workers=workers,
            )
            if args.once:
                return code
            args.run_now = False
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("[HT-CN M9.2] 自动谐波分析运行时已停止。", flush=True)
        return 130
    finally:
        lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
