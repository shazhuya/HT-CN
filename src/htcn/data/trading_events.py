from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Protocol

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


@dataclass(frozen=True, slots=True)
class DailyEventSyncAudit:
    trade_date: date
    source: str
    status: str
    record_count: int
    coverage_scope: str
    error_message: str | None = None


class DailyTradingEventProvider(Protocol):
    name: str

    def get_daily_trading_events(self, trade_date: date) -> list[SecurityDailyEventRecord]: ...


def ensure_security_daily_event_schema(catalog_path: str | Path) -> None:
    """Create Phase-3.1 event tables without altering frozen M1 core tables."""
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
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS security_daily_event_sync (
                trade_date DATE NOT NULL,
                source VARCHAR NOT NULL,
                status VARCHAR NOT NULL,
                record_count INTEGER NOT NULL,
                coverage_scope VARCHAR NOT NULL,
                error_message VARCHAR,
                updated_at TIMESTAMP NOT NULL,
                PRIMARY KEY (trade_date, source)
            )
            """
        )


def upsert_security_daily_events(
    catalog_path: str | Path,
    records: list[SecurityDailyEventRecord],
) -> int:
    """Persist events without allowing partial evidence to downgrade complete evidence."""
    if not records:
        return 0
    ensure_security_daily_event_schema(catalog_path)
    now = datetime.now(UTC).replace(tzinfo=None)
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
                trading_status = CASE
                    WHEN resolution_complete AND NOT excluded.resolution_complete
                    THEN trading_status
                    ELSE excluded.trading_status
                END,
                no_price_limit = CASE
                    WHEN resolution_complete AND NOT excluded.resolution_complete
                    THEN no_price_limit
                    ELSE excluded.no_price_limit
                END,
                price_limit_pct_override = CASE
                    WHEN resolution_complete AND NOT excluded.resolution_complete
                    THEN price_limit_pct_override
                    ELSE excluded.price_limit_pct_override
                END,
                resolution_complete = (resolution_complete OR excluded.resolution_complete),
                source = CASE
                    WHEN resolution_complete AND NOT excluded.resolution_complete
                    THEN source
                    ELSE excluded.source
                END,
                reason = CASE
                    WHEN resolution_complete AND NOT excluded.resolution_complete
                    THEN reason
                    ELSE excluded.reason
                END,
                updated_at = excluded.updated_at
            """,
            rows,
        )
    return len(rows)


def record_daily_event_sync_audit(
    catalog_path: str | Path,
    audit: DailyEventSyncAudit,
) -> None:
    ensure_security_daily_event_schema(catalog_path)
    now = datetime.now(UTC).replace(tzinfo=None)
    with duckdb.connect(str(catalog_path)) as con:
        con.execute(
            """
            INSERT INTO security_daily_event_sync VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(trade_date, source) DO UPDATE SET
                status = excluded.status,
                record_count = excluded.record_count,
                coverage_scope = excluded.coverage_scope,
                error_message = excluded.error_message,
                updated_at = excluded.updated_at
            """,
            [
                audit.trade_date,
                audit.source,
                audit.status,
                audit.record_count,
                audit.coverage_scope,
                audit.error_message,
                now,
            ],
        )


def sync_daily_trading_events(
    *,
    catalog_path: str | Path,
    provider: DailyTradingEventProvider,
    trade_date: date,
) -> int:
    """Fetch positive event evidence once and persist an auditable sync outcome.

    Current AKShare suspension ingestion is deliberately ``positive_evidence_only``:
    a successful empty response means no suspension row was confirmed by that source; it
    does not certify that every security had no other exchange-level exception that day.
    """
    source = getattr(provider, "event_source", None) or getattr(provider, "name", "unknown")
    try:
        records = provider.get_daily_trading_events(trade_date)
        wrong_date = [record for record in records if record.trade_date != trade_date]
        if wrong_date:
            raise ValueError("daily trading event provider returned records for another date")
        stored = upsert_security_daily_events(catalog_path, records)
        record_daily_event_sync_audit(
            catalog_path,
            DailyEventSyncAudit(
                trade_date=trade_date,
                source=str(source),
                status="success",
                record_count=stored,
                coverage_scope="positive_evidence_only",
            ),
        )
        return stored
    except Exception as exc:
        record_daily_event_sync_audit(
            catalog_path,
            DailyEventSyncAudit(
                trade_date=trade_date,
                source=str(source),
                status="failed",
                record_count=0,
                coverage_scope="positive_evidence_only",
                error_message=f"{type(exc).__name__}: {exc}",
            ),
        )
        raise
