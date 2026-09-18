from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from htcn.app.sector_context import build_industry_context


def test_sector_context_read_path_does_not_create_tables(tmp_path) -> None:
    catalog = tmp_path / "catalog.duckdb"
    with duckdb.connect(str(catalog)) as con:
        con.execute("CREATE TABLE sentinel(value INTEGER)")
    before = catalog.stat().st_mtime_ns

    result = build_industry_context(
        catalog_path=catalog,
        instrument_id="SSE.688256",
        instrument_frame=pd.DataFrame(),
        as_of=date(2026, 9, 18),
    )

    assert result.status == "membership_unavailable"
    with duckdb.connect(str(catalog), read_only=True) as con:
        tables = {
            row[0]
            for row in con.execute(
                "SELECT table_name FROM information_schema.tables"
            ).fetchall()
        }
    assert tables == {"sentinel"}
    assert catalog.stat().st_mtime_ns == before
