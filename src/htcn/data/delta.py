from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from .store import ParquetDailyStore
from .validation import normalize_daily


class MarketDailyDeltaStore:
    """One compact all-market delta parquet per trade date.

    Daily maintenance writes one file instead of rewriting thousands of per-symbol history
    files. Periodic compaction may later fold deltas into the base store.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, trade_date: date) -> Path:
        return self.root / f"{trade_date.isoformat()}.parquet"

    def write(self, frame: pd.DataFrame, *, trade_date: date) -> Path:
        normalized = normalize_daily(frame)
        normalized = normalized[
            pd.to_datetime(normalized["trade_date"]).dt.date == trade_date
        ].copy()
        if normalized.empty:
            raise ValueError(f"delta frame has no rows for {trade_date}")
        normalized = normalized.drop_duplicates(
            ["instrument_id", "trade_date"], keep="last"
        ).sort_values("instrument_id")
        path = self.path_for(trade_date)
        tmp = path.with_suffix(".parquet.tmp")
        normalized.to_parquet(tmp, index=False)
        tmp.replace(path)
        return path

    def read_date(self, trade_date: date) -> pd.DataFrame:
        path = self.path_for(trade_date)
        if not path.exists():
            return pd.DataFrame()
        return normalize_daily(pd.read_parquet(path))

    def list_dates(self) -> list[date]:
        result: list[date] = []
        for path in self.root.glob("*.parquet"):
            try:
                result.append(date.fromisoformat(path.stem))
            except ValueError:
                continue
        return sorted(set(result))

    def read_instrument(
        self,
        instrument_id: str,
        start: date | None = None,
        end: date | None = None,
    ) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []
        for trade_date in self.list_dates():
            if start is not None and trade_date < start:
                continue
            if end is not None and trade_date > end:
                continue
            frame = self.read_date(trade_date)
            if frame.empty:
                continue
            selected = frame[frame["instrument_id"].astype(str) == instrument_id]
            if not selected.empty:
                frames.append(selected)
        if not frames:
            return pd.DataFrame()
        return normalize_daily(pd.concat(frames, ignore_index=True))

    def latest_dates_by_instrument(self) -> dict[str, date]:
        latest: dict[str, date] = {}
        for trade_date in self.list_dates():
            frame = self.read_date(trade_date)
            if frame.empty:
                continue
            for instrument_id in frame["instrument_id"].astype(str).unique().tolist():
                latest[instrument_id] = trade_date
        return latest

    def remove_dates(self, dates: list[date]) -> None:
        for trade_date in dates:
            path = self.path_for(trade_date)
            if path.exists():
                path.unlink()


class DailyHistoryView:
    """Logical history = durable base parquet + un-compacted market deltas."""

    def __init__(self, base: ParquetDailyStore, deltas: MarketDailyDeltaStore) -> None:
        self.base = base
        self.deltas = deltas

    def read(
        self,
        instrument_id: str,
        start: date | None = None,
        end: date | None = None,
    ) -> pd.DataFrame:
        base = self.base.read(instrument_id, start, end)
        delta = self.deltas.read_instrument(instrument_id, start, end)
        if base.empty:
            return delta
        if delta.empty:
            return base
        return normalize_daily(pd.concat([base, delta], ignore_index=True))


def compact_daily_deltas(
    *,
    base: ParquetDailyStore,
    deltas: MarketDailyDeltaStore,
    dates: list[date] | None = None,
) -> tuple[int, int]:
    """Fold selected delta files into per-symbol base files, then remove those deltas.

    Returns (instrument_count, row_count). The function is intentionally explicit/manual
    in M1; normal daily maintenance should remain append-only and fast.
    """
    selected_dates = dates if dates is not None else deltas.list_dates()
    frames = [deltas.read_date(day) for day in selected_dates]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return 0, 0

    combined = normalize_daily(pd.concat(frames, ignore_index=True))
    instruments = 0
    for instrument_id, group in combined.groupby("instrument_id", sort=True):
        base.upsert(group.reset_index(drop=True))
        instruments += 1
    deltas.remove_dates(selected_dates)
    return instruments, len(combined)
