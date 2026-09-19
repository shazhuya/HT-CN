from __future__ import annotations

import argparse
import json
from pathlib import Path

from htcn.app.operator_history import query_operator_history


ROOT = Path(__file__).resolve().parents[1]
HISTORY_ROOT = ROOT / "data" / "product" / "m5" / "operator_history"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Query product-only M5 daily Operator history."
    )
    parser.add_argument("--instrument")
    parser.add_argument("--display-key")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--all-revisions", action="store_true")
    parser.add_argument("--limit", type=int, default=60)
    args = parser.parse_args()

    payload = query_operator_history(
        history_root=HISTORY_ROOT,
        instrument_id=args.instrument,
        display_key=args.display_key,
        start_trade_date=args.start,
        end_trade_date=args.end,
        latest_revision_per_day=not args.all_revisions,
        limit=max(1, int(args.limit)),
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
