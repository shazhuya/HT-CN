from __future__ import annotations

import tempfile
from datetime import date, timedelta
from pathlib import Path

from htcn.data.catalog import DataCatalog
from htcn.data.providers import AkShareProvider, BaoStockProvider, FailoverProvider
from htcn.data.store import ParquetDailyStore
from htcn.data.sync import sync_daily
from htcn.data.validation import normalize_daily


SYMBOLS = ["SSE.688256", "SZSE.300820", "SSE.688300"]


def main() -> int:
    print("[HT-CN M1 LIVE] Initializing providers...", flush=True)
    primary = AkShareProvider()
    backup = BaoStockProvider()
    provider = FailoverProvider(primary, backup)

    end = date.today()
    start = end - timedelta(days=120)

    print("[HT-CN M1 LIVE] Checking trading calendar...", flush=True)
    calendar = provider.get_trade_calendar(start, end)
    if not calendar:
        raise RuntimeError("No trading days returned by either provider")
    print(f"[HT-CN M1 LIVE] Calendar OK: {len(calendar)} trading days via {provider.last_provider}")

    print("[HT-CN M1 LIVE] Checking security master...", flush=True)
    securities = provider.list_securities()
    if len(securities) < 1000:
        raise RuntimeError(f"Security master unexpectedly small: {len(securities)}")
    print(f"[HT-CN M1 LIVE] Security master OK: {len(securities)} instruments via {provider.last_provider}")

    with tempfile.TemporaryDirectory(prefix="htcn-m1-live-") as temp_dir:
        root = Path(temp_dir)
        store = ParquetDailyStore(root / "daily")
        catalog = DataCatalog(root / "catalog.duckdb")

        for instrument_id in SYMBOLS:
            print(f"[HT-CN M1 LIVE] Syncing {instrument_id}...", flush=True)
            frame = sync_daily(
                provider=provider,
                store=store,
                catalog=catalog,
                instrument_id=instrument_id,
                start=start,
                end=end,
            )
            frame = normalize_daily(frame)
            if frame.empty:
                raise RuntimeError(f"No daily data returned for {instrument_id}")
            if frame["trade_date"].duplicated().any():
                raise RuntimeError(f"Duplicate trade dates for {instrument_id}")
            print(
                f"[HT-CN M1 LIVE] {instrument_id}: {len(frame)} rows, "
                f"{frame['trade_date'].min().date()} -> {frame['trade_date'].max().date()}, "
                f"provider={provider.last_provider}",
                flush=True,
            )

        print("[HT-CN M1 LIVE] Re-running one symbol to verify incremental idempotency...", flush=True)
        before = len(store.read(SYMBOLS[0], start, end))
        sync_daily(
            provider=provider,
            store=store,
            catalog=catalog,
            instrument_id=SYMBOLS[0],
            start=start,
            end=end,
        )
        after = len(store.read(SYMBOLS[0], start, end))
        if before != after:
            raise RuntimeError(f"Incremental sync changed row count: {before} -> {after}")

    print("[HT-CN M1 LIVE] PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
