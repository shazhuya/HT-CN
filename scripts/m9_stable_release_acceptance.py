from __future__ import annotations

import argparse
import json
from pathlib import Path

from htcn.app.stable_release_acceptance import evaluate_stable_release_acceptance

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run HT-CN M9.6 Stable Product Release Acceptance"
    )
    parser.add_argument(
        "--release-report",
        default="artifacts/reports/m9-release-package.json",
    )
    parser.add_argument(
        "--output",
        default="artifacts/reports/m9-stable-release-acceptance.json",
    )
    args = parser.parse_args()

    release_report = json.loads(
        (ROOT / args.release_report).read_text(encoding="utf-8")
    )
    payload = evaluate_stable_release_acceptance(
        ROOT,
        release_report=release_report,
    )
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["accepted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
