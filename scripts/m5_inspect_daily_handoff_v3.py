from __future__ import annotations

import argparse
import json
from pathlib import Path

from htcn.app.handoff_v3_inspector import (
    build_handoff_v3_inspection,
    filter_handoff_v3_inspection,
    write_portable_review_workspace,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="HT-CN M5 Phase 15: inspect a verified handoff v3 ZIP without market DB."
    )
    parser.add_argument(
        "--bundle",
        default="artifacts/reports/htcn-daily-handoff-v3.zip",
    )
    parser.add_argument(
        "--json-output",
        default="artifacts/reports/m5-handoff-v3-inspector.json",
    )
    parser.add_argument(
        "--html-output",
        default="artifacts/reports/m5-handoff-v3-workspace.html",
    )
    parser.add_argument("--instrument", default="")
    parser.add_argument("--display-key", default="")
    parser.add_argument(
        "--query-only",
        action="store_true",
        help="Print filtered inspection JSON and do not write workspace artifacts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle = Path(args.bundle)

    if args.query_only:
        payload = build_handoff_v3_inspection(bundle)
        if args.instrument or args.display_key:
            payload = filter_handoff_v3_inspection(
                payload,
                instrument_id=args.instrument or None,
                display_key=args.display_key or None,
            )
        print(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                allow_nan=False,
            )
        )
        return 0

    result = write_portable_review_workspace(
        bundle_path=bundle,
        json_output=args.json_output,
        html_output=args.html_output,
    )
    if args.instrument or args.display_key:
        payload = build_handoff_v3_inspection(bundle)
        filtered = filter_handoff_v3_inspection(
            payload,
            instrument_id=args.instrument or None,
            display_key=args.display_key or None,
        )
        result["drilldown"] = filtered.get("drilldown")
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
