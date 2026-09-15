from datetime import date

import pandas as pd

from htcn.data.delta import DailyHistoryView, MarketDailyDeltaStore, compact_daily_deltas
from htcn.data.store import ParquetDailyStore


def _rows(day: date, close: float) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "instrument_id": "SSE.600000",
                "trade_date": day,
                "open": close - 0.2,
                "high": close + 0.4,
                "low": close - 0.5,
                "close": close,
                "volume": 1_000_000.0,
                "source": "test",
            }
        ]
    )


def test_daily_delta_overlay_and_compaction(tmp_path) -> None:
    base = ParquetDailyStore(tmp_path / "base")
    deltas = MarketDailyDeltaStore(tmp_path / "delta")
    base.upsert(_rows(date(2026, 9, 14), 10.0))
    deltas.write(_rows(date(2026, 9, 15), 10.5), trade_date=date(2026, 9, 15))

    view = DailyHistoryView(base, deltas)
    merged = view.read("SSE.600000")
    assert merged["trade_date"].dt.date.tolist() == [date(2026, 9, 14), date(2026, 9, 15)]
    assert merged["close"].tolist() == [10.0, 10.5]
    assert deltas.latest_dates_by_instrument()["SSE.600000"] == date(2026, 9, 15)

    instruments, rows = compact_daily_deltas(base=base, deltas=deltas)
    assert (instruments, rows) == (1, 1)
    assert deltas.list_dates() == []
    compacted = base.read("SSE.600000")
    assert compacted["close"].tolist() == [10.0, 10.5]
