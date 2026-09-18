from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from scripts.m3_sync_all_contexts import _latest_logical_market_date


def test_logical_market_latest_uses_delta_beyond_base_catalog(tmp_path) -> None:
    root = tmp_path / "market"
    root.mkdir()
    catalog = root / "catalog.duckdb"
    with duckdb.connect(str(catalog)) as con:
        con.execute("CREATE TABLE daily_dataset(last_trade_date DATE)")
        con.execute("INSERT INTO daily_dataset VALUES (DATE '2026-09-16')")
    delta = root / "daily_delta"
    delta.mkdir()
    pd.DataFrame({"x":[1]}).to_parquet(delta / "2026-09-17.parquet", index=False)

    assert _latest_logical_market_date(catalog, root) == date(2026, 9, 17)
