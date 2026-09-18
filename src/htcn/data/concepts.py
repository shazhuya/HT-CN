from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
import time
from typing import Any

import duckdb
import pandas as pd

from htcn.data.sectors import (
    SectorMembershipRecord,
    SectorSnapshotRecord,
    _avg,
    _median,
    _metrics,
    _read_local_market_window,
    ensure_sector_schema,
    persist_sector_snapshots,
)


CONCEPT_KIND = "concept"
CONCEPT_SOURCE = "akshare_eastmoney_concept"


def _record_sync(
    catalog_path: str | Path,
    *,
    observed_on: date,
    status: str,
    sector_count: int,
    membership_count: int,
    error_message: str | None,
) -> None:
    ensure_sector_schema(catalog_path)
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).replace(tzinfo=None)
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
            CONCEPT_KIND, CONCEPT_SOURCE, observed_on, status,
            sector_count, membership_count, 0, error_message, now
        ])


def concept_sync_is_fresh(
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
        """, [CONCEPT_KIND, CONCEPT_SOURCE]).fetchone()
    if row is None or str(row[1]) != "success":
        return False
    observed = pd.Timestamp(row[0]).date()
    return 0 <= (as_of - observed).days <= max_age_days


def _replace_concepts(
    catalog_path: str | Path,
    records: list[SectorMembershipRecord],
) -> int:
    if not records:
        raise ValueError("refuse to replace concept membership with empty snapshot")
    ensure_sector_schema(catalog_path)
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    rows = [[
        item.instrument_id, item.sector_kind, item.sector_code, item.sector_name,
        item.source, item.observed_on, now
    ] for item in records]
    with duckdb.connect(str(catalog_path)) as con:
        con.execute("BEGIN TRANSACTION")
        try:
            con.execute(
                "DELETE FROM security_sector_membership WHERE sector_kind=? AND source=?",
                [CONCEPT_KIND, CONCEPT_SOURCE],
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


def sync_concept_memberships(
    *,
    catalog_path: str | Path,
    provider: Any,
    observed_on: date,
    workers: int = 8,
    retries: int = 2,
) -> dict[str, int | str]:
    """Fetch all concept memberships concurrently, then replace atomically."""
    boards = provider.list_concept_boards()
    if boards is None or boards.empty:
        _record_sync(
            catalog_path, observed_on=observed_on,
            status="failed_preserved_previous_snapshot",
            sector_count=0, membership_count=0,
            error_message="concept board list empty",
        )
        raise RuntimeError("concept board list empty")

    board_rows = list(
        boards[["sector_code", "sector_name"]]
        .drop_duplicates()
        .itertuples(index=False)
    )

    def fetch_one(code: str):
        last_error: Exception | None = None
        for attempt in range(max(retries, 1)):
            try:
                frame = provider.get_concept_constituents(code)
                if frame is None or frame.empty:
                    raise RuntimeError("empty_constituents")
                return frame
            except Exception as exc:
                last_error = exc
                if attempt + 1 < max(retries, 1):
                    time.sleep(0.15 * (attempt + 1))
        assert last_error is not None
        raise last_error

    results: dict[str, pd.DataFrame] = {}
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=max(1, min(workers, 16))) as pool:
        futures = {
            pool.submit(fetch_one, str(row.sector_code)): (
                str(row.sector_code), str(row.sector_name)
            )
            for row in board_rows
        }
        for future in as_completed(futures):
            code, _name = futures[future]
            try:
                results[code] = future.result()
            except Exception as exc:
                failures.append(f"{code}:{type(exc).__name__}:{exc}")

    records: list[SectorMembershipRecord] = []
    for row in board_rows:
        code, name = str(row.sector_code), str(row.sector_name)
        members = results.get(code)
        if members is None:
            continue
        for instrument_id in members["instrument_id"].drop_duplicates().tolist():
            instrument_id = str(instrument_id)
            if instrument_id.startswith(("SSE.", "SZSE.")):
                records.append(
                    SectorMembershipRecord(
                        instrument_id, CONCEPT_KIND, code, name,
                        CONCEPT_SOURCE, observed_on
                    )
                )

    deduped = list({
        (item.instrument_id, item.sector_code): item for item in records
    }.values())
    if failures:
        message = "; ".join(sorted(failures)[:12])
        _record_sync(
            catalog_path, observed_on=observed_on,
            status="failed_preserved_previous_snapshot",
            sector_count=len(board_rows), membership_count=len(deduped),
            error_message=message,
        )
        raise RuntimeError(
            f"concept refresh incomplete; previous snapshot preserved: {message}"
        )

    count = _replace_concepts(catalog_path, deduped)
    _record_sync(
        catalog_path, observed_on=observed_on, status="success",
        sector_count=len(board_rows), membership_count=count, error_message=None,
    )
    return {
        "status": "success",
        "sector_count": len(board_rows),
        "membership_count": count,
    }


def build_concept_snapshots_from_local_market(
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
        """, [CONCEPT_KIND, CONCEPT_SOURCE]).df()
    if not calendar_rows:
        raise RuntimeError("trade_calendar has no usable dates")
    if memberships.empty:
        raise RuntimeError("concept membership unavailable")

    trade_days = sorted(pd.Timestamp(row[0]).normalize() for row in calendar_rows)
    target = trade_days[-1].date()
    market = _read_local_market_window(
        data_root, start=trade_days[0].date(), end=target
    )
    if market.empty:
        raise RuntimeError("local market bars unavailable for concept aggregation")
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
            sector_kind=CONCEPT_KIND,
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
