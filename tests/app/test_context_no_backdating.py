from __future__ import annotations

from datetime import date, datetime

import duckdb
import pandas as pd

from htcn.app.concept_context import build_concept_context
from htcn.app.sector_context import build_industry_context
from htcn.data.concepts import CONCEPT_KIND, CONCEPT_SOURCE
from htcn.data.sectors import INDUSTRY_KIND, INDUSTRY_SOURCE, ensure_sector_schema


def _insert(catalog, *, kind: str, source: str, code: str, name: str) -> None:
    ensure_sector_schema(catalog)
    with duckdb.connect(str(catalog)) as con:
        con.execute(
            "INSERT INTO security_sector_membership VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                "SSE.688256", kind, code, name, source,
                date(2026, 9, 18), datetime(2026, 9, 18, 8, 0)
            ],
        )


def test_industry_mapping_is_not_backdated_before_observation(tmp_path) -> None:
    catalog = tmp_path / "catalog.duckdb"
    _insert(
        catalog, kind=INDUSTRY_KIND, source=INDUSTRY_SOURCE,
        code="BK1", name="半导体"
    )
    result = build_industry_context(
        catalog_path=catalog,
        instrument_id="SSE.688256",
        instrument_frame=pd.DataFrame(),
        as_of=date(2026, 9, 17),
    )
    assert result.status == "mapping_after_as_of"
    assert result.mapping_observed_on == "2026-09-18"


def test_concept_mapping_is_not_backdated_before_observation(tmp_path) -> None:
    catalog = tmp_path / "catalog.duckdb"
    _insert(
        catalog, kind=CONCEPT_KIND, source=CONCEPT_SOURCE,
        code="BK2", name="AI算力"
    )
    result = build_concept_context(
        catalog_path=catalog,
        instrument_id="SSE.688256",
        instrument_frame=pd.DataFrame(),
        as_of=date(2026, 9, 17),
    )
    assert result.status == "mapping_after_as_of"
    assert result.mapping_observed_on == "2026-09-18"
    assert result.resolved_count == 0
