from __future__ import annotations

import argparse
import json
from pathlib import Path

from htcn.app.stable_release_acceptance import write_stable_release_acceptance

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate HT-CN Stable product release")
    parser.add_argument("--release-report", default="artifacts/reports/m9-release-package.json")
    parser.add_argument("--output", default="artifacts/reports/m9-stable-release-acceptance.json")
    args = parser.parse_args()
    payload, code = write_stable_release_acceptance(
        root=ROOT,
        release_report_path=ROOT / args.release_report,
        output=args.output,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
