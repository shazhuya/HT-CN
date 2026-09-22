from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from htcn.app.evidence_identity import read_code_identity
from htcn.app.operator_process_lock import OperatorCacheProcessLock
from htcn.app.product_migration import ensure_product_state_schema
from htcn.app.product_supervisor import (
    ChildRuntime,
    ChildSpec,
    RestartPolicy,
    aggregate_supervisor_state,
    child_restart_due,
    mark_child_running,
    record_child_exit,
    write_product_supervisor_status,
)

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT / "data" / "market" / "runtime"
STATUS_PATH = RUNTIME_ROOT / "m9-product-supervisor.json"
LOCK_PATH = RUNTIME_ROOT / "m9-product-supervisor.lock"
STOP_PATH = RUNTIME_ROOT / "m9-product-supervisor.stop"
LOG_ROOT = ROOT / "artifacts" / "logs" / "m9-product-supervisor"
WEB_DIST = ROOT / "apps" / "web" / "dist"


def child_specs() -> tuple[ChildSpec, ...]:
    python = sys.executable
    return (
        ChildSpec(
            "api",
            (
                python,
                "-m",
                "uvicorn",
                "services.api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8765",
            ),
            critical=True,
        ),
        ChildSpec(
            "web",
            (
                python,
                "-m",
                "http.server",
                "5173",
                "--bind",
                "127.0.0.1",
                "--directory",
                str(WEB_DIST),
            ),
            critical=True,
        ),
        ChildSpec(
            "market_data",
            (python, "scripts/m9_market_data_service.py"),
        ),
        ChildSpec(
            "harmonic_runtime",
            (python, "scripts/m9_harmonic_analysis_runtime.py"),
        ),
        ChildSpec(
            "background_evidence",
            (python, "scripts/m9_background_evidence_service.py"),
        ),
    )


def _diagnostics(state: str, children: dict[str, ChildRuntime]) -> list[str]:
    if state == "healthy":
        return ["HT-CN 产品运行层正常；API、Web 与后台服务均在运行。"]
    crash = [item.name for item in children.values() if item.status == "crash_loop"]
    backoff = [item.name for item in children.values() if item.status == "backoff"]
    rows: list[str] = []
    if state == "blocked":
        rows.append("产品运行层被关键服务 crash-loop 阻断；请使用恢复入口查看日志后重启。")
    else:
        rows.append("产品运行层正在自动恢复部分子服务；工作台可能暂时显示旧数据。")
    if crash:
        rows.append("Crash-loop：" + "、".join(crash) + "。")
    if backoff:
        rows.append("退避重启中：" + "、".join(backoff) + "。")
    return rows


def _write_status(
    *,
    children: dict[str, ChildRuntime],
    identity_payload: dict[str, object],
    product_state: dict[str, Any],
    status_override: str | None = None,
) -> None:
    state = status_override or aggregate_supervisor_state(list(children.values()))
    payload = {
        "schema_version": 1,
        "service": "m9_product_supervisor",
        "status": state,
        "healthy": state == "healthy",
        "supervisor_pid": os.getpid(),
        "release_identity": identity_payload,
        "product_state_schema": product_state,
        "children": {
            name: runtime.as_payload()
            for name, runtime in sorted(children.items())
        },
        "static_web": {
            "mode": "built_static",
            "url": "http://127.0.0.1:5173",
            "vite_required": False,
        },
        "api": {
            "url": "http://127.0.0.1:8765",
        },
        "diagnostics_zh": (
            ["产品运行前置检查完成。"]
            if status_override == "ready"
            else ["HT-CN 已停止。"]
            if status_override == "stopped"
            else _diagnostics(state, children)
        ),
    }
    write_product_supervisor_status(STATUS_PATH, payload)


def _spawn(spec: ChildSpec, runtime: ChildRuntime) -> subprocess.Popen[bytes]:
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    log_path = LOG_ROOT / f"{spec.name}.log"
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with log_path.open("ab") as log:
        process = subprocess.Popen(
            spec.command,
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
        )
    mark_child_running(runtime, pid=process.pid)
    return process


