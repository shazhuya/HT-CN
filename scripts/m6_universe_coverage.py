from __future__ import annotations

import argparse
import json
from pathlib import Path

from htcn.app.universe_coverage import build_live_universe_coverage


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "market"
REPORT_PATH = ROOT / "artifacts" / "reports" / "m6-universe-coverage.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build the M6.3 machine-readable universe coverage contract report."
        )
    )
    parser.add_argument(
        "--skip-qfq",
        action="store_true",
        help="report product coverage without evaluating formal-QFQ readiness",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPORT_PATH,
    )
    args = parser.parse_args()

    payload = build_live_universe_coverage(
        DATA_ROOT,
        include_qfq=not args.skip_qfq,
    )
    output = args.output
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["status"] == "valid" else 2


if __name__ == "__main__":
    raise SystemExit(main())
