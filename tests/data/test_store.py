from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from htcn.data.store import ParquetDailyStore
from htcn.data.validation import DataValidationError, normalize_daily


def sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "instrument_id": "SSE.688256",
                "trade_date": "2026-09-14",
                "open": 100.0,
                "high": 110.0,
                "low": 98.0,
                "close": 108.0,
                "volume": 1000,
                "source": "mock",
            },
            {
                "instrument_id": "SSE.688256",
                "trade_date": "2026-09-15",
                "open": 108.0,
                "high": 112.0,
                "low": 104.0,
                "close": 106.0,
                "volume": 1200,
                "source": "mock",
            },
        ]
    )


def test_upsert_is_idempotent(tmp_path) -> None:
    store = ParquetDailyStore(tmp_path / "daily")
    frame = sample_frame()

    first = store.upsert(frame)
    second = store.upsert(frame)

    assert len(first) == 2
    assert len(second) == 2
    assert store.latest_date("SSE.688256") == date(2026, 9, 15)


def test_read_range(tmp_path) -> None:
    store = ParquetDailyStore(tmp_path / "daily")
    store.upsert(sample_frame())

    result = store.read("SSE.688256", date(2026, 9, 15), date(2026, 9, 15))
    assert len(result) == 1
    assert float(result.iloc[0]["close"]) == 106.0


def test_invalid_ohlc_rejected() -> None:
    frame = sample_frame()
    frame.loc[0, "high"] = 90.0

    with pytest.raises(DataValidationError):
        normalize_daily(frame)
