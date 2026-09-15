from __future__ import annotations

import argparse
import random
import time
from datetime import date
from pathlib import Path

import pandas as pd

from htcn.data.catalog import DataCatalog
from htcn.data.providers import AkShareProvider, AkShareSinaProvider, BaoStockProvider, FailoverProvider
from htcn.data.store import ParquetDailyStore
from htcn.data.sync import sync_daily
from htcn.data.universe import SUPPORTED_INITIAL_DAILY_PREFIXES


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "market"
CATALOG_PATH = DATA_ROOT / "catalog.duckdb"
DAILY_ROOT = DATA_ROOT / "daily"
START_DATE = date(1990, 1, 1)


def build_provider() -> FailoverProvider:
    return FailoverProvider(
        AkShareProvider(),
        FailoverProvider(AkShareSinaProvider(), BaoStockProvider()),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HT-CN SSE/SZSE daily incremental updater")
    parser.add_argument("--limit", type=int, default=0, help="0 means all initialized SSE/SZSE datasets")
    parser.add_argument("--sleep", type=float, default=0.15)
    return parser.parse_args()


def _result_source(result: pd.DataFrame, provider: FailoverProvider) -> str:
    if not result.empty and "source" in result.columns:
        values = result["source"].dropna()
        if not values.empty:
            return str(values.iloc[-1])
    return str(provider.last_provider or "unknown")


def main() -> int:
    args = parse_args()
    print("[HT-CN M1 DAILY] Starting incremental update...", flush=True)
    if not CATALOG_PATH.exists():
        print("[HT-CN M1 DAILY] Database not found. Run initializer first.", flush=True)
        return 1

    catalog = DataCatalog(CATALOG_PATH)
    store = ParquetDailyStore(DAILY_ROOT)
    provider = build_provider()

    # Bulk-load metadata once. The old implementation opened DuckDB once per market
    # security just to discover initialized datasets; at full-market scale that can look
    # like a hang before the first progress line appears.
    listed_ids = set(catalog.list_security_ids(listed_only=True))
    dataset_rows = catalog.list_daily_datasets()
    metadata_by_id = {
        str(row["instrument_id"]): row
        for row in dataset_rows
        if str(row["instrument_id"]) in listed_ids
        and str(row["instrument_id"]).startswith(SUPPORTED_INITIAL_DAILY_PREFIXES)
    }
    candidates = sorted(metadata_by_id)

    if args.limit > 0:
        candidates = candidates[: args.limit]

    print(
        f"[HT-CN M1 DAILY] Initialized listed SSE/SZSE datasets to update: {len(candidates)}",
        flush=True,
    )
    if not candidates:
        print("[HT-CN M1 DAILY] Nothing to update. PASS", flush=True)
        return 0

    end = date.today()
    updated = 0
    unchanged = 0
    failed = 0

    for index, instrument_id in enumerate(candidates, start=1):
        before_last = metadata_by_id[instrument_id].get("last_trade_date")
        try:
            result = sync_daily(
                provider=provider,
                store=store,
                catalog=catalog,
                instrument_id=instrument_id,
                start=START_DATE,
                end=end,
            )
            after_last = None
            if not result.empty:
                after_last = pd.Timestamp(result["trade_date"].max()).date()
            if after_last != before_last:
                updated += 1
                state = "UPDATED"
            else:
                unchanged += 1
                state = "CURRENT"
            print(
                f"[HT-CN M1 DAILY] [{index}/{len(candidates)}] {state} {instrument_id}: "
                f"rows={len(result)}, last={after_last}, source={_result_source(result, provider)}",
                flush=True,
            )
        except KeyboardInterrupt:
            print("\n[HT-CN M1 DAILY] Interrupted. Existing data remains safe.", flush=True)
            return 130
        except Exception as exc:
            failed += 1
            print(
                f"[HT-CN M1 DAILY] [{index}/{len(candidates)}] FAILED {instrument_id}: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )

        if args.sleep > 0:
            time.sleep(args.sleep + random.uniform(0.0, min(0.1, args.sleep)))

    print(
        f"[HT-CN M1 DAILY] DONE updated={updated}, current={unchanged}, failed={failed}",
        flush=True,
    )
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
