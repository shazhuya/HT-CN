from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import duckdb

from .models import Security


class DataCatalog:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self.path))

    def _init_schema(self) -> None:
        with self._connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_dataset (
                    instrument_id VARCHAR PRIMARY KEY,
                    source VARCHAR NOT NULL,
                    parquet_path VARCHAR NOT NULL,
                    row_count BIGINT NOT NULL,
                    first_trade_date DATE,
                    last_trade_date DATE,
                    updated_at TIMESTAMP NOT NULL
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS security_master (
                    instrument_id VARCHAR PRIMARY KEY,
                    symbol VARCHAR NOT NULL,
                    exchange VARCHAR NOT NULL,
                    name VARCHAR NOT NULL,
                    board VARCHAR NOT NULL,
                    list_date DATE,
                    delist_date DATE,
                    is_st BOOLEAN NOT NULL,
                    status VARCHAR NOT NULL,
                    source VARCHAR NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS trade_calendar (
                    trade_date DATE PRIMARY KEY,
                    source VARCHAR NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_task (
                    instrument_id VARCHAR PRIMARY KEY,
                    status VARCHAR NOT NULL,
                    error_message VARCHAR,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP NOT NULL
                )
                """
            )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def record_daily(
        self,
        *,
        instrument_id: str,
        source: str,
        parquet_path: str,
        row_count: int,
        first_trade_date: str | None,
        last_trade_date: str | None,
    ) -> None:
        now = self._now()
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO daily_dataset VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(instrument_id) DO UPDATE SET
                    source = excluded.source,
                    parquet_path = excluded.parquet_path,
                    row_count = excluded.row_count,
                    first_trade_date = excluded.first_trade_date,
                    last_trade_date = excluded.last_trade_date,
                    updated_at = excluded.updated_at
                """,
                [
                    instrument_id,
                    source,
                    parquet_path,
                    row_count,
                    first_trade_date,
                    last_trade_date,
                    now,
                ],
            )

    def get_daily(self, instrument_id: str) -> dict[str, object] | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM daily_dataset WHERE instrument_id = ?",
                [instrument_id],
            ).fetchone()
            if row is None:
                return None
            columns = [description[0] for description in con.description]
            return dict(zip(columns, row, strict=True))

    def upsert_securities(self, securities: list[Security], *, source: str) -> int:
        if not securities:
            return 0
        now = self._now()
        rows = [
            [
                item.instrument_id,
                item.symbol,
                item.exchange.value,
                item.name,
                item.board.value,
                item.list_date,
                item.delist_date,
                item.is_st,
                item.status,
                source,
                now,
            ]
            for item in securities
        ]
        with self._connect() as con:
            con.executemany(
                """
                INSERT INTO security_master VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(instrument_id) DO UPDATE SET
                    symbol = excluded.symbol,
                    exchange = excluded.exchange,
                    name = excluded.name,
                    board = excluded.board,
                    list_date = COALESCE(excluded.list_date, security_master.list_date),
                    delist_date = COALESCE(excluded.delist_date, security_master.delist_date),
                    is_st = excluded.is_st,
                    status = excluded.status,
                    source = excluded.source,
                    updated_at = excluded.updated_at
                """,
                rows,
            )
        return len(rows)

    def security_count(self) -> int:
        with self._connect() as con:
            return int(con.execute("SELECT COUNT(*) FROM security_master").fetchone()[0])

    def record_trade_calendar(self, days: list[date], *, source: str) -> int:
        if not days:
            return 0
        now = self._now()
        rows = [[day, source, now] for day in days]
        with self._connect() as con:
            con.executemany(
                """
                INSERT INTO trade_calendar VALUES (?, ?, ?)
                ON CONFLICT(trade_date) DO UPDATE SET
                    source = excluded.source,
                    updated_at = excluded.updated_at
                """,
                rows,
            )
        return len(rows)

    def calendar_count(self) -> int:
        with self._connect() as con:
            return int(con.execute("SELECT COUNT(*) FROM trade_calendar").fetchone()[0])

    def mark_task(self, instrument_id: str, status: str, error_message: str | None = None) -> None:
        now = self._now()
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO sync_task VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(instrument_id) DO UPDATE SET
                    status = excluded.status,
                    error_message = excluded.error_message,
                    attempt_count = sync_task.attempt_count + 1,
                    updated_at = excluded.updated_at
                """,
                [instrument_id, status, error_message, now],
            )

    def task_status(self, instrument_id: str) -> dict[str, object] | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM sync_task WHERE instrument_id = ?",
                [instrument_id],
            ).fetchone()
            if row is None:
                return None
            columns = [description[0] for description in con.description]
            return dict(zip(columns, row, strict=True))
