from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from htcn.app.product_supervisor import read_product_supervisor_status

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT / "data" / "market" / "runtime"
STATUS_PATH = RUNTIME_ROOT / "m9-product-supervisor.json"
STOP_PATH = RUNTIME_ROOT / "m9-product-supervisor.stop"


def request_stop(*, wait_seconds: float = 15.0) -> int:
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    STOP_PATH.write_text("stop\n", encoding="utf-8")
    deadline = time.monotonic() + max(0.0, wait_seconds)
    while time.monotonic() < deadline:
        payload = read_product_supervisor_status(STATUS_PATH)
        if payload.get("status") in {"stopped", "not_started"}:
            return 0
        time.sleep(0.25)
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Control HT-CN product supervisor")
    parser.add_argument("action", choices=("stop", "status"))
    args = parser.parse_args()
    if args.action == "stop":
        return request_stop()
    print(
        json.dumps(
            read_product_supervisor_status(STATUS_PATH),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
