from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from htcn.data.sectors import INDUSTRY_KIND, INDUSTRY_SOURCE


@dataclass(frozen=True, slots=True)
class SectorCandidate:
    sector_code: str
    sector_name: str


@dataclass(frozen=True, slots=True)
class IndustryContext:
    status: str
    sector_kind: str
    sector_code: str | None
    sector_name: str | None
    mapping_source: str | None
    mapping_observed_on: str | None
    candidate_sectors: tuple[SectorCandidate, ...]
    snapshot_trade_date: str | None
    total_member_count: int | None
    return_1d_count: int | None
    return_5d_count: int | None
    return_20d_count: int | None
    mean_return_1d_pct: float | None
    median_return_1d_pct: float | None
    mean_return_5d_pct: float | None
    median_return_5d_pct: float | None
    mean_return_20d_pct: float | None
    median_return_20d_pct: float | None
    pct_above_ma20: float | None
    up_ratio_1d: float | None
    down_ratio_1d: float | None
    avg_volume_ratio_20: float | None
    instrument_relative_5d_vs_sector_median_pct: float | None
    instrument_relative_20d_vs_sector_median_pct: float | None
    aggregate_method: str = "local_constituent_equal_weight_mean_and_median"
    mutates_harmonic_identity: bool = False
    mutates_source_raw_prz: bool = False
    owns_lifecycle: bool = False

    def as_payload(self) -> dict[str, object]:
        payload = asdict(self)
        payload["candidate_sectors"] = [asdict(item) for item in self.candidate_sectors]
        return payload


def _instrument_return(frame: pd.DataFrame, sessions: int) -> float | None:
    if frame.empty:
        return None
    if "pct_change" in frame.columns:
        values = pd.to_numeric(frame["pct_change"].tail(sessions), errors="coerce")
        if len(values) == sessions and not values.isna().any():
            product = 1.0
            for value in values.tolist():
                product *= 1.0 + max(float(value), -100.0) / 100.0
            return 100.0 * (product - 1.0)
    if "close" not in frame.columns:
        return None
    close = pd.to_numeric(frame["close"], errors="coerce").dropna()
    if len(close) <= sessions:
        return None
    start = float(close.iloc[-sessions - 1])
    return None if start <= 0 else 100.0 * (float(close.iloc[-1]) / start - 1.0)


def _empty(
    status: str,
    *,
    candidates: tuple[SectorCandidate, ...] = (),
    mapping_source: str | None = None,
    mapping_observed_on: str | None = None,
    sector_code: str | None = None,
    sector_name: str | None = None,
) -> IndustryContext:
    return IndustryContext(
        status, INDUSTRY_KIND, sector_code, sector_name, mapping_source,
        mapping_observed_on, candidates, None, None, None, None, None,
        None, None, None, None, None, None, None, None, None, None, None, None
    )


def build_industry_context(
    *,
    catalog_path: str | Path,
    instrument_id: str,
    instrument_frame: pd.DataFrame,
    as_of: date | None,
) -> IndustryContext:
    path = Path(catalog_path)
    if not path.exists():
        return _empty("membership_unavailable")
    with duckdb.connect(str(path), read_only=True) as con:
        table_names = {
            str(row[0])
            for row in con.execute(
                "SELECT table_name FROM information_schema.tables"
            ).fetchall()
        }
        if "security_sector_membership" not in table_names:
            return _empty("membership_unavailable")
        rows = con.execute("""
            SELECT sector_code, sector_name, source, observed_on
            FROM security_sector_membership
            WHERE instrument_id=? AND sector_kind=? AND source=?
            ORDER BY sector_code
        """, [instrument_id, INDUSTRY_KIND, INDUSTRY_SOURCE]).fetchall()
    if not rows:
        return _empty("membership_unavailable")

    candidates = tuple(
        SectorCandidate(str(row[0]), str(row[1])) for row in rows
    )
    source = str(rows[0][2])
    observed_date = pd.Timestamp(rows[0][3]).date()
    observed = observed_date.isoformat()
    if as_of is not None and observed_date > as_of:
        return _empty(
            "mapping_after_as_of",
            candidates=candidates,
            mapping_source=source,
            mapping_observed_on=observed,
        )
    if len({item.sector_code for item in candidates}) != 1:
        return _empty(
            "membership_ambiguous", candidates=candidates,
            mapping_source=source, mapping_observed_on=observed
        )

    code, name = candidates[0].sector_code, candidates[0].sector_name
    with duckdb.connect(str(path), read_only=True) as con:
        table_names = {
            str(item[0])
            for item in con.execute(
                "SELECT table_name FROM information_schema.tables"
            ).fetchall()
        }
        if "sector_snapshot" not in table_names:
            return _empty(
                "mapped_snapshot_unavailable", candidates=candidates,
                mapping_source=source, mapping_observed_on=observed,
                sector_code=code, sector_name=name
            )
        row = con.execute("""
            SELECT * FROM sector_snapshot
            WHERE sector_kind=? AND sector_code=?
              AND (? IS NULL OR trade_date<=?)
            ORDER BY trade_date DESC LIMIT 1
        """, [INDUSTRY_KIND, code, as_of, as_of]).fetchone()
        columns = [item[0] for item in con.description] if row is not None else []
    if row is None:
        return _empty(
            "mapped_snapshot_unavailable", candidates=candidates,
            mapping_source=source, mapping_observed_on=observed,
            sector_code=code, sector_name=name
        )

    data = dict(zip(columns, row, strict=True))
    stock5 = _instrument_return(instrument_frame, 5)
    stock20 = _instrument_return(instrument_frame, 20)
    med5, med20 = data["median_return_5d_pct"], data["median_return_20d_pct"]
    return IndustryContext(
        status="resolved",
        sector_kind=INDUSTRY_KIND,
        sector_code=code,
        sector_name=name,
        mapping_source=source,
        mapping_observed_on=observed,
        candidate_sectors=candidates,
        snapshot_trade_date=pd.Timestamp(data["trade_date"]).date().isoformat(),
        total_member_count=int(data["total_member_count"]),
        return_1d_count=int(data["return_1d_count"]),
        return_5d_count=int(data["return_5d_count"]),
        return_20d_count=int(data["return_20d_count"]),
        mean_return_1d_pct=data["mean_return_1d_pct"],
        median_return_1d_pct=data["median_return_1d_pct"],
        mean_return_5d_pct=data["mean_return_5d_pct"],
        median_return_5d_pct=med5,
        mean_return_20d_pct=data["mean_return_20d_pct"],
        median_return_20d_pct=med20,
        pct_above_ma20=data["pct_above_ma20"],
        up_ratio_1d=data["up_ratio_1d"],
        down_ratio_1d=data["down_ratio_1d"],
        avg_volume_ratio_20=data["avg_volume_ratio_20"],
        instrument_relative_5d_vs_sector_median_pct=(
            None if stock5 is None or med5 is None else stock5 - float(med5)
        ),
        instrument_relative_20d_vs_sector_median_pct=(
            None if stock20 is None or med20 is None else stock20 - float(med20)
        ),
    )
