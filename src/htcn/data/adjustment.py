from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .validation import normalize_daily

FACTOR_COLUMNS = ["instrument_id", "trade_date", "price_factor", "mode", "source"]


def derive_price_factors(
    raw_frame: pd.DataFrame,
    adjusted_frame: pd.DataFrame,
    *,
    mode: str = "qfq",
    source: str = "akshare_qfq",
) -> pd.DataFrame:
    """Derive effective price-adjustment factors from raw and adjusted closes.

    factor(t) = adjusted_close(t) / raw_close(t)

    Raw OHLCV remains HT-CN's durable source of truth. The factor layer is separate so
    adjusted prices can be regenerated and audited without redownloading raw history.
    """
    if mode not in {"qfq", "hfq"}:
        raise ValueError("mode must be 'qfq' or 'hfq'")

    raw = normalize_daily(raw_frame)
    adjusted = normalize_daily(adjusted_frame)
    if raw.empty or adjusted.empty:
        return pd.DataFrame(columns=FACTOR_COLUMNS)

    raw_ids = set(raw["instrument_id"].astype(str).unique())
    adjusted_ids = set(adjusted["instrument_id"].astype(str).unique())
    if len(raw_ids) != 1 or raw_ids != adjusted_ids:
        raise ValueError("raw and adjusted frames must contain the same single instrument")

    merged = raw[["instrument_id", "trade_date", "close"]].merge(
        adjusted[["instrument_id", "trade_date", "close"]],
        on=["instrument_id", "trade_date"],
        how="inner",
        suffixes=("_raw", "_adjusted"),
        validate="one_to_one",
    )
    if merged.empty:
        return pd.DataFrame(columns=FACTOR_COLUMNS)

    factor = merged["close_adjusted"] / merged["close_raw"]
    if (~np.isfinite(factor)).any() or (factor <= 0).any():
        raise ValueError("derived adjustment factor must be finite and positive")

    out = merged[["instrument_id", "trade_date"]].copy()
    out["price_factor"] = factor.astype(float)
    out["mode"] = mode
    out["source"] = source
    return out[FACTOR_COLUMNS].sort_values("trade_date").reset_index(drop=True)


def apply_price_factors(raw_frame: pd.DataFrame, factors: pd.DataFrame) -> pd.DataFrame:
    """Return an adjusted OHLC view while preserving raw volume/amount fields."""
    raw = normalize_daily(raw_frame)
    if raw.empty:
        return raw
    required = {"instrument_id", "trade_date", "price_factor"}
    missing = required.difference(factors.columns)
    if missing:
        raise ValueError(f"factor frame missing columns: {sorted(missing)}")

    factor_frame = factors[["instrument_id", "trade_date", "price_factor"]].copy()
    factor_frame["trade_date"] = pd.to_datetime(factor_frame["trade_date"]).dt.normalize()
    merged = raw.merge(
        factor_frame,
        on=["instrument_id", "trade_date"],
        how="left",
        validate="one_to_one",
    )
    if merged["price_factor"].isna().any():
        missing_dates = merged.loc[merged["price_factor"].isna(), "trade_date"].dt.date.tolist()
        raise ValueError(f"missing adjustment factors for dates: {missing_dates[:5]}")

    for column in ("open", "high", "low", "close", "pre_close"):
        if column in merged.columns:
            merged[column] = merged[column] * merged["price_factor"]
    merged = merged.drop(columns=["price_factor"])
    return normalize_daily(merged)


class AdjustmentFactorStore:
    """One compact factor parquet per instrument for M1.

    Factors are intentionally kept separate from raw history. A later point-in-time
    backtest layer can version factor knowledge without rewriting the raw data lake.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_name(instrument_id: str) -> str:
        return instrument_id.replace(":", "_").replace("/", "_")

    def path_for(self, instrument_id: str) -> Path:
        return self.root / f"{self._safe_name(instrument_id)}.parquet"

    def write(self, factors: pd.DataFrame) -> Path:
        if factors.empty:
            raise ValueError("cannot write empty adjustment factor frame")
        instrument_ids = factors["instrument_id"].astype(str).unique().tolist()
        if len(instrument_ids) != 1:
            raise ValueError("factor store expects exactly one instrument")
        out = factors.copy()
        out["trade_date"] = pd.to_datetime(out["trade_date"]).dt.normalize()
        out["price_factor"] = pd.to_numeric(out["price_factor"], errors="raise")
        out = out.drop_duplicates(["instrument_id", "trade_date"], keep="last")
        out = out.sort_values("trade_date").reset_index(drop=True)
        path = self.path_for(instrument_ids[0])
        tmp = path.with_suffix(".parquet.tmp")
        out.to_parquet(tmp, index=False)
        tmp.replace(path)
        return path

    def read(self, instrument_id: str) -> pd.DataFrame:
        path = self.path_for(instrument_id)
        if not path.exists():
            return pd.DataFrame(columns=FACTOR_COLUMNS)
        out = pd.read_parquet(path)
        out["trade_date"] = pd.to_datetime(out["trade_date"]).dt.normalize()
        return out.sort_values("trade_date").reset_index(drop=True)
