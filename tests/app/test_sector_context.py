from __future__ import annotations

from datetime import date

import pandas as pd

from htcn.app.sector_context import build_industry_context
from htcn.data.sectors import (
    INDUSTRY_KIND,
    INDUSTRY_SOURCE,
    SectorMembershipRecord,
    SectorSnapshotRecord,
    persist_sector_snapshots,
    replace_sector_memberships,
)


def _frame() -> pd.DataFrame:
    dates = pd.bdate_range("2026-08-17", periods=25)
    return pd.DataFrame({
        "trade_date": dates,
        "close": [100 + index for index in range(25)],
        "pct_change": [1.0] * 25,
    })


def test_industry_context_resolves_unique_mapping_and_relative_strength(tmp_path) -> None:
    catalog = tmp_path / "catalog.duckdb"
    replace_sector_memberships(
        catalog,
        records=[SectorMembershipRecord(
            "SSE.688256", INDUSTRY_KIND, "BK1036", "半导体",
            INDUSTRY_SOURCE, date(2026, 9, 18)
        )],
    )
    persist_sector_snapshots(catalog, [SectorSnapshotRecord(
        INDUSTRY_KIND, "BK1036", "半导体", date(2026, 9, 18),
        120, 118, 116, 110,
        0.2, 0.1, 1.1, 1.0, 2.2, 2.0,
        55.0, 48.0, 45.0, 1.15
    )])
    context = build_industry_context(
        catalog_path=catalog,
        instrument_id="SSE.688256",
        instrument_frame=_frame(),
        as_of=date(2026, 9, 18),
    )
    assert context.status == "resolved"
    assert context.sector_name == "半导体"
    assert context.instrument_relative_5d_vs_sector_median_pct is not None
    assert context.instrument_relative_5d_vs_sector_median_pct > 0
    assert context.mutates_harmonic_identity is False
    assert context.mutates_source_raw_prz is False
    assert context.owns_lifecycle is False


def test_industry_context_fails_closed_on_ambiguous_mapping(tmp_path) -> None:
    catalog = tmp_path / "catalog.duckdb"
    replace_sector_memberships(
        catalog,
        records=[
            SectorMembershipRecord(
                "SSE.688256", INDUSTRY_KIND, "BK1", "行业甲",
                INDUSTRY_SOURCE, date(2026, 9, 18)
            ),
            SectorMembershipRecord(
                "SSE.688256", INDUSTRY_KIND, "BK2", "行业乙",
                INDUSTRY_SOURCE, date(2026, 9, 18)
            ),
        ],
    )
    context = build_industry_context(
        catalog_path=catalog,
        instrument_id="SSE.688256",
        instrument_frame=_frame(),
        as_of=date(2026, 9, 18),
    )
    assert context.status == "membership_ambiguous"
    assert {item.sector_name for item in context.candidate_sectors} == {"行业甲", "行业乙"}
