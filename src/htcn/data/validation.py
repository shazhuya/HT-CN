from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = [
    "instrument_id",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "volume",
]

OPTIONAL_COLUMNS = ["amount", "pre_close", "pct_change", "turnover", "source"]


class DataValidationError(ValueError):
    pass


def normalize_daily(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise DataValidationError(f"missing required columns: {missing}")

    out = frame.copy()
    out["trade_date"] = pd.to_datetime(out["trade_date"], errors="raise").dt.normalize()

    numeric = ["open", "high", "low", "close", "volume", "amount", "pre_close", "pct_change", "turnover"]
    for column in numeric:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="raise")

    if out[REQUIRED_COLUMNS].isnull().any().any():
        raise DataValidationError("required daily fields contain null values")

    if (out[["open", "high", "low", "close"]] <= 0).any().any():
        raise DataValidationError("OHLC prices must be positive")
    if (out["volume"] < 0).any():
        raise DataValidationError("volume must be non-negative")
    if (out["high"] < out[["open", "close", "low"]].max(axis=1)).any():
        raise DataValidationError("high is below another OHLC field")
    if (out["low"] > out[["open", "close", "high"]].min(axis=1)).any():
        raise DataValidationError("low is above another OHLC field")

    out = out.drop_duplicates(subset=["instrument_id", "trade_date"], keep="last")
    out = out.sort_values(["instrument_id", "trade_date"]).reset_index(drop=True)

    ordered = REQUIRED_COLUMNS + [column for column in OPTIONAL_COLUMNS if column in out.columns]
    return out[ordered]
