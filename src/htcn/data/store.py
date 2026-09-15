from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from .validation import normalize_daily


class ParquetDailyStore:
    """Local daily-bar store.

    M1 keeps the layout simple and deterministic: one parquet file per instrument.
    Later milestones can migrate to larger year partitions without changing callers.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_name(instrument_id: str) -> str:
        return instrument_id.replace(":", "_").replace("/", "_")

    def path_for(self, instrument_id: str) -> Path:
        return self.root / f"{self._safe_name(instrument_id)}.parquet"

    def read(
        self,
        instrument_id: str,
        start: date | None = None,
        end: date | None = None,
    ) -> pd.DataFrame:
        path = self.path_for(instrument_id)
        if not path.exists():
            return pd.DataFrame()

        frame = pd.read_parquet(path)
        if frame.empty:
            return frame

        frame["trade_date"] = pd.to_datetime(frame["trade_date"]).dt.normalize()
        if start is not None:
            frame = frame[frame["trade_date"] >= pd.Timestamp(start)]
        if end is not None:
            frame = frame[frame["trade_date"] <= pd.Timestamp(end)]
        return frame.reset_index(drop=True)

    def upsert(self, frame: pd.DataFrame) -> pd.DataFrame:
        incoming = normalize_daily(frame)
        if incoming.empty:
            return incoming

        instrument_ids = incoming["instrument_id"].unique().tolist()
        if len(instrument_ids) != 1:
            raise ValueError("ParquetDailyStore.upsert expects exactly one instrument")

        instrument_id = str(instrument_ids[0])
        existing = self.read(instrument_id)
        if not existing.empty:
            merged = pd.concat([existing, incoming], ignore_index=True)
        else:
            merged = incoming

        merged = normalize_daily(merged)
        path = self.path_for(instrument_id)
        tmp = path.with_suffix(".parquet.tmp")
        merged.to_parquet(tmp, index=False)
        tmp.replace(path)
        return merged

    def latest_date(self, instrument_id: str) -> date | None:
        frame = self.read(instrument_id)
        if frame.empty:
            return None
        return pd.Timestamp(frame["trade_date"].max()).date()
