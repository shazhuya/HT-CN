from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

import pandas as pd

SUPPORTED_INTRADAY_TIMEFRAMES: dict[str, str] = {
    "15m": "15",
    "60m": "60",
}


class IntradayProviderError(RuntimeError):
    pass


class IntradayProvider(Protocol):
    def fetch(
        self,
        instrument_id: str,
        *,
        timeframe: str,
        start: datetime,
        end: datetime,
        adjust: str = "qfq",
    ) -> IntradayBars:
        ...


@dataclass(frozen=True, slots=True)
class IntradayBars:
    instrument_id: str
    timeframe: str
    adjustment: str
    provider: str
    fetched_at: pd.Timestamp
    frame: pd.DataFrame

    def __post_init__(self) -> None:
        if self.timeframe not in SUPPORTED_INTRADAY_TIMEFRAMES:
            raise ValueError(f"unsupported intraday timeframe: {self.timeframe}")
        required = {"trade_time", "open", "high", "low", "close", "volume"}
        missing = required.difference(self.frame.columns)
        if missing:
            raise ValueError(f"intraday frame missing columns: {sorted(missing)}")

    @property
    def first_trade_time(self) -> pd.Timestamp | None:
        if self.frame.empty:
            return None
        return pd.Timestamp(self.frame["trade_time"].iloc[0])

    @property
    def last_trade_time(self) -> pd.Timestamp | None:
        if self.frame.empty:
            return None
        return pd.Timestamp(self.frame["trade_time"].iloc[-1])


def _split_instrument(instrument_id: str) -> tuple[str, str]:
    try:
        exchange, code = instrument_id.upper().split(".", 1)
    except ValueError as exc:
        raise ValueError(f"invalid instrument id: {instrument_id}") from exc
    if exchange not in {"SSE", "SZSE", "BSE"} or not code.isdigit():
        raise ValueError(f"invalid A-share instrument id: {instrument_id}")
    return exchange, code


def _sina_symbol(instrument_id: str) -> str:
    exchange, code = _split_instrument(instrument_id)
    prefix = {"SSE": "sh", "SZSE": "sz", "BSE": "bj"}[exchange]
    return f"{prefix}{code}"


def _code_only(instrument_id: str) -> str:
    return _split_instrument(instrument_id)[1]


def _normalize_intraday(
    raw: pd.DataFrame,
    *,
    instrument_id: str,
    timeframe: str,
    provider: str,
    adjustment: str,
) -> IntradayBars:
    if raw is None or raw.empty:
        return IntradayBars(
            instrument_id=instrument_id,
            timeframe=timeframe,
            adjustment=adjustment,
            provider=provider,
            fetched_at=pd.Timestamp.now(tz="Asia/Shanghai"),
            frame=pd.DataFrame(
                columns=["trade_time", "open", "high", "low", "close", "volume"]
            ),
        )

    aliases = {
        "时间": "trade_time",
        "日期": "trade_time",
        "day": "trade_time",
        "datetime": "trade_time",
        "开盘": "open",
        "open": "open",
        "最高": "high",
        "high": "high",
        "最低": "low",
        "low": "low",
        "收盘": "close",
        "close": "close",
        "成交量": "volume",
        "volume": "volume",
    }
    columns: dict[str, str] = {}
    for column in raw.columns:
        key = str(column).strip()
        if key in aliases:
            columns[column] = aliases[key]
    normalized = raw.rename(columns=columns)
    required = ["trade_time", "open", "high", "low", "close"]
    missing = [column for column in required if column not in normalized.columns]
    if missing:
        raise IntradayProviderError(
            f"{provider} intraday response missing columns: {missing}; got={list(raw.columns)}"
        )
    if "volume" not in normalized.columns:
        normalized["volume"] = 0.0

    frame = normalized[["trade_time", "open", "high", "low", "close", "volume"]].copy()
    frame["trade_time"] = pd.to_datetime(frame["trade_time"], errors="coerce")
    for column in ("open", "high", "low", "close", "volume"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["trade_time", "open", "high", "low", "close"])
    frame = frame.loc[frame["high"] >= frame["low"]]
    frame = (
        frame.drop_duplicates(subset=["trade_time"], keep="last")
        .sort_values("trade_time")
        .reset_index(drop=True)
    )
    return IntradayBars(
        instrument_id=instrument_id,
        timeframe=timeframe,
        adjustment=adjustment,
        provider=provider,
        fetched_at=pd.Timestamp.now(tz="Asia/Shanghai"),
        frame=frame,
    )


