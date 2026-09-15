from __future__ import annotations

import argparse
import random
import time
from datetime import date
from pathlib import Path

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


def main() -> int:
    args = parse_args()
    if not CATALOG_PATH.exists():
        print("[HT-CN M1 DAILY] Database not found. Run initializer first.")
        return 1

    catalog = DataCatalog(CATALOG_PATH)
    store = ParquetDailyStore(DAILY_ROOT)
    provider = build_provider()

    candidates: list[str] = []
    for instrument_id in catalog.list_security_ids(listed_only=True):
        if not instrument_id.startswith(SUPPORTED_INITIAL_DAILY_PREFIXES):
            continue
        if catalog.get_daily(instrument_id) is not None:
            candidates.append(instrument_id)

    if args.limit > 0:
        candidates = candidates[: args.limit]

    print(f"[HT-CN M1 DAILY] Initialized SSE/SZSE datasets to update: {len(candidates)}")
    if not candidates:
        print("[HT-CN M1 DAILY] Nothing to update. PASS")
        return 0

    end = date.today()
    updated = 0
    unchanged = 0
    failed = 0

    for index, instrument_id in enumerate(candidates, start=1):
        before = catalog.get_daily(instrument_id) or {}
        before_last = before.get("last_trade_date")
        try:
            result = sync_daily(
                provider=provider,
                store=store,
                catalog=catalog,
                instrument_id=instrument_id,
                start=START_DATE,
                end=end,
            )
            after = catalog.get_daily(instrument_id) or {}
            after_last = after.get("last_trade_date")
            if after_last != before_last:
                updated += 1
                state = "UPDATED"
            else:
                unchanged += 1
                state = "CURRENT"
            print(
                f"[HT-CN M1 DAILY] [{index}/{len(candidates)}] {state} {instrument_id}: "
                f"rows={len(result)}, last={after_last}, source={after.get('source')}",
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
