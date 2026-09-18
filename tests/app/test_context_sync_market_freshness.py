from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from scripts.m3_sync_all_contexts import _logical_market_coverage


def test_logical_market_coverage_uses_delta_beyond_base_catalog(tmp_path) -> None:
    root = tmp_path / "market"
    root.mkdir()
    catalog = root / "catalog.duckdb"
    with duckdb.connect(str(catalog)) as con:
        con.execute("CREATE TABLE security_master(instrument_id VARCHAR, status VARCHAR)")
        con.execute("CREATE TABLE daily_dataset(instrument_id VARCHAR, last_trade_date DATE)")
        con.execute("INSERT INTO security_master VALUES ('SSE.688001', 'listed')")
        con.execute("INSERT INTO daily_dataset VALUES ('SSE.688001', DATE '2026-09-16')")

    delta = root / "daily_delta"
    delta.mkdir()
    pd.DataFrame([
        {
            "instrument_id": "SSE.688001",
            "trade_date": pd.Timestamp("2026-09-17"),
        }
    ]).to_parquet(delta / "2026-09-17.parquet", index=False)

    coverage = _logical_market_coverage(catalog, root, date(2026, 9, 17))
    assert coverage["logical_market_latest"] == "2026-09-17"
    assert coverage["current_dataset_count"] == 1
    assert coverage["stale_dataset_count"] == 0
