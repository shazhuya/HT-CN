from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from htcn.data.catalog import DataCatalog
from htcn.data.health import audit_local_daily
from htcn.data.models import Board, Exchange, Security
from htcn.data.store import ParquetDailyStore


def _security() -> Security:
    return Security(
        instrument_id="SSE.688256",
        symbol="688256",
        exchange=Exchange.SSE,
        name="test",
        board=Board.STAR,
        status="listed",
    )


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "instrument_id": "SSE.688256",
                "trade_date": "2026-09-14",
                "open": 100.0,
                "high": 110.0,
                "low": 99.0,
                "close": 108.0,
                "volume": 12345,
                "source": "test",
            }
        ]
    )


def test_health_passes_for_consistent_dataset(tmp_path: Path) -> None:
    catalog = DataCatalog(tmp_path / "catalog.duckdb")
    store = ParquetDailyStore(tmp_path / "daily")
    catalog.upsert_securities([_security()], source="test")
    stored = store.upsert(_frame())
    catalog.record_daily(
        instrument_id="SSE.688256",
        source="test",
        parquet_path=str(store.path_for("SSE.688256")),
        row_count=len(stored),
        first_trade_date=date(2026, 9, 14).isoformat(),
        last_trade_date=date(2026, 9, 14).isoformat(),
    )

    report = audit_local_daily(catalog)
    assert report.passed
    assert report.checked == 1
    assert report.uninitialized == 0


def test_health_detects_missing_parquet(tmp_path: Path) -> None:
    catalog = DataCatalog(tmp_path / "catalog.duckdb")
    catalog.upsert_securities([_security()], source="test")
    catalog.record_daily(
        instrument_id="SSE.688256",
        source="test",
        parquet_path=str(tmp_path / "missing.parquet"),
        row_count=1,
        first_trade_date=date(2026, 9, 14).isoformat(),
        last_trade_date=date(2026, 9, 14).isoformat(),
    )

    report = audit_local_daily(catalog)
    assert not report.passed
    assert len(report.errors) == 1
    assert "missing parquet" in report.errors[0].message