def _stop_processes(processes: dict[str, subprocess.Popen[bytes]]) -> None:
    for process in processes.values():
        if process.poll() is None:
            process.terminate()
    deadline = time.monotonic() + 10
    for process in processes.values():
        if process.poll() is not None:
            continue
        remaining = max(0.0, deadline - time.monotonic())
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            process.kill()


def _preflight() -> tuple[dict[str, object], dict[str, Any]]:
    identity = read_code_identity(ROOT)
    if identity.head is None or not identity.worktree_clean:
        raise RuntimeError(
            "代码身份校验失败；开发态必须 clean Git，安装包必须通过 release identity。"
        )
    if not (WEB_DIST / "index.html").is_file():
        raise RuntimeError("缺少已构建 Web：apps/web/dist/index.html")
    product_state = ensure_product_state_schema(ROOT)
    return identity.as_payload(), product_state


def run_supervisor(*, check_only: bool, poll_seconds: float) -> int:
    try:
        identity_payload, product_state = _preflight()
    except Exception as exc:  # noqa: BLE001 - product startup boundary
        write_product_supervisor_status(
            STATUS_PATH,
            {
                "schema_version": 1,
                "service": "m9_product_supervisor",
                "status": "blocked",
                "healthy": False,
                "supervisor_pid": os.getpid(),
                "release_identity": None,
                "children": {},
                "diagnostics_zh": [f"产品启动前置检查失败：{type(exc).__name__}: {exc}"],
            },
        )
        return 2

    specs = {item.name: item for item in child_specs()}
    children = {
        name: ChildRuntime(name=name, critical=spec.critical)
        for name, spec in specs.items()
    }
    if check_only:
        _write_status(
            children=children,
            identity_payload=identity_payload,
            product_state=product_state,
            status_override="ready",
        )
        return 0

    lock = OperatorCacheProcessLock(
        LOCK_PATH,
        timeout_seconds=1.0,
        poll_interval_seconds=0.05,
    )
    try:
        lock.acquire()
    except TimeoutError:
        return 3

    STOP_PATH.unlink(missing_ok=True)
    policy = RestartPolicy()
    processes: dict[str, subprocess.Popen[bytes]] = {}
    try:
        for name, spec in specs.items():
            processes[name] = _spawn(spec, children[name])
        while not STOP_PATH.exists():
            now = time.monotonic()
            for name, spec in specs.items():
                runtime = children[name]
                process = processes.get(name)
                if process is not None and runtime.status == "running":
                    code = process.poll()
                    if code is not None:
                        record_child_exit(
                            runtime,
                            exit_code=code,
                            now_monotonic=now,
                            policy=policy,
                        )
                        processes.pop(name, None)
                if child_restart_due(runtime, now_monotonic=now):
                    try:
                        processes[name] = _spawn(spec, runtime)
                    except OSError as exc:
                        record_child_exit(
                            runtime,
                            exit_code=127,
                            now_monotonic=now,
                            policy=policy,
                        )
                        runtime.last_error = f"{type(exc).__name__}: {exc}"
            _write_status(
                children=children,
                identity_payload=identity_payload,
                product_state=product_state,
            )
            time.sleep(max(0.2, poll_seconds))
    except KeyboardInterrupt:
        pass
    finally:
        _stop_processes(processes)
        for runtime in children.values():
            runtime.status = "stopped"
            runtime.pid = None
        _write_status(
            children=children,
            identity_payload=identity_payload,
            product_state=product_state,
            status_override="stopped",
        )
        STOP_PATH.unlink(missing_ok=True)
        lock.release()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="HT-CN M9.5 product supervisor")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=1.0)
    args = parser.parse_args()
    return run_supervisor(
        check_only=bool(args.check),
        poll_seconds=max(0.2, float(args.poll_seconds)),
    )


if __name__ == "__main__":
    raise SystemExit(main())
