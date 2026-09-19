from __future__ import annotations

import argparse
import json
from pathlib import Path

from htcn.research.evidence_intake import audit_evidence_bundle


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit an M4 evidence bundle from authoritative baseline + transactions."
    )
    parser.add_argument("bundle")
    parser.add_argument(
        "--expected-baseline-trade-date",
        default="2026-09-17",
    )
    args = parser.parse_args()

    result = audit_evidence_bundle(
        Path(args.bundle),
        expected_baseline_trade_date=args.expected_baseline_trade_date,
    )
    print(json.dumps(result.as_payload(), ensure_ascii=False, indent=2))
    return 0 if result.status != "not_ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
