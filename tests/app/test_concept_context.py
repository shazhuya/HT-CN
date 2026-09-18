from __future__ import annotations

from datetime import date, datetime

import duckdb
import pandas as pd

from htcn.app.concept_context import build_concept_context
from htcn.data.concepts import CONCEPT_KIND, CONCEPT_SOURCE
from htcn.data.sectors import SectorSnapshotRecord, ensure_sector_schema, persist_sector_snapshots


def _frame() -> pd.DataFrame:
    dates = pd.bdate_range("2026-08-17", periods=25)
    return pd.DataFrame({
        "trade_date": dates,
        "close": [100 + index for index in range(25)],
        "pct_change": [1.0] * 25,
    })


def _insert_memberships(catalog, rows) -> None:
    ensure_sector_schema(catalog)
    with duckdb.connect(str(catalog)) as con:
        con.executemany(
            "INSERT INTO security_sector_membership VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )


def test_multi_concept_membership_is_normal_and_sorted_by_transparent_5d_return(tmp_path) -> None:
    catalog = tmp_path / "catalog.duckdb"
    now = datetime(2026, 9, 18, 8, 0)
    _insert_memberships(catalog, [
        ["SSE.688256", CONCEPT_KIND, "BK1", "国产芯片", CONCEPT_SOURCE, date(2026, 9, 18), now],
        ["SSE.688256", CONCEPT_KIND, "BK2", "AI算力", CONCEPT_SOURCE, date(2026, 9, 18), now],
    ])
    persist_sector_snapshots(catalog, [
        SectorSnapshotRecord(
            CONCEPT_KIND, "BK1", "国产芯片", date(2026, 9, 18),
            80, 80, 80, 78, .1, .1, 1.0, .8, 2.0, 1.5, 55, 52, 42, 1.1
        ),
        SectorSnapshotRecord(
            CONCEPT_KIND, "BK2", "AI算力", date(2026, 9, 18),
            60, 60, 60, 58, .2, .2, 2.5, 2.2, 3.0, 2.8, 62, 58, 35, 1.3
        ),
    ])

    context = build_concept_context(
        catalog_path=catalog,
        instrument_id="SSE.688256",
        instrument_frame=_frame(),
        as_of=date(2026, 9, 18),
    )
    assert context.status == "resolved"
    assert context.membership_count == 2
    assert [item.sector_name for item in context.concepts] == ["AI算力", "国产芯片"]
    assert context.owns_lifecycle is False
    assert context.mutates_harmonic_identity is False


def test_concept_context_is_partial_when_one_snapshot_is_missing(tmp_path) -> None:
    catalog = tmp_path / "catalog.duckdb"
    now = datetime(2026, 9, 18, 8, 0)
    _insert_memberships(catalog, [
        ["SSE.688256", CONCEPT_KIND, "BK1", "国产芯片", CONCEPT_SOURCE, date(2026, 9, 18), now],
        ["SSE.688256", CONCEPT_KIND, "BK2", "AI算力", CONCEPT_SOURCE, date(2026, 9, 18), now],
    ])
    persist_sector_snapshots(catalog, [
        SectorSnapshotRecord(
            CONCEPT_KIND, "BK1", "国产芯片", date(2026, 9, 18),
            80, 80, 80, 78, .1, .1, 1.0, .8, 2.0, 1.5, 55, 52, 42, 1.1
        ),
    ])
    context = build_concept_context(
        catalog_path=catalog,
        instrument_id="SSE.688256",
        instrument_frame=_frame(),
        as_of=date(2026, 9, 18),
    )
    assert context.status == "partial"
    assert context.resolved_count == 1
    assert context.membership_count == 2
