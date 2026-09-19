from __future__ import annotations

import argparse
import json
from pathlib import Path

from htcn.app.review_followup_journal import query_review_journal

ROOT = Path(__file__).resolve().parents[1]
JOURNAL_ROOT = ROOT / "data" / "product" / "m5" / "review_journal"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Query M5 product review/follow-up journal."
    )
    parser.add_argument("--instrument")
    parser.add_argument("--display-key")
    parser.add_argument("--observation-id")
    parser.add_argument(
        "--state",
        choices=("unseen", "reviewed", "follow_up"),
    )
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    payload = query_review_journal(
        journal_root=JOURNAL_ROOT,
        display_key=args.display_key,
        instrument_id=args.instrument,
        source_observation_id=args.observation_id,
        review_state=args.state,
        limit=max(1, int(args.limit)),
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
