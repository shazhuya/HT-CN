from __future__ import annotations

from datetime import UTC, date, datetime
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
        return datetime.now(UTC).replace(tzinfo=None)

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

    def list_daily_datasets(self) -> list[dict[str, object]]:
        """Return all daily-dataset metadata with one DuckDB connection.

        Health/audit jobs must not call get_daily() once for every security in the market;
        doing so creates thousands of short-lived DuckDB connections and makes the command
        appear hung before it produces any output.
        """
        with self._connect() as con:
            rows = con.execute(
                "SELECT * FROM daily_dataset ORDER BY instrument_id"
            ).fetchall()
            columns = [description[0] for description in con.description]
        return [dict(zip(columns, row, strict=True)) for row in rows]

    def daily_dataset_count(self) -> int:
        with self._connect() as con:
            return int(con.execute("SELECT COUNT(*) FROM daily_dataset").fetchone()[0])

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

    def list_security_ids(self, *, listed_only: bool = True) -> list[str]:
        sql = "SELECT instrument_id FROM security_master"
        params: list[object] = []
        if listed_only:
            sql += " WHERE status = ?"
            params.append("listed")
        sql += " ORDER BY instrument_id"
        with self._connect() as con:
            return [row[0] for row in con.execute(sql, params).fetchall()]

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

    def begin_task(self, instrument_id: str) -> None:
        """Start one synchronization attempt and increment attempt_count exactly once."""
        now = self._now()
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO sync_task VALUES (?, 'RUNNING', NULL, 1, ?)
                ON CONFLICT(instrument_id) DO UPDATE SET
                    status = 'RUNNING',
                    error_message = NULL,
                    attempt_count = sync_task.attempt_count + 1,
                    updated_at = excluded.updated_at
                """,
                [instrument_id, now],
            )

    def finish_task(
        self,
        instrument_id: str,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """Finish a task without incrementing attempt_count."""
        now = self._now()
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO sync_task VALUES (?, ?, ?, 0, ?)
                ON CONFLICT(instrument_id) DO UPDATE SET
                    status = excluded.status,
                    error_message = excluded.error_message,
                    updated_at = excluded.updated_at
                """,
                [instrument_id, status, error_message, now],
            )

    def mark_task(self, instrument_id: str, status: str, error_message: str | None = None) -> None:
        """Compatibility wrapper retained for M1 scripts/tests."""
        if status == "RUNNING":
            self.begin_task(instrument_id)
        else:
            self.finish_task(instrument_id, status, error_message)

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

    def task_counts(self) -> dict[str, int]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT status, COUNT(*) FROM sync_task GROUP BY status ORDER BY status"
            ).fetchall()
        return {str(status): int(count) for status, count in rows}

    def failed_tasks(self, *, limit: int = 20) -> list[dict[str, object]]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT instrument_id, status, error_message, attempt_count, updated_at
                FROM sync_task
                WHERE status = 'FAILED'
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                [limit],
            ).fetchall()
            columns = [description[0] for description in con.description]
        return [dict(zip(columns, row, strict=True)) for row in rows]

    def sync_candidates(
        self,
        *,
        max_attempts: int = 5,
        limit: int | None = None,
    ) -> list[str]:
        """Return listed instruments that still need their initial durable daily dataset.

        COMPLETED instruments with an existing daily_dataset entry are skipped. RUNNING rows
        from an interrupted process are intentionally eligible again so a rerun resumes work.
        """
        sql = """
            SELECT s.instrument_id
            FROM security_master AS s
            LEFT JOIN sync_task AS t ON t.instrument_id = s.instrument_id
            LEFT JOIN daily_dataset AS d ON d.instrument_id = s.instrument_id
            WHERE s.status = 'listed'
              AND NOT (COALESCE(t.status, '') = 'COMPLETED' AND d.instrument_id IS NOT NULL)
              AND COALESCE(t.attempt_count, 0) < ?
            ORDER BY s.instrument_id
        """
        params: list[object] = [max_attempts]
        if limit is not None and limit > 0:
            sql += " LIMIT ?"
            params.append(limit)
        with self._connect() as con:
            return [row[0] for row in con.execute(sql, params).fetchall()]
