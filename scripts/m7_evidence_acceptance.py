from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from htcn.research.m7_evidence_acceptance import assess_m7_evidence_bundle


def _read_receipt(path: str | None) -> dict | None:
    if not path:
        return None
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("previous receipt must be a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only M7 evidence-bundle acceptance and idempotency audit."
        )
    )
    parser.add_argument("bundle")
    parser.add_argument("--previous-receipt")
    parser.add_argument("--expected-baseline-trade-date")
    parser.add_argument("--output")
    args = parser.parse_args()

    result = assess_m7_evidence_bundle(
        args.bundle,
        previous_receipt=_read_receipt(args.previous_receipt),
        expected_baseline_trade_date=args.expected_baseline_trade_date,
    )
    payload = result.as_payload()
    payload["generated_at_utc"] = datetime.now(UTC).isoformat()

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
            encoding="utf-8",
        )

    print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if result.status == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