class AkShareIntradayProvider:
    """A-share 15/60 minute provider with Eastmoney -> Sina failover."""

    def __init__(self, ak_module: Any | None = None) -> None:
        self._ak_module = ak_module

    def _ak(self):
        if self._ak_module is not None:
            return self._ak_module
        import akshare as ak

        return ak

    def _eastmoney(
        self,
        instrument_id: str,
        *,
        period: str,
        start: datetime,
        end: datetime,
        adjust: str,
    ) -> pd.DataFrame:
        return self._ak().stock_zh_a_hist_min_em(
            symbol=_code_only(instrument_id),
            period=period,
            start_date=start.strftime("%Y-%m-%d %H:%M:%S"),
            end_date=end.strftime("%Y-%m-%d %H:%M:%S"),
            adjust=adjust,
        )

    def _sina(
        self,
        instrument_id: str,
        *,
        period: str,
        adjust: str,
    ) -> pd.DataFrame:
        return self._ak().stock_zh_a_minute(
            symbol=_sina_symbol(instrument_id),
            period=period,
            adjust=adjust,
        )

    def fetch(
        self,
        instrument_id: str,
        *,
        timeframe: str,
        start: datetime,
        end: datetime,
        adjust: str = "qfq",
    ) -> IntradayBars:
        if timeframe not in SUPPORTED_INTRADAY_TIMEFRAMES:
            raise ValueError(f"unsupported intraday timeframe: {timeframe}")
        if start >= end:
            raise ValueError("intraday start must be before end")
        period = SUPPORTED_INTRADAY_TIMEFRAMES[timeframe]
        failures: list[str] = []

        try:
            raw = self._eastmoney(
                instrument_id,
                period=period,
                start=start,
                end=end,
                adjust=adjust,
            )
            result = _normalize_intraday(
                raw,
                instrument_id=instrument_id,
                timeframe=timeframe,
                provider="akshare_eastmoney",
                adjustment=adjust,
            )
            if not result.frame.empty:
                return result
            failures.append("eastmoney returned no rows")
        except Exception as exc:  # noqa: BLE001 - third-party provider boundary must fail over
            failures.append(f"eastmoney: {type(exc).__name__}: {exc}")

        try:
            raw = self._sina(
                instrument_id,
                period=period,
                adjust=adjust,
            )
            result = _normalize_intraday(
                raw,
                instrument_id=instrument_id,
                timeframe=timeframe,
                provider="akshare_sina",
                adjustment=adjust,
            )
            start_bound = pd.Timestamp(start)
            end_bound = pd.Timestamp(end)
            if start_bound.tzinfo is not None:
                start_bound = start_bound.tz_convert("Asia/Shanghai").tz_localize(None)
            if end_bound.tzinfo is not None:
                end_bound = end_bound.tz_convert("Asia/Shanghai").tz_localize(None)
            bounded = result.frame.loc[
                (result.frame["trade_time"] >= start_bound)
                & (result.frame["trade_time"] <= end_bound)
            ].reset_index(drop=True)
            if not bounded.empty:
                return IntradayBars(
                    instrument_id=result.instrument_id,
                    timeframe=result.timeframe,
                    adjustment=result.adjustment,
                    provider=result.provider,
                    fetched_at=result.fetched_at,
                    frame=bounded,
                )
            failures.append("sina returned no rows in requested range")
        except Exception as exc:  # noqa: BLE001 - third-party provider boundary must fail over
            failures.append(f"sina: {type(exc).__name__}: {exc}")

        raise IntradayProviderError(
            f"no intraday provider succeeded for {instrument_id} {timeframe}: "
            + " | ".join(failures)
        )


class ParquetIntradayCache:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def path_for(self, instrument_id: str, timeframe: str) -> Path:
        if timeframe not in SUPPORTED_INTRADAY_TIMEFRAMES:
            raise ValueError(f"unsupported intraday timeframe: {timeframe}")
        return self.root / timeframe / f"{instrument_id}.parquet"

    def read(self, instrument_id: str, timeframe: str) -> IntradayBars | None:
        path = self.path_for(instrument_id, timeframe)
        if not path.exists():
            return None
        frame = pd.read_parquet(path)
        if frame.empty:
            return None
        provider = str(frame["provider"].iloc[-1]) if "provider" in frame else "cache_unknown"
        adjustment = str(frame["adjustment"].iloc[-1]) if "adjustment" in frame else "unknown"
        fetched_at = (
            pd.Timestamp(frame["fetched_at"].iloc[-1])
            if "fetched_at" in frame
            else pd.Timestamp(path.stat().st_mtime, unit="s", tz="UTC").tz_convert("Asia/Shanghai")
        )
        core = frame[["trade_time", "open", "high", "low", "close", "volume"]].copy()
        return IntradayBars(
            instrument_id=instrument_id,
            timeframe=timeframe,
            adjustment=adjustment,
            provider=provider,
            fetched_at=fetched_at,
            frame=core,
        )

    def write(self, bars: IntradayBars) -> Path:
        path = self.path_for(bars.instrument_id, bars.timeframe)
        path.parent.mkdir(parents=True, exist_ok=True)
        frame = bars.frame.copy()
        frame["provider"] = bars.provider
        frame["adjustment"] = bars.adjustment
        frame["fetched_at"] = bars.fetched_at.isoformat()
        temp = path.with_suffix(".tmp.parquet")
        frame.to_parquet(temp, index=False)
        temp.replace(path)
        return path
