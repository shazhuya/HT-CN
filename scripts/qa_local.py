from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
WEB_DIR = ROOT / "apps" / "web"
SCREENSHOT_DIR = ROOT / "artifacts" / "screenshots"


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print(f"[HT-CN QA] RUN: {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, cwd=str(cwd or ROOT), check=True)


def wait_for_port(host: str, port: int, timeout: float = 30.0) -> None:
    import socket

    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            if sock.connect_ex((host, port)) == 0:
                return
        time.sleep(0.25)
    raise RuntimeError(f"Timed out waiting for {host}:{port}")


def terminate(proc: subprocess.Popen[bytes] | subprocess.Popen[str] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def main() -> int:
    os.chdir(ROOT)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    if not VENV_PYTHON.exists():
        print("[HT-CN QA] ERROR: .venv not found. Run install script first.", file=sys.stderr)
        return 2
    if not (WEB_DIR / "node_modules").exists():
        print("[HT-CN QA] ERROR: web dependencies not found. Run install script first.", file=sys.stderr)
        return 2

    api: subprocess.Popen[bytes] | None = None
    web: subprocess.Popen[bytes] | None = None

    try:
        print("[HT-CN QA] 1/6 Deterministic Python regression", flush=True)
        run([str(VENV_PYTHON), "-m", "pytest", "-q"])

        print("[HT-CN QA] 2/6 Web type-check + build", flush=True)
        run(["npm.cmd", "run", "build"], cwd=WEB_DIR)

        print("[HT-CN QA] 3/6 Real M1 metadata / tradability read smoke", flush=True)
        run([
            str(VENV_PYTHON),
            "scripts/m3_metadata_tradability_smoke.py",
            "--catalog",
            "data/market/catalog.duckdb",
            "--require-parquet",
        ])

        print("[HT-CN QA] 4/6 Real M1 product payload contract smoke", flush=True)
        run([
            str(VENV_PYTHON),
            "scripts/m3_product_contract_smoke.py",
            "--data-root",
            "data/market",
            "--max-samples",
            "8",
        ])

        print("[HT-CN QA] 5/6 Start local API + Workbench", flush=True)
        api = subprocess.Popen(
            [
                str(VENV_PYTHON),
                "-m",
                "uvicorn",
                "services.api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8765",
            ],
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        web = subprocess.Popen(
            ["npm.cmd", "run", "dev", "--", "--host", "127.0.0.1"],
            cwd=str(WEB_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        wait_for_port("127.0.0.1", 8765)
        wait_for_port("127.0.0.1", 5173)

        print("[HT-CN QA] 6/6 Full Playwright browser acceptance", flush=True)
        run(["npx.cmd", "playwright", "test"], cwd=WEB_DIR)

        print("[HT-CN QA] PASS", flush=True)
        print(
            "[HT-CN QA] reports: m3-metadata-tradability-smoke.json / "
            "m3-product-contract-smoke.json / playwright/index.html",
            flush=True,
        )
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"[HT-CN QA] FAIL: command exited with code {exc.returncode}", file=sys.stderr)
        return exc.returncode or 1
    except Exception as exc:
        print(f"[HT-CN QA] FAIL: {exc}", file=sys.stderr)
        return 1
    finally:
        terminate(web)
        terminate(api)


if __name__ == "__main__":
    raise SystemExit(main())
