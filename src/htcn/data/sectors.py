from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

INDUSTRY_KIND = "industry"
INDUSTRY_SOURCE = "akshare_eastmoney_industry"
LOCAL_AGGREGATE_SOURCE = "local_constituent_aggregate_v1"


@dataclass(frozen=True, slots=True)
class SectorMembershipRecord:
    instrument_id: str
    sector_kind: str
    sector_code: str
    sector_name: str
    source: str
    observed_on: date


@dataclass(frozen=True, slots=True)
class SectorSnapshotRecord:
    sector_kind: str
    sector_code: str
    sector_name: str
    trade_date: date
    total_member_count: int
    return_1d_count: int
    return_5d_count: int
    return_20d_count: int
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
    source: str = LOCAL_AGGREGATE_SOURCE


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def ensure_sector_schema(catalog_path: str | Path) -> None:
    path = Path(catalog_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(path)) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS security_sector_membership (
                instrument_id VARCHAR NOT NULL,
                sector_kind VARCHAR NOT NULL,
                sector_code VARCHAR NOT NULL,
                sector_name VARCHAR NOT NULL,
                source VARCHAR NOT NULL,
                observed_on DATE NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                PRIMARY KEY (instrument_id, sector_kind, sector_code, source)
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS sector_membership_sync (
                sector_kind VARCHAR NOT NULL,
                source VARCHAR NOT NULL,
                observed_on DATE NOT NULL,
                status VARCHAR NOT NULL,
                sector_count INTEGER NOT NULL,
                membership_count INTEGER NOT NULL,
                ambiguous_security_count INTEGER NOT NULL,
                error_message VARCHAR,
                updated_at TIMESTAMP NOT NULL,
                PRIMARY KEY (sector_kind, source)
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS sector_snapshot (
                sector_kind VARCHAR NOT NULL,
                sector_code VARCHAR NOT NULL,
                sector_name VARCHAR NOT NULL,
                trade_date DATE NOT NULL,
                total_member_count INTEGER NOT NULL,
                return_1d_count INTEGER NOT NULL,
                return_5d_count INTEGER NOT NULL,
                return_20d_count INTEGER NOT NULL,
                mean_return_1d_pct DOUBLE,
                median_return_1d_pct DOUBLE,
                mean_return_5d_pct DOUBLE,
                median_return_5d_pct DOUBLE,
                mean_return_20d_pct DOUBLE,
                median_return_20d_pct DOUBLE,
                pct_above_ma20 DOUBLE,
                up_ratio_1d DOUBLE,
                down_ratio_1d DOUBLE,
                avg_volume_ratio_20 DOUBLE,
                source VARCHAR NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                PRIMARY KEY (sector_kind, sector_code, trade_date)
            )
        """)


def _ambiguous_count(records: list[SectorMembershipRecord]) -> int:
    if not records:
        return 0
    frame = pd.DataFrame(
        [(item.instrument_id, item.sector_code) for item in records],
        columns=["instrument_id", "sector_code"],
    ).drop_duplicates()
    counts = frame.groupby("instrument_id")["sector_code"].nunique()
    return int((counts > 1).sum())


def _record_sync(
    catalog_path: str | Path,
    *,
    observed_on: date,
    status: str,
    sector_count: int,
    membership_count: int,
    ambiguous_security_count: int,
    error_message: str | None,
) -> None:
    ensure_sector_schema(catalog_path)
    with duckdb.connect(str(catalog_path)) as con:
        con.execute("""
            INSERT INTO sector_membership_sync VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sector_kind, source) DO UPDATE SET
                observed_on=excluded.observed_on,
                status=excluded.status,
                sector_count=excluded.sector_count,
                membership_count=excluded.membership_count,
                ambiguous_security_count=excluded.ambiguous_security_count,
                error_message=excluded.error_message,
                updated_at=excluded.updated_at
        """, [
            INDUSTRY_KIND, INDUSTRY_SOURCE, observed_on, status, sector_count,
            membership_count, ambiguous_security_count, error_message, _now()
        ])


def replace_sector_memberships(
    catalog_path: str | Path,
    *,
    records: list[SectorMembershipRecord],
) -> int:
    if not records:
        raise ValueError("refuse to replace sector membership with empty snapshot")
    ensure_sector_schema(catalog_path)
    now = _now()
    rows = [[
        item.instrument_id, item.sector_kind, item.sector_code, item.sector_name,
        item.source, item.observed_on, now
    ] for item in records]
    with duckdb.connect(str(catalog_path)) as con:
        con.execute("BEGIN TRANSACTION")
        try:
            con.execute(
                "DELETE FROM security_sector_membership WHERE sector_kind=? AND source=?",
                [INDUSTRY_KIND, INDUSTRY_SOURCE],
            )
            con.executemany(
                "INSERT INTO security_sector_membership VALUES (?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
    return len(rows)


def sync_industry_memberships(
    *,
    catalog_path: str | Path,
    provider: Any,
    observed_on: date,
) -> dict[str, int | str]:
    """All-or-nothing Eastmoney industry membership refresh."""
    boards = provider.list_industry_boards()
    if boards is None or boards.empty:
        _record_sync(
            catalog_path, observed_on=observed_on, status="failed_preserved_previous_snapshot",
            sector_count=0, membership_count=0, ambiguous_security_count=0,
            error_message="industry board list empty",
        )
        raise RuntimeError("industry board list empty")

    records: list[SectorMembershipRecord] = []
    failures: list[str] = []
    for row in boards[["sector_code", "sector_name"]].drop_duplicates().itertuples(index=False):
        code, name = str(row.sector_code), str(row.sector_name)
        try:
            members = provider.get_industry_constituents(code)
        except Exception as exc:
            failures.append(f"{code}:{type(exc).__name__}:{exc}")
            continue
        if members is None or members.empty:
            failures.append(f"{code}:empty_constituents")
            continue
        for member in members["instrument_id"].drop_duplicates().tolist():
            instrument_id = str(member)
            if instrument_id.startswith(("SSE.", "SZSE.")):
                records.append(
                    SectorMembershipRecord(
                        instrument_id, INDUSTRY_KIND, code, name,
                        INDUSTRY_SOURCE, observed_on
                    )
                )

    deduped = list({
        (item.instrument_id, item.sector_code): item for item in records
    }.values())
    ambiguous = _ambiguous_count(deduped)
    if failures:
        message = "; ".join(failures[:12])
        _record_sync(
            catalog_path, observed_on=observed_on,
            status="failed_preserved_previous_snapshot",
            sector_count=int(boards["sector_code"].nunique()),
            membership_count=len(deduped),
            ambiguous_security_count=ambiguous,
            error_message=message,
        )
        raise RuntimeError(
            f"industry refresh incomplete; previous snapshot preserved: {message}"
        )

    count = replace_sector_memberships(catalog_path, records=deduped)
    _record_sync(
        catalog_path, observed_on=observed_on, status="success",
        sector_count=int(boards["sector_code"].nunique()),
        membership_count=count, ambiguous_security_count=ambiguous,
        error_message=None,
    )
    return {
        "status": "success",
        "sector_count": int(boards["sector_code"].nunique()),
        "membership_count": count,
        "ambiguous_security_count": ambiguous,
    }


def membership_sync_is_fresh(
    catalog_path: str | Path,
    *,
    as_of: date,
    max_age_days: int,
) -> bool:
    ensure_sector_schema(catalog_path)
    with duckdb.connect(str(catalog_path), read_only=True) as con:
        row = con.execute("""
            SELECT observed_on, status FROM sector_membership_sync
            WHERE sector_kind=? AND source=?
        """, [INDUSTRY_KIND, INDUSTRY_SOURCE]).fetchone()
    if row is None or str(row[1]) != "success":
        return False
    observed = pd.Timestamp(row[0]).date()
    return 0 <= (as_of - observed).days <= max_age_days


def _read_local_market_window(
    data_root: str | Path,
    *,
    start: date,
    end: date,
) -> pd.DataFrame:
    root = Path(data_root)
    parts: list[str] = []
    with duckdb.connect() as con:
        for directory, priority in ((root / "daily", 0), (root / "daily_delta", 1)):
            if not directory.exists() or not any(directory.glob("*.parquet")):
                continue
            glob = (directory / "*.parquet").as_posix().replace("'", "''")
            schema = {
                str(row[0])
                for row in con.execute(
                    f"DESCRIBE SELECT * FROM read_parquet('{glob}', union_by_name=true)"
                ).fetchall()
            }
            pct_expr = (
                "pct_change"
                if "pct_change" in schema
                else "CAST(NULL AS DOUBLE) AS pct_change"
            )
            parts.append(f"""
                SELECT instrument_id, CAST(trade_date AS DATE) AS trade_date,
                       close, volume, {pct_expr}, {priority} AS source_priority
                FROM read_parquet('{glob}', union_by_name=true)
                WHERE CAST(trade_date AS DATE) BETWEEN DATE '{start.isoformat()}'
                                                   AND DATE '{end.isoformat()}'
            """)
        if not parts:
            return pd.DataFrame()
        frame = con.execute(" UNION ALL ".join(parts)).df()
    if frame.empty:
        return frame
    frame["trade_date"] = pd.to_datetime(frame["trade_date"]).dt.normalize()
    return (
        frame.sort_values(["instrument_id", "trade_date", "source_priority"])
        .drop_duplicates(["instrument_id", "trade_date"], keep="last")
        .drop(columns=["source_priority"])
        .reset_index(drop=True)
    )

def _compound(values: list[float]) -> float:
    product = 1.0
    for value in values:
        product *= 1.0 + max(float(value), -100.0) / 100.0
    return 100.0 * (product - 1.0)


def _metrics(
    bars: pd.DataFrame,
    *,
    trade_days: list[pd.Timestamp],
    list_date: date | None,
) -> dict[str, float | None]:
    by_date = (
        bars.sort_values("trade_date").drop_duplicates("trade_date", keep="last")
        .set_index("trade_date") if not bars.empty else pd.DataFrame()
    )

    closes = pd.Series(index=pd.DatetimeIndex(trade_days), dtype=float)
    volumes = pd.Series(index=pd.DatetimeIndex(trade_days), dtype=float)
    if isinstance(by_date, pd.DataFrame) and not by_date.empty:
        for day, row in by_date.iterrows():
            if day in closes.index:
                closes.loc[day] = pd.to_numeric(
                    pd.Series([row.get("close")]), errors="coerce"
                ).iloc[0]
                volumes.loc[day] = pd.to_numeric(
                    pd.Series([row.get("volume")]), errors="coerce"
                ).iloc[0]
    closes = closes.ffill()

    def horizon(sessions: int) -> float | None:
        window = trade_days[-sessions:]
        if len(window) < sessions:
            return None
        if list_date is not None and list_date > window[0].date():
            return None

        pct_values: list[float] = []
        pct_complete_for_observed_bars = True
        for day in window:
            if isinstance(by_date, pd.DataFrame) and not by_date.empty and day in by_date.index:
                value = by_date.loc[day, "pct_change"] if "pct_change" in by_date.columns else None
                if isinstance(value, pd.Series):
                    value = value.iloc[-1]
                numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
                if pd.isna(numeric):
                    pct_complete_for_observed_bars = False
                    break
                pct_values.append(float(numeric))
            else:
                # A listed constituent with no bar on a market session is treated as
                # unchanged for that session (for example a full-day suspension).
                pct_values.append(0.0)
        if pct_complete_for_observed_bars:
            return _compound(pct_values)

        # Some old/failover parquet sets do not carry pct_change. Fall back to a
        # transparent local close-to-close return rather than inventing zero returns.
        if len(trade_days) <= sessions:
            return None
        start_day = trade_days[-sessions - 1]
        end_day = trade_days[-1]
        if list_date is not None and list_date > start_day.date():
            return None
        start_close = closes.loc[start_day]
        end_close = closes.loc[end_day]
        if pd.isna(start_close) or pd.isna(end_close) or float(start_close) <= 0:
            return None
        return 100.0 * (float(end_close) / float(start_close) - 1.0)

    above = None
    last20 = closes.iloc[-20:]
    if len(last20) == 20 and not last20.isna().any():
        above = 1.0 if float(last20.iloc[-1]) > float(last20.mean()) else 0.0

    volume_ratio = None
    if len(volumes) >= 21:
        avg = float(volumes.iloc[-21:-1].fillna(0.0).mean())
        latest = 0.0 if pd.isna(volumes.iloc[-1]) else float(volumes.iloc[-1])
        if avg > 0:
            volume_ratio = latest / avg
    return {
        "return_1d": horizon(1),
        "return_5d": horizon(5),
        "return_20d": horizon(20),
        "above_ma20": above,
        "volume_ratio_20": volume_ratio,
    }

def _avg(values: list[float]) -> float | None:
    return None if not values else float(pd.Series(values, dtype=float).mean())


def _median(values: list[float]) -> float | None:
    return None if not values else float(pd.Series(values, dtype=float).median())


def persist_sector_snapshots(
    catalog_path: str | Path,
    snapshots: list[SectorSnapshotRecord],
) -> int:
    if not snapshots:
        return 0
    ensure_sector_schema(catalog_path)
    now = _now()
    rows = [[
        item.sector_kind, item.sector_code, item.sector_name, item.trade_date,
        item.total_member_count, item.return_1d_count, item.return_5d_count,
        item.return_20d_count, item.mean_return_1d_pct, item.median_return_1d_pct,
        item.mean_return_5d_pct, item.median_return_5d_pct,
        item.mean_return_20d_pct, item.median_return_20d_pct,
        item.pct_above_ma20, item.up_ratio_1d, item.down_ratio_1d,
        item.avg_volume_ratio_20, item.source, now
    ] for item in snapshots]
    with duckdb.connect(str(catalog_path)) as con:
        con.executemany("""
            INSERT INTO sector_snapshot VALUES (
                ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
            )
            ON CONFLICT(sector_kind, sector_code, trade_date) DO UPDATE SET
                sector_name=excluded.sector_name,
                total_member_count=excluded.total_member_count,
                return_1d_count=excluded.return_1d_count,
                return_5d_count=excluded.return_5d_count,
                return_20d_count=excluded.return_20d_count,
                mean_return_1d_pct=excluded.mean_return_1d_pct,
                median_return_1d_pct=excluded.median_return_1d_pct,
                mean_return_5d_pct=excluded.mean_return_5d_pct,
                median_return_5d_pct=excluded.median_return_5d_pct,
                mean_return_20d_pct=excluded.mean_return_20d_pct,
                median_return_20d_pct=excluded.median_return_20d_pct,
                pct_above_ma20=excluded.pct_above_ma20,
                up_ratio_1d=excluded.up_ratio_1d,
                down_ratio_1d=excluded.down_ratio_1d,
                avg_volume_ratio_20=excluded.avg_volume_ratio_20,
                source=excluded.source,
                updated_at=excluded.updated_at
        """, rows)
    return len(rows)


def build_industry_snapshot_from_local_market(
    *,
    catalog_path: str | Path,
    data_root: str | Path,
    target_date: date | None = None,
) -> list[SectorSnapshotRecord]:
    ensure_sector_schema(catalog_path)
    with duckdb.connect(str(catalog_path), read_only=True) as con:
        calendar_rows = con.execute("""
            SELECT trade_date FROM trade_calendar
            WHERE (? IS NULL OR trade_date <= ?)
            ORDER BY trade_date DESC LIMIT 25
        """, [target_date, target_date]).fetchall()
        memberships = con.execute("""
            SELECT m.instrument_id, m.sector_code, m.sector_name,
                   s.list_date, s.delist_date
            FROM security_sector_membership m
            LEFT JOIN security_master s ON s.instrument_id=m.instrument_id
            WHERE m.sector_kind=? AND m.source=?
            ORDER BY m.sector_code, m.instrument_id
        """, [INDUSTRY_KIND, INDUSTRY_SOURCE]).df()
    if not calendar_rows:
        raise RuntimeError("trade_calendar has no usable dates")
    if memberships.empty:
        raise RuntimeError("industry membership unavailable")

    trade_days = sorted(pd.Timestamp(row[0]).normalize() for row in calendar_rows)
    target = trade_days[-1].date()
    market = _read_local_market_window(
        data_root, start=trade_days[0].date(), end=target
    )
    if market.empty:
        raise RuntimeError("local market bars unavailable for sector aggregation")
    groups = {
        key: group.reset_index(drop=True)
        for key, group in market.groupby("instrument_id", sort=False)
    }

    snapshots: list[SectorSnapshotRecord] = []
    for (code, name), sector in memberships.groupby(["sector_code", "sector_name"], sort=True):
        r1: list[float] = []
        r5: list[float] = []
        r20: list[float] = []
        above: list[float] = []
        volume: list[float] = []
        active = 0
        for row in sector.itertuples(index=False):
            list_date = None if pd.isna(row.list_date) else pd.Timestamp(row.list_date).date()
            delist_date = None if pd.isna(row.delist_date) else pd.Timestamp(row.delist_date).date()
            if list_date is not None and list_date > target:
                continue
            if delist_date is not None and delist_date < target:
                continue
            active += 1
            item = _metrics(
                groups.get(str(row.instrument_id), pd.DataFrame()),
                trade_days=trade_days, list_date=list_date
            )
            if item["return_1d"] is not None: r1.append(float(item["return_1d"]))
            if item["return_5d"] is not None: r5.append(float(item["return_5d"]))
            if item["return_20d"] is not None: r20.append(float(item["return_20d"]))
            if item["above_ma20"] is not None: above.append(float(item["above_ma20"]))
            if item["volume_ratio_20"] is not None: volume.append(float(item["volume_ratio_20"]))

        snapshots.append(SectorSnapshotRecord(
            sector_kind=INDUSTRY_KIND,
            sector_code=str(code),
            sector_name=str(name),
            trade_date=target,
            total_member_count=active,
            return_1d_count=len(r1),
            return_5d_count=len(r5),
            return_20d_count=len(r20),
            mean_return_1d_pct=_avg(r1),
            median_return_1d_pct=_median(r1),
            mean_return_5d_pct=_avg(r5),
            median_return_5d_pct=_median(r5),
            mean_return_20d_pct=_avg(r20),
            median_return_20d_pct=_median(r20),
            pct_above_ma20=None if not above else 100.0 * sum(above) / len(above),
            up_ratio_1d=None if not r1 else 100.0 * sum(x > 0 for x in r1) / len(r1),
            down_ratio_1d=None if not r1 else 100.0 * sum(x < 0 for x in r1) / len(r1),
            avg_volume_ratio_20=_avg(volume),
        ))
    persist_sector_snapshots(catalog_path, snapshots)
    return snapshots
