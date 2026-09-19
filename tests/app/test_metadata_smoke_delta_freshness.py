from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from scripts.m3_metadata_tradability_smoke import run


def test_metadata_smoke_reads_latest_daily_delta_not_only_base_parquet(tmp_path) -> None:
    root = tmp_path / "market"
    daily = root / "daily"
    delta = root / "daily_delta"
    daily.mkdir(parents=True)
    delta.mkdir(parents=True)
    catalog = root / "catalog.duckdb"

    with duckdb.connect(str(catalog)) as con:
        con.execute("""
            CREATE TABLE security_master (
                instrument_id VARCHAR, symbol VARCHAR, exchange VARCHAR, name VARCHAR,
                board VARCHAR, list_date DATE, delist_date DATE, is_st BOOLEAN,
                status VARCHAR, source VARCHAR, updated_at TIMESTAMP
            )
        """)
        con.execute("""
            CREATE TABLE daily_dataset (
                instrument_id VARCHAR, source VARCHAR, parquet_path VARCHAR,
                row_count BIGINT, first_trade_date DATE, last_trade_date DATE,
                updated_at TIMESTAMP
            )
        """)
        con.executemany(
            "INSERT INTO security_master VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, now())",
            [
                ["SSE.600000","600000","SSE","浦发银行","MAIN",date(1999,11,10),None,False,"listed","test"],
                ["SSE.688001","688001","SSE","华兴源创","STAR",date(2019,7,22),None,False,"listed","test"],
                ["SZSE.300001","300001","SZSE","特锐德","CHINEXT",date(2009,10,30),None,False,"listed","test"],
            ],
        )

    rows = []
    for instrument_id in ("SSE.600000","SSE.688001","SZSE.300001"):
        base = pd.DataFrame([
            {
                "instrument_id": instrument_id,
                "trade_date": pd.Timestamp("2026-09-16"),
                "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2,
                "volume": 1000.0, "source": "test",
            }
        ])
        path = daily / f"{instrument_id}.parquet"
        base.to_parquet(path, index=False)
        rows.append([instrument_id,"test",str(path),1,date(2026,9,16),date(2026,9,16)])
    with duckdb.connect(str(catalog)) as con:
        con.executemany(
            "INSERT INTO daily_dataset VALUES (?, ?, ?, ?, ?, ?, now())",
            rows,
        )

    pd.DataFrame([
        {
            "instrument_id": instrument_id,
            "trade_date": pd.Timestamp("2026-09-17"),
            "open": 10.2, "high": 10.7, "low": 10.0, "close": 10.4,
            "volume": 1200.0, "source": "delta",
        }
        for instrument_id in ("SSE.600000","SSE.688001","SZSE.300001")
    ]).to_parquet(delta / "2026-09-17.parquet", index=False)

    result = run(catalog)
    assert result["status"] == "pass"
    assert all(item["logical_last_trade_date"] == "2026-09-17" for item in result["samples"])
