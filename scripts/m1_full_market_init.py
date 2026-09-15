from __future__ import annotations

import argparse
import random
import time
from datetime import date
from pathlib import Path

from htcn.data.catalog import DataCatalog
from htcn.data.providers import (
    AkShareProvider,
    AkShareSinaProvider,
    BaoStockProvider,
    FailoverProvider,
)
from htcn.data.store import ParquetDailyStore
from htcn.data.sync import sync_daily
from htcn.data.universe import select_initial_daily_candidates


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "market"
CATALOG_PATH = DATA_ROOT / "catalog.duckdb"
DAILY_ROOT = DATA_ROOT / "daily"
START_DATE = date(1990, 1, 1)


def build_provider() -> FailoverProvider:
    # Primary path: AKShare Eastmoney -> AKShare Sina -> BaoStock.
    # Nested FailoverProvider preserves the actual leaf provider name for provenance.
    return FailoverProvider(
        AkShareProvider(),
        FailoverProvider(AkShareSinaProvider(), BaoStockProvider()),
    )


def ensure_reference_data(catalog: DataCatalog, provider: FailoverProvider) -> None:
    if catalog.security_count() < 1000:
        print("[HT-CN M1 FULL] Refreshing security master...", flush=True)
        securities = provider.list_securities()
        source = provider.last_provider or "unknown"
        catalog.upsert_securities(securities, source=source)
        print(
            f"[HT-CN M1 FULL] Security master: {catalog.security_count()} stored, source={source}",
            flush=True,
        )

    if catalog.calendar_count() < 1000:
        print("[HT-CN M1 FULL] Refreshing trading calendar...", flush=True)
        days = provider.get_trade_calendar(START_DATE, date.today())
        source = provider.last_provider or "unknown"
        catalog.record_trade_calendar(days, source=source)
        print(
            f"[HT-CN M1 FULL] Calendar: {catalog.calendar_count()} days, source={source}",
            flush=True,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HT-CN resumable full A-share daily initializer")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="maximum supported instruments in this run; 0 means all remaining candidates",
    )
    parser.add_argument("--max-attempts", type=int, default=5)
    parser.add_argument("--retries", type=int, default=2, help="transient retries inside one task")
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.25,
        help="base seconds between instruments to reduce provider pressure",
    )
    parser.add_argument("--progress-every", type=int, default=25)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    DATA_ROOT.mkdir(parents=True, exist_ok=True)

    catalog = DataCatalog(CATALOG_PATH)
    store = ParquetDailyStore(DAILY_ROOT)
    provider = build_provider()
    ensure_reference_data(catalog, provider)

    all_candidates = catalog.sync_candidates(
        max_attempts=max(1, args.max_attempts),
        limit=None,
    )
    candidates, deferred_bse = select_initial_daily_candidates(
        all_candidates,
        limit=args.limit,
    )
    total_market = catalog.security_count()
    existing = catalog.daily_dataset_count()

    print(
        f"[HT-CN M1 FULL] Market={total_market}, existing datasets={existing}, "
        f"this run={len(candidates)}",
        flush=True,
    )
    if deferred_bse:
        print(
            f"[HT-CN M1 FULL] BSE deferred={deferred_bse}: 920-code history continuity "
            "adapter pending; this batch processes SSE+SZSE only.",
            flush=True,
        )

    if not candidates:
        print(
            "[HT-CN M1 FULL] No remaining SSE/SZSE instruments to initialize. PASS",
            flush=True,
        )
        return 0

    completed = 0
    failed = 0
    interrupted = False
    end = date.today()

    for index, instrument_id in enumerate(candidates, start=1):
        catalog.begin_task(instrument_id)
        print(
            f"[HT-CN M1 FULL] [{index}/{len(candidates)}] {instrument_id}...",
            flush=True,
        )

        success = False
        last_error = ""
        try:
            for retry in range(max(1, args.retries + 1)):
                try:
                    frame = sync_daily(
                        provider=provider,
                        store=store,
                        catalog=catalog,
                        instrument_id=instrument_id,
                        start=START_DATE,
                        end=end,
                    )
                    if frame.empty:
                        raise RuntimeError("provider returned no history")
                    success = True
                    break
                except KeyboardInterrupt:
                    raise
                except Exception as exc:
                    last_error = f"{type(exc).__name__}: {exc}"
                    if retry < args.retries:
                        delay = min(8.0, 1.0 * (2**retry))
                        print(
                            f"[HT-CN M1 FULL] retry {retry + 1}/{args.retries} "
                            f"after {delay:.1f}s: {last_error}",
                            flush=True,
                        )
                        time.sleep(delay)

            if success:
                catalog.finish_task(instrument_id, "COMPLETED")
                completed += 1
                metadata = catalog.get_daily(instrument_id) or {}
                print(
                    f"[HT-CN M1 FULL] OK {instrument_id}: rows={metadata.get('row_count')}, "
                    f"{metadata.get('first_trade_date')} -> {metadata.get('last_trade_date')}, "
                    f"source={metadata.get('source')}",
                    flush=True,
                )
            else:
                catalog.finish_task(instrument_id, "FAILED", last_error)
                failed += 1
                print(f"[HT-CN M1 FULL] FAILED {instrument_id}: {last_error}", flush=True)

        except KeyboardInterrupt:
            catalog.finish_task(instrument_id, "INTERRUPTED", "user interrupted process")
            interrupted = True
            print("\n[HT-CN M1 FULL] Interrupted safely. Re-run to resume.", flush=True)
            break

        if index % max(1, args.progress_every) == 0 or index == len(candidates):
            counts = catalog.task_counts()
            print(
                f"[HT-CN M1 FULL] PROGRESS run_ok={completed}, run_failed={failed}, "
                f"datasets={catalog.daily_dataset_count()}/{total_market}, tasks={counts}",
                flush=True,
            )

        if args.sleep > 0:
            jitter = random.uniform(0.0, min(0.25, args.sleep))
            time.sleep(args.sleep + jitter)

    print(
        f"[HT-CN M1 FULL] DONE: completed={completed}, failed={failed}, "
        f"datasets={catalog.daily_dataset_count()}/{total_market}",
        flush=True,
    )
    print(f"[HT-CN M1 FULL] Catalog: {CATALOG_PATH}", flush=True)
    print(f"[HT-CN M1 FULL] Daily root: {DAILY_ROOT}", flush=True)

    if interrupted:
        return 130
    # A few provider failures should not destroy the whole resumable run. They remain in
    # sync_task and are retried by later runs until max_attempts is reached.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
