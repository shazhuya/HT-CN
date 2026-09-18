from __future__ import annotations

from datetime import date, datetime

import duckdb
import pandas as pd
import pytest

from htcn.data.concepts import CONCEPT_KIND, CONCEPT_SOURCE, sync_concept_memberships
from htcn.data.sectors import ensure_sector_schema


class _Provider:
    def list_concept_boards(self):
        return pd.DataFrame([
            {"sector_code": "BK1", "sector_name": "旧概念可更新"},
            {"sector_code": "BK2", "sector_name": "故障概念"},
        ])

    def get_concept_constituents(self, code: str):
        if code == "BK2":
            raise RuntimeError("upstream failed")
        return pd.DataFrame([{"instrument_id": "SSE.688256"}])


def test_failed_concept_refresh_preserves_previous_complete_snapshot(tmp_path) -> None:
    catalog = tmp_path / "catalog.duckdb"
    ensure_sector_schema(catalog)
    old_time = datetime(2026, 9, 10, 8, 0)
    with duckdb.connect(str(catalog)) as con:
        con.execute(
            "INSERT INTO security_sector_membership VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                "SSE.688256", CONCEPT_KIND, "OLD1", "旧完整概念",
                CONCEPT_SOURCE, date(2026, 9, 10), old_time
            ],
        )

    with pytest.raises(RuntimeError, match="previous snapshot preserved"):
        sync_concept_memberships(
            catalog_path=catalog,
            provider=_Provider(),
            observed_on=date(2026, 9, 18),
            workers=2,
            retries=1,
        )

    with duckdb.connect(str(catalog), read_only=True) as con:
        rows = con.execute(
            """
            SELECT sector_code, sector_name
            FROM security_sector_membership
            WHERE sector_kind=? AND source=?
            """,
            [CONCEPT_KIND, CONCEPT_SOURCE],
        ).fetchall()
        audit = con.execute(
            """
            SELECT status FROM sector_membership_sync
            WHERE sector_kind=? AND source=?
            """,
            [CONCEPT_KIND, CONCEPT_SOURCE],
        ).fetchone()

    assert rows == [("OLD1", "旧完整概念")]
    assert audit == ("failed_preserved_previous_snapshot",)
