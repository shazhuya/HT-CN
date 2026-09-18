from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from htcn.app.sector_context import _instrument_return
from htcn.data.concepts import CONCEPT_KIND, CONCEPT_SOURCE


@dataclass(frozen=True, slots=True)
class ConceptEvidence:
    sector_code: str
    sector_name: str
    snapshot_trade_date: str | None
    total_member_count: int | None
    median_return_5d_pct: float | None
    median_return_20d_pct: float | None
    pct_above_ma20: float | None
    up_ratio_1d: float | None
    avg_volume_ratio_20: float | None
    instrument_relative_5d_pct: float | None
    instrument_relative_20d_pct: float | None


@dataclass(frozen=True, slots=True)
class ConceptContext:
    status: str
    mapping_source: str | None
    mapping_observed_on: str | None
    membership_count: int
    resolved_count: int
    concepts: tuple[ConceptEvidence, ...]
    aggregate_method: str = "local_constituent_equal_weight_mean_and_median"
    ordering: str = "sector_median_return_5d_desc"
    mutates_harmonic_identity: bool = False
    mutates_source_raw_prz: bool = False
    owns_lifecycle: bool = False

    def as_payload(self) -> dict[str, object]:
        return {
            "status": self.status,
            "mapping_source": self.mapping_source,
            "mapping_observed_on": self.mapping_observed_on,
            "membership_count": self.membership_count,
            "resolved_count": self.resolved_count,
            "concepts": [asdict(item) for item in self.concepts],
            "aggregate_method": self.aggregate_method,
            "ordering": self.ordering,
            "mutates_harmonic_identity": self.mutates_harmonic_identity,
            "mutates_source_raw_prz": self.mutates_source_raw_prz,
            "owns_lifecycle": self.owns_lifecycle,
        }


def build_concept_context(
    *,
    catalog_path: str | Path,
    instrument_id: str,
    instrument_frame: pd.DataFrame,
    as_of: date | None,
) -> ConceptContext:
    path = Path(catalog_path)
    if not path.exists():
        return ConceptContext("membership_unavailable", None, None, 0, 0, ())

    with duckdb.connect(str(path), read_only=True) as con:
        tables = {
            str(row[0])
            for row in con.execute(
                "SELECT table_name FROM information_schema.tables"
            ).fetchall()
        }
        if "security_sector_membership" not in tables:
            return ConceptContext("membership_unavailable", None, None, 0, 0, ())
        memberships = con.execute("""
            SELECT sector_code, sector_name, source, observed_on
            FROM security_sector_membership
            WHERE instrument_id=? AND sector_kind=? AND source=?
            ORDER BY sector_code
        """, [instrument_id, CONCEPT_KIND, CONCEPT_SOURCE]).fetchall()
        if not memberships:
            return ConceptContext("membership_unavailable", None, None, 0, 0, ())
        latest_observed = max(pd.Timestamp(row[3]).date() for row in memberships)
        if as_of is not None and latest_observed > as_of:
            return ConceptContext(
                "mapping_after_as_of",
                CONCEPT_SOURCE,
                latest_observed.isoformat(),
                len(memberships),
                0,
                (),
            )
        if "sector_snapshot" not in tables:
            observed = max(pd.Timestamp(row[3]).date() for row in memberships).isoformat()
            return ConceptContext(
                "mapped_snapshots_unavailable", CONCEPT_SOURCE, observed,
                len(memberships), 0, ()
            )

        stock5 = _instrument_return(instrument_frame, 5)
        stock20 = _instrument_return(instrument_frame, 20)
        items: list[ConceptEvidence] = []
        for code, name, _source, _observed in memberships:
            row = con.execute("""
                SELECT trade_date, total_member_count,
                       median_return_5d_pct, median_return_20d_pct,
                       pct_above_ma20, up_ratio_1d, avg_volume_ratio_20
                FROM sector_snapshot
                WHERE sector_kind=? AND sector_code=?
                  AND (? IS NULL OR trade_date<=?)
                ORDER BY trade_date DESC LIMIT 1
            """, [CONCEPT_KIND, str(code), as_of, as_of]).fetchone()
            if row is None:
                items.append(ConceptEvidence(
                    str(code), str(name), None, None, None, None,
                    None, None, None, None, None
                ))
                continue
            med5, med20 = row[2], row[3]
            items.append(ConceptEvidence(
                sector_code=str(code),
                sector_name=str(name),
                snapshot_trade_date=pd.Timestamp(row[0]).date().isoformat(),
                total_member_count=int(row[1]),
                median_return_5d_pct=med5,
                median_return_20d_pct=med20,
                pct_above_ma20=row[4],
                up_ratio_1d=row[5],
                avg_volume_ratio_20=row[6],
                instrument_relative_5d_pct=(
                    None if stock5 is None or med5 is None else stock5 - float(med5)
                ),
                instrument_relative_20d_pct=(
                    None if stock20 is None or med20 is None else stock20 - float(med20)
                ),
            ))

    items.sort(
        key=lambda item: (
            item.median_return_5d_pct is not None,
            float(item.median_return_5d_pct or 0.0),
            item.sector_name,
        ),
        reverse=True,
    )
    resolved = sum(item.snapshot_trade_date is not None for item in items)
    status = (
        "resolved" if resolved == len(items)
        else "partial" if resolved
        else "mapped_snapshots_unavailable"
    )
    observed = max(pd.Timestamp(row[3]).date() for row in memberships).isoformat()
    return ConceptContext(
        status=status,
        mapping_source=CONCEPT_SOURCE,
        mapping_observed_on=observed,
        membership_count=len(items),
        resolved_count=resolved,
        concepts=tuple(items),
    )
