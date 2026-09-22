from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class RestartPolicy:
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    max_restarts_in_window: int = 5
    window_seconds: float = 300.0


@dataclass(frozen=True, slots=True)
class ChildSpec:
    name: str
    command: tuple[str, ...]
    critical: bool = False


@dataclass(slots=True)
class ChildRuntime:
    name: str
    critical: bool
    status: str = "stopped"
    pid: int | None = None
    restart_count: int = 0
    failure_times: list[float] = field(default_factory=list)
    next_restart_at_monotonic: float | None = None
    last_exit_code: int | None = None
    last_error: str | None = None

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


def mark_child_running(runtime: ChildRuntime, *, pid: int) -> None:
    runtime.status = "running"
    runtime.pid = int(pid)
    runtime.next_restart_at_monotonic = None
    runtime.last_error = None


def record_child_exit(
    runtime: ChildRuntime,
    *,
    exit_code: int,
    now_monotonic: float,
    policy: RestartPolicy,
) -> None:
    runtime.pid = None
    runtime.last_exit_code = int(exit_code)
    runtime.restart_count += 1
    cutoff = now_monotonic - policy.window_seconds
    runtime.failure_times = [
        value for value in runtime.failure_times if value >= cutoff
    ]
    runtime.failure_times.append(now_monotonic)
    if len(runtime.failure_times) >= policy.max_restarts_in_window:
        runtime.status = "crash_loop"
        runtime.next_restart_at_monotonic = None
        runtime.last_error = (
            f"{runtime.name} entered crash loop after "
            f"{len(runtime.failure_times)} failures"
        )
        return
    delay = min(
        policy.max_delay_seconds,
        policy.base_delay_seconds * (2 ** max(0, len(runtime.failure_times) - 1)),
    )
    runtime.status = "backoff"
    runtime.next_restart_at_monotonic = now_monotonic + delay
    runtime.last_error = f"{runtime.name} exited with code {exit_code}"


def child_restart_due(runtime: ChildRuntime, *, now_monotonic: float) -> bool:
    return (
        runtime.status == "backoff"
        and runtime.next_restart_at_monotonic is not None
        and now_monotonic >= runtime.next_restart_at_monotonic
    )


def aggregate_supervisor_state(children: list[ChildRuntime]) -> str:
    if not children:
        return "blocked"
    if any(item.critical and item.status == "crash_loop" for item in children):
        return "blocked"
    if any(item.status != "running" for item in children):
        return "degraded"
    return "healthy"


def empty_product_supervisor_status() -> dict[str, object]:
    return {
        "schema_version": 1,
        "service": "m9_product_supervisor",
        "status": "not_started",
        "healthy": False,
        "supervisor_pid": None,
        "release_identity": None,
        "children": {},
        "last_backup": None,
        "diagnostics_zh": ["产品 supervisor 尚未启动。"],
    }


def read_product_supervisor_status(path: str | Path) -> dict[str, object]:
    target = Path(path)
    if not target.is_file():
        return empty_product_supervisor_status()
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fallback = empty_product_supervisor_status()
        fallback["status"] = "status_unreadable"
        fallback["diagnostics_zh"] = [
            f"产品 supervisor 状态不可读：{type(exc).__name__}"
        ]
        return fallback
    if not isinstance(payload, dict):
        fallback = empty_product_supervisor_status()
        fallback["status"] = "status_invalid"
        fallback["diagnostics_zh"] = ["产品 supervisor 状态格式无效。"]
        return fallback
    return payload


def write_product_supervisor_status(
    path: str | Path,
    payload: dict[str, Any],
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp.replace(target)
    return target
