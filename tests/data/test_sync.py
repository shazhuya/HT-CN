from __future__ import annotations

from datetime import date

import pandas as pd

from htcn.data.catalog import DataCatalog
from htcn.data.store import ParquetDailyStore
from htcn.data.sync import sync_daily


class MockProvider:
    name = "mock"

    def __init__(self) -> None:
        self.calls: list[tuple[date, date]] = []

    def list_securities(self):
        return []

    def get_trade_calendar(self, start: date, end: date):
        return []

    def get_daily(self, instrument_id: str, start: date, end: date) -> pd.DataFrame:
        self.calls.append((start, end))
        rows = []
        for day, close in [
            (date(2026, 9, 14), 108.0),
            (date(2026, 9, 15), 106.0),
            (date(2026, 9, 16), 109.0),
        ]:
            if start <= day <= end:
                rows.append(
                    {
                        "instrument_id": instrument_id,
                        "trade_date": day.isoformat(),
                        "open": close - 1,
                        "high": close + 2,
                        "low": close - 3,
                        "close": close,
                        "volume": 1000,
                        "source": self.name,
                    }
                )
        return pd.DataFrame(rows)


def test_sync_only_fetches_missing_tail(tmp_path) -> None:
    provider = MockProvider()
    store = ParquetDailyStore(tmp_path / "daily")
    catalog = DataCatalog(tmp_path / "catalog.duckdb")

    first = sync_daily(
        provider=provider,
        store=store,
        catalog=catalog,
        instrument_id="SSE.688256",
        start=date(2026, 9, 14),
        end=date(2026, 9, 15),
    )
    second = sync_daily(
        provider=provider,
        store=store,
        catalog=catalog,
        instrument_id="SSE.688256",
        start=date(2026, 9, 14),
        end=date(2026, 9, 16),
    )

    assert len(first) == 2
    assert len(second) == 3
    assert provider.calls == [
        (date(2026, 9, 14), date(2026, 9, 15)),
        (date(2026, 9, 16), date(2026, 9, 16)),
    ]

    meta = catalog.get_daily("SSE.688256")
    assert meta is not None
    assert meta["source"] == "mock"
    assert meta["row_count"] == 3
