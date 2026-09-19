from __future__ import annotations

import argparse
import json
from pathlib import Path

from htcn.app.real_closeout_preflight import (
    write_real_closeout_preflight_report,
)


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "HT-CN M5 Phase23: read-only safety preflight before the "
            "private-M1 final closeout chain."
        )
    )
    parser.add_argument(
        "--output",
        default="artifacts/reports/m5-real-closeout-preflight.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload, code = write_real_closeout_preflight_report(
        root=ROOT,
        output=args.output,
    )
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        ),
        flush=True,
    )
    if code:
        print(
            "[HT-CN M5 PREFLIGHT] BLOCKED BEFORE M1/PRODUCT MUTATION -> "
            + str(args.output),
            flush=True,
        )
    else:
        suffix = " WITH WARNINGS" if payload["warning_count"] else ""
        print(
            "[HT-CN M5 PREFLIGHT] READY" + suffix + " -> " + str(args.output),
            flush=True,
        )
    return int(code)


if __name__ == "__main__":
    raise SystemExit(main())
