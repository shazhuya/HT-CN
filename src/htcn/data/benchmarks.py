from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True, slots=True)
class BenchmarkSpec:
    key: str
    symbol: str
    name_zh: str


CORE_BENCHMARKS: tuple[BenchmarkSpec, ...] = (
    BenchmarkSpec("star50", "000688", "科创50"),
    BenchmarkSpec("chinext", "399006", "创业板指"),
    BenchmarkSpec("csi300", "000300", "沪深300"),
    BenchmarkSpec("sse_composite", "000001", "上证指数"),
)


class CoreBenchmarkStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, key: str) -> Path:
        return self.root / f"{key}.parquet"

    def read(self, key: str) -> pd.DataFrame:
        path = self.path_for(key)
        if not path.exists():
            return pd.DataFrame()
        frame = pd.read_parquet(path)
        if frame.empty:
            return frame
        frame = frame.copy()
        frame["trade_date"] = pd.to_datetime(
            frame["trade_date"], errors="coerce"
        ).dt.normalize()
        frame = frame.dropna(subset=["trade_date", "close"])
        return (
            frame.sort_values("trade_date")
            .drop_duplicates("trade_date", keep="last")
            .reset_index(drop=True)
        )

    def upsert(self, key: str, incoming: pd.DataFrame) -> pd.DataFrame:
        required = {"trade_date", "open", "high", "low", "close"}
        missing = required.difference(incoming.columns)
        if missing:
            raise ValueError(f"benchmark data missing columns: {sorted(missing)}")
        frame = incoming.copy()
        frame["trade_date"] = pd.to_datetime(
            frame["trade_date"], errors="raise"
        ).dt.normalize()
        for column in ("open", "high", "low", "close"):
            frame[column] = pd.to_numeric(frame[column], errors="raise")
        existing = self.read(key)
        if not existing.empty:
            frame = pd.concat([existing, frame], ignore_index=True)
        frame = (
            frame.sort_values("trade_date")
            .drop_duplicates("trade_date", keep="last")
            .reset_index(drop=True)
        )
        path = self.path_for(key)
        tmp = path.with_suffix(".parquet.tmp")
        frame.to_parquet(tmp, index=False)
        tmp.replace(path)
        return frame
