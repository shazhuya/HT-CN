from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from htcn.data.benchmarks import CORE_BENCHMARKS, CoreBenchmarkStore


@dataclass(frozen=True, slots=True)
class BenchmarkContext:
    key: str
    symbol: str
    name_zh: str
    available: bool
    as_of_trade_date: str | None
    close: float | None
    return_1d_pct: float | None
    return_5d_pct: float | None
    return_20d_pct: float | None
    ma20: float | None
    distance_to_ma20_pct: float | None
    ma20_slope_5d_pct: float | None
    trend_state: str
    instrument_relative_5d_pct: float | None
    instrument_relative_20d_pct: float | None


@dataclass(frozen=True, slots=True)
class MarketContext:
    status: str
    as_of_trade_date: str | None
    benchmarks: tuple[BenchmarkContext, ...]
    mutates_harmonic_identity: bool = False
    mutates_source_raw_prz: bool = False
    owns_lifecycle: bool = False

    def as_payload(self) -> dict[str, object]:
        return {
            "status": self.status,
            "as_of_trade_date": self.as_of_trade_date,
            "benchmarks": [asdict(item) for item in self.benchmarks],
            "mutates_harmonic_identity": self.mutates_harmonic_identity,
            "mutates_source_raw_prz": self.mutates_source_raw_prz,
            "owns_lifecycle": self.owns_lifecycle,
        }


def _return_pct(close: pd.Series, sessions: int) -> float | None:
    if len(close) <= sessions:
        return None
    start = float(close.iloc[-sessions - 1])
    end = float(close.iloc[-1])
    if start <= 0:
        return None
    return 100.0 * (end / start - 1.0)


def _stock_return(frame: pd.DataFrame, sessions: int, as_of: pd.Timestamp) -> float | None:
    if frame.empty or "trade_date" not in frame.columns or "close" not in frame.columns:
        return None
    work = frame.copy()
    work["trade_date"] = pd.to_datetime(
        work["trade_date"], errors="coerce"
    ).dt.normalize()
    work = work[work["trade_date"] <= as_of].dropna(
        subset=["trade_date", "close"]
    )
    work = work.sort_values("trade_date").drop_duplicates(
        "trade_date", keep="last"
    )
    close = pd.to_numeric(work["close"], errors="coerce").dropna()
    return _return_pct(close, sessions)


def _unavailable(spec) -> BenchmarkContext:
    return BenchmarkContext(
        spec.key,
        spec.symbol,
        spec.name_zh,
        False,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        "unavailable",
        None,
        None,
    )


def _benchmark_context(
    spec,
    frame: pd.DataFrame,
    *,
    instrument_frame: pd.DataFrame,
    as_of: pd.Timestamp | None,
) -> BenchmarkContext:
    if frame.empty or as_of is None:
        return _unavailable(spec)
    work = frame.copy()
    work["trade_date"] = pd.to_datetime(
        work["trade_date"], errors="coerce"
    ).dt.normalize()
    work = work[work["trade_date"] <= as_of].dropna(
        subset=["trade_date", "close"]
    )
    work = work.sort_values("trade_date").drop_duplicates(
        "trade_date", keep="last"
    )
    if work.empty:
        return _unavailable(spec)
    close = pd.to_numeric(work["close"], errors="coerce").dropna()
    if close.empty:
        return _unavailable(spec)

    ret1 = _return_pct(close, 1)
    ret5 = _return_pct(close, 5)
    ret20 = _return_pct(close, 20)
    ma20_series = close.rolling(20).mean()
    ma20 = (
        None
        if len(ma20_series) < 20 or pd.isna(ma20_series.iloc[-1])
        else float(ma20_series.iloc[-1])
    )
    latest = float(close.iloc[-1])
    distance = None if ma20 is None or ma20 == 0 else 100.0 * (latest / ma20 - 1.0)
    slope = None
    if (
        len(ma20_series) >= 25
        and not pd.isna(ma20_series.iloc[-6])
        and float(ma20_series.iloc[-6]) != 0
    ):
        slope = 100.0 * (
            float(ma20_series.iloc[-1]) / float(ma20_series.iloc[-6]) - 1.0
        )

    if distance is None or slope is None:
        trend = "insufficient_history"
    elif distance > 0 and slope > 0:
        trend = "above_rising_ma20"
    elif distance < 0 and slope < 0:
        trend = "below_falling_ma20"
    else:
        trend = "mixed_ma20"

    stock5 = _stock_return(instrument_frame, 5, as_of)
    stock20 = _stock_return(instrument_frame, 20, as_of)
    rel5 = None if stock5 is None or ret5 is None else stock5 - ret5
    rel20 = None if stock20 is None or ret20 is None else stock20 - ret20
    trade_date = pd.Timestamp(work["trade_date"].iloc[-1]).date().isoformat()
    return BenchmarkContext(
        key=spec.key,
        symbol=spec.symbol,
        name_zh=spec.name_zh,
        available=True,
        as_of_trade_date=trade_date,
        close=latest,
        return_1d_pct=ret1,
        return_5d_pct=ret5,
        return_20d_pct=ret20,
        ma20=ma20,
        distance_to_ma20_pct=distance,
        ma20_slope_5d_pct=slope,
        trend_state=trend,
        instrument_relative_5d_pct=rel5,
        instrument_relative_20d_pct=rel20,
    )


def build_core_market_context(
    instrument_frame: pd.DataFrame,
    *,
    benchmark_root: str | Path,
) -> MarketContext:
    as_of: pd.Timestamp | None = None
    if not instrument_frame.empty and "trade_date" in instrument_frame.columns:
        stamp = pd.to_datetime(
            instrument_frame["trade_date"].iloc[-1], errors="coerce"
        )
        if not pd.isna(stamp):
            as_of = stamp.normalize()

    store = CoreBenchmarkStore(benchmark_root)
    items = tuple(
        _benchmark_context(
            spec,
            store.read(spec.key),
            instrument_frame=instrument_frame,
            as_of=as_of,
        )
        for spec in CORE_BENCHMARKS
    )
    available = sum(item.available for item in items)
    status = (
        "complete"
        if available == len(items)
        else "partial"
        if available
        else "unavailable"
    )
    return MarketContext(
        status=status,
        as_of_trade_date=None if as_of is None else as_of.date().isoformat(),
        benchmarks=items,
    )
