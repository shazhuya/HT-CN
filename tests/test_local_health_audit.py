from __future__ import annotations

from datetime import date

import pandas as pd

from htcn.data.catalog import DataCatalog
from htcn.data.health import audit_local_daily
from htcn.data.models import Board, Exchange, Security
from htcn.data.store import ParquetDailyStore


def test_health_audit_checks_only_initialized_in_scope_data(tmp_path) -> None:
    catalog = DataCatalog(tmp_path / "catalog.duckdb")
    store = ParquetDailyStore(tmp_path / "daily")

    catalog.upsert_securities(
        [
            Security("SSE.600000", "600000", Exchange.SSE, "A", Board.MAIN),
            Security("SZSE.000001", "000001", Exchange.SZSE, "B", Board.MAIN),
            Security("BSE.920001", "920001", Exchange.BSE, "C", Board.BSE),
        ],
        source="test",
    )

    frame = pd.DataFrame(
        [
            {
                "instrument_id": "SSE.600000",
                "trade_date": "2026-09-14",
                "open": 10.0,
                "high": 11.0,
                "low": 9.5,
                "close": 10.5,
                "volume": 1000,
                "source": "test",
            }
        ]
    )
    stored = store.upsert(frame)
    catalog.record_daily(
        instrument_id="SSE.600000",
        source="test",
        parquet_path=str(store.path_for("SSE.600000")),
        row_count=len(stored),
        first_trade_date=date(2026, 9, 14).isoformat(),
        last_trade_date=date(2026, 9, 14).isoformat(),
    )

    progress: list[tuple[int, int, str]] = []
    report = audit_local_daily(
        catalog,
        progress=lambda done, total, instrument: progress.append((done, total, instrument)),
        progress_every=1,
    )

    assert report.passed
    assert report.checked == 1
    assert report.uninitialized == 1
    assert progress == [(1, 1, "SSE.600000")]
