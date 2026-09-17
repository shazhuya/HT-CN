from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb


@dataclass(frozen=True, slots=True)
class SecurityDailyEventRecord:
    instrument_id: str
    trade_date: date
    trading_status: str
    no_price_limit: bool | None
    price_limit_pct_override: float | None
    resolution_complete: bool
    source: str
    reason: str | None = None


def ensure_security_daily_event_schema(catalog_path: str | Path) -> None:
    """Create the optional Phase-3.1 daily event table without touching M1 core tables."""
    path = Path(catalog_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(path)) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS security_daily_event (
                instrument_id VARCHAR NOT NULL,
                trade_date DATE NOT NULL,
                trading_status VARCHAR NOT NULL,
                no_price_limit BOOLEAN,
                price_limit_pct_override DOUBLE,
                resolution_complete BOOLEAN NOT NULL,
                source VARCHAR NOT NULL,
                reason VARCHAR,
                updated_at TIMESTAMP NOT NULL,
                PRIMARY KEY (instrument_id, trade_date)
            )
            """
        )


def upsert_security_daily_events(
    catalog_path: str | Path,
    records: list[SecurityDailyEventRecord],
) -> int:
    if not records:
        return 0
    ensure_security_daily_event_schema(catalog_path)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    rows = [
        [
            record.instrument_id,
            record.trade_date,
            record.trading_status,
            record.no_price_limit,
            record.price_limit_pct_override,
            record.resolution_complete,
            record.source,
            record.reason,
            now,
        ]
        for record in records
    ]
    with duckdb.connect(str(catalog_path)) as con:
        con.executemany(
            """
            INSERT INTO security_daily_event VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(instrument_id, trade_date) DO UPDATE SET
                trading_status = excluded.trading_status,
                no_price_limit = excluded.no_price_limit,
                price_limit_pct_override = excluded.price_limit_pct_override,
                resolution_complete = excluded.resolution_complete,
                source = excluded.source,
                reason = excluded.reason,
                updated_at = excluded.updated_at
            """,
            rows,
        )
    return len(rows)
