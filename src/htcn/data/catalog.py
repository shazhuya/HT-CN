from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import duckdb


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
        now = datetime.now(timezone.utc).replace(tzinfo=None)
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
