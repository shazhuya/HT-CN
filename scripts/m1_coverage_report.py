from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

from htcn.data.catalog import DataCatalog
from htcn.data.delta import MarketDailyDeltaStore
from htcn.data.universe import SUPPORTED_INITIAL_DAILY_PREFIXES


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "market"
CATALOG_PATH = DATA_ROOT / "catalog.duckdb"
DELTA_ROOT = DATA_ROOT / "daily_delta"
FACTOR_ROOT = DATA_ROOT / "adjustment" / "qfq"


def _date(value):
    return None if value is None else pd.Timestamp(value).date()


def main() -> int:
    if not CATALOG_PATH.exists():
        print("[HT-CN M1 COVERAGE] Database not found.")
        return 1

    catalog = DataCatalog(CATALOG_PATH)
    deltas = MarketDailyDeltaStore(DELTA_ROOT)
    listed = {
        instrument_id
        for instrument_id in catalog.list_security_ids(listed_only=True)
        if instrument_id.startswith(SUPPORTED_INITIAL_DAILY_PREFIXES)
    }
    delta_latest = deltas.latest_dates_by_instrument()
    datasets = [
        row for row in catalog.list_daily_datasets()
        if str(row["instrument_id"]) in listed
    ]

    effective = {}
    for row in datasets:
        instrument_id = str(row["instrument_id"])
        base_last = _date(row.get("last_trade_date"))
        delta_last = delta_latest.get(instrument_id)
        values = [value for value in (base_last, delta_last) if value is not None]
        effective[instrument_id] = max(values) if values else None

    counts = Counter(value for value in effective.values() if value is not None)
    latest = max(counts) if counts else None
    latest_count = counts.get(latest, 0) if latest is not None else 0
    factor_files = len(list(FACTOR_ROOT.glob("*.parquet"))) if FACTOR_ROOT.exists() else 0

    print(f"[HT-CN M1 COVERAGE] SSE+SZSE listed scope : {len(listed)}")
    print(f"[HT-CN M1 COVERAGE] Base datasets          : {len(datasets)}")
    print(f"[HT-CN M1 COVERAGE] Delta files            : {len(deltas.list_dates())}")
    print(f"[HT-CN M1 COVERAGE] QFQ factor files       : {factor_files}")
    print(f"[HT-CN M1 COVERAGE] Latest effective date  : {latest}")
    print(f"[HT-CN M1 COVERAGE] At latest date         : {latest_count}/{len(datasets)}")
    print("[HT-CN M1 COVERAGE] Latest-date distribution:")
    for trade_date, count in sorted(counts.items(), reverse=True)[:10]:
        print(f"  {trade_date}: {count}")
    print("[HT-CN M1 COVERAGE] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
