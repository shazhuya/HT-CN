from __future__ import annotations

from pathlib import Path

import pandas as pd

from htcn.data.catalog import DataCatalog
from htcn.data.delta import MarketDailyDeltaStore, compact_daily_deltas
from htcn.data.store import ParquetDailyStore


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "market"
CATALOG_PATH = DATA_ROOT / "catalog.duckdb"
DAILY_ROOT = DATA_ROOT / "daily"
DELTA_ROOT = DATA_ROOT / "daily_delta"


def main() -> int:
    if not CATALOG_PATH.exists():
        print("[HT-CN M1 COMPACT] Database not found.")
        return 1

    catalog = DataCatalog(CATALOG_PATH)
    base = ParquetDailyStore(DAILY_ROOT)
    deltas = MarketDailyDeltaStore(DELTA_ROOT)
    dates = deltas.list_dates()
    if not dates:
        print("[HT-CN M1 COMPACT] No delta files. PASS")
        return 0

    frames = [deltas.read_date(day) for day in dates]
    frames = [frame for frame in frames if not frame.empty]
    touched = sorted(
        set(pd.concat(frames, ignore_index=True)["instrument_id"].astype(str).tolist())
    ) if frames else []

    print(
        f"[HT-CN M1 COMPACT] Compacting {len(dates)} delta files across "
        f"{len(touched)} instruments...",
        flush=True,
    )
    instruments, rows = compact_daily_deltas(base=base, deltas=deltas, dates=dates)

    for index, instrument_id in enumerate(touched, start=1):
        frame = base.read(instrument_id)
        if frame.empty:
            continue
        catalog.record_daily(
            instrument_id=instrument_id,
            source="base+compacted_delta",
            parquet_path=str(base.path_for(instrument_id)),
            row_count=len(frame),
            first_trade_date=pd.Timestamp(frame["trade_date"].min()).date().isoformat(),
            last_trade_date=pd.Timestamp(frame["trade_date"].max()).date().isoformat(),
        )
        if index % 500 == 0 or index == len(touched):
            print(f"[HT-CN M1 COMPACT] metadata {index}/{len(touched)}", flush=True)

    print(
        f"[HT-CN M1 COMPACT] PASS instruments={instruments}, rows={rows}, "
        f"remaining_delta_files={len(deltas.list_dates())}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
