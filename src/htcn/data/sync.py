from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from .catalog import DataCatalog
from .provider import MarketDataProvider
from .store import ParquetDailyStore


def sync_daily(
    *,
    provider: MarketDataProvider,
    store: ParquetDailyStore,
    catalog: DataCatalog,
    instrument_id: str,
    start: date,
    end: date,
) -> pd.DataFrame:
    """Fetch only the missing tail and persist it locally.

    M1 intentionally starts with tail-increment sync. Gap detection and multi-range repair
    are added after the base path is proven on real providers.
    """

    latest = store.latest_date(instrument_id)
    fetch_start = start if latest is None else max(start, latest + timedelta(days=1))

    if fetch_start <= end:
        incoming = provider.get_daily(instrument_id, fetch_start, end)
        if not incoming.empty:
            store.upsert(incoming)

    result = store.read(instrument_id, start, end)
    path = store.path_for(instrument_id)

    first_trade_date = None
    last_trade_date = None
    if not result.empty:
        first_trade_date = pd.Timestamp(result["trade_date"].min()).date().isoformat()
        last_trade_date = pd.Timestamp(result["trade_date"].max()).date().isoformat()

    catalog.record_daily(
        instrument_id=instrument_id,
        source=provider.name,
        parquet_path=str(path),
        row_count=len(result),
        first_trade_date=first_trade_date,
        last_trade_date=last_trade_date,
    )
    return result
