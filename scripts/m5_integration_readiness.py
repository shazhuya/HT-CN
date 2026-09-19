from __future__ import annotations

import argparse
import json
from pathlib import Path

from htcn.app.integration_readiness import (
    write_integration_readiness_report,
)

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "HT-CN M5 Phase20: verify preserve-ancestry "
            "integration readiness against main."
        )
    )
    parser.add_argument("--main-ref", default="origin/main")
    parser.add_argument(
        "--output",
        default="artifacts/reports/m5-integration-readiness.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload, code = write_integration_readiness_report(
        repo=ROOT,
        output=args.output,
        main_ref=args.main_ref,
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
