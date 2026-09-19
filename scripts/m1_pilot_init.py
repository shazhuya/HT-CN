from __future__ import annotations

from datetime import date
from pathlib import Path

from htcn.data.catalog import DataCatalog
from htcn.data.providers import AkShareProvider, BaoStockProvider, FailoverProvider
from htcn.data.store import ParquetDailyStore
from htcn.data.sync import sync_daily

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "market"
CATALOG_PATH = DATA_ROOT / "catalog.duckdb"
DAILY_ROOT = DATA_ROOT / "daily"

# Representative A-share pilot set. M1 validates the durable database path before
# the full-market initializer is enabled.
PILOT_SYMBOLS = [
    "SSE.688256",   # STAR
    "SZSE.300820",  # ChiNext
    "SSE.688300",   # STAR
    "SZSE.000001",  # Shenzhen main board
    "SSE.600519",   # Shanghai main board
]


def main() -> int:
    print(f"[HT-CN M1 INIT] Data root: {DATA_ROOT}", flush=True)
    DATA_ROOT.mkdir(parents=True, exist_ok=True)

    catalog = DataCatalog(CATALOG_PATH)
    store = ParquetDailyStore(DAILY_ROOT)
    provider = FailoverProvider(AkShareProvider(), BaoStockProvider())

    print("[HT-CN M1 INIT] Persisting A-share security master...", flush=True)
    securities = provider.list_securities()
    source = provider.last_provider or "unknown"
    saved = catalog.upsert_securities(securities, source=source)
    print(
        f"[HT-CN M1 INIT] Security master: {saved} incoming, "
        f"{catalog.security_count()} stored, source={source}",
        flush=True,
    )

    print("[HT-CN M1 INIT] Persisting trading calendar...", flush=True)
    calendar = provider.get_trade_calendar(date(1990, 1, 1), date.today())
    calendar_source = provider.last_provider or "unknown"
    catalog.record_trade_calendar(calendar, source=calendar_source)
    print(
        f"[HT-CN M1 INIT] Calendar: {catalog.calendar_count()} trading days, "
        f"source={calendar_source}",
        flush=True,
    )

    completed = 0
    failed: list[tuple[str, str]] = []
    for instrument_id in PILOT_SYMBOLS:
        print(f"[HT-CN M1 INIT] Syncing full history {instrument_id}...", flush=True)
        catalog.mark_task(instrument_id, "RUNNING")
        try:
            frame = sync_daily(
                provider=provider,
                store=store,
                catalog=catalog,
                instrument_id=instrument_id,
                start=date(1990, 1, 1),
                end=date.today(),
            )
            if frame.empty:
                raise RuntimeError("provider returned no history")
            catalog.mark_task(instrument_id, "COMPLETED")
            completed += 1
            print(
                f"[HT-CN M1 INIT] {instrument_id}: {len(frame)} rows, "
                f"{frame['trade_date'].min().date()} -> {frame['trade_date'].max().date()}, "
                f"provider={provider.last_provider}",
                flush=True,
            )
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            catalog.mark_task(instrument_id, "FAILED", message)
            failed.append((instrument_id, message))
            print(f"[HT-CN M1 INIT] FAILED {instrument_id}: {message}", flush=True)

    print(
        f"[HT-CN M1 INIT] Pilot complete: {completed}/{len(PILOT_SYMBOLS)} symbols",
        flush=True,
    )
    print(f"[HT-CN M1 INIT] Catalog: {CATALOG_PATH}", flush=True)
    print(f"[HT-CN M1 INIT] Daily files: {DAILY_ROOT}", flush=True)

    if failed:
        for instrument_id, message in failed:
            print(f"[HT-CN M1 INIT] RETRY NEEDED {instrument_id}: {message}", flush=True)
        return 1

    print("[HT-CN M1 INIT] PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
