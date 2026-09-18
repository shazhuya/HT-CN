from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb

from htcn.data.concepts import (
    build_concept_snapshots_from_local_market,
    concept_sync_is_fresh,
    sync_concept_memberships,
)
from htcn.data.providers import AkShareProvider


SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


def main() -> int:
    parser = argparse.ArgumentParser(description="HT-CN M3 concept/theme context sync")
    parser.add_argument("--catalog", default="data/market/catalog.duckdb")
    parser.add_argument("--data-root", default="data/market")
    parser.add_argument("--membership-refresh-days", type=int, default=7)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--force-membership-refresh", action="store_true")
    parser.add_argument("--output", default="artifacts/reports/m3-concept-context-sync.json")
    args = parser.parse_args()

    catalog = Path(args.catalog)
    if not catalog.exists():
        raise SystemExit(f"catalog not found: {catalog}")
    with duckdb.connect(str(catalog), read_only=True) as con:
        row = con.execute("SELECT MAX(trade_date) FROM trade_calendar").fetchone()
    if row is None or row[0] is None:
        raise SystemExit("trade_calendar has no local trade date")
    target = row[0]
    today = datetime.now(SHANGHAI_TZ).date()

    refresh = args.force_membership_refresh or not concept_sync_is_fresh(
        catalog, as_of=today, max_age_days=max(args.membership_refresh_days, 0)
    )
    membership = {"status": "fresh_cached_snapshot"}
    if refresh:
        membership = sync_concept_memberships(
            catalog_path=catalog,
            provider=AkShareProvider(),
            observed_on=today,
            workers=args.workers,
        )
    snapshots = build_concept_snapshots_from_local_market(
        catalog_path=catalog,
        data_root=args.data_root,
        target_date=target,
    )
    payload = {
        "schema_version": 1,
        "local_trade_date": str(target),
        "membership_refresh_needed": refresh,
        "membership": membership,
        "concept_snapshot_count": len(snapshots),
        "aggregate_method": "local_constituent_equal_weight_mean_and_median",
        "source_boundary": (
            "Eastmoney supplies concept membership only; concept strength/breadth/volume "
            "are recomputed from local M1 constituent bars."
        ),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    print(f"\n[M3] report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
