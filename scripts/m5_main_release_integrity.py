from __future__ import annotations

import argparse
import json
from pathlib import Path

from htcn.app.main_release_integrity import (
    write_main_release_integrity_report,
)

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "HT-CN M5 Phase22: verify formal-main release lineage integrity."
        )
    )
    parser.add_argument(
        "--output",
        default="artifacts/reports/m5-main-release-integrity.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload, code = write_main_release_integrity_report(
        repo=ROOT,
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
    return int(code)


if __name__ == "__main__":
    raise SystemExit(main())
