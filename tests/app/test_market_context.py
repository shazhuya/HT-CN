from __future__ import annotations

import pandas as pd

from htcn.app.market_context import build_core_market_context
from htcn.data.benchmarks import CoreBenchmarkStore


def _frame(start: str, periods: int, step: float) -> pd.DataFrame:
    dates = pd.bdate_range(start, periods=periods)
    close = [100.0 + index * step for index in range(periods)]
    return pd.DataFrame(
        {
            "trade_date": dates,
            "open": close,
            "high": [x + 1 for x in close],
            "low": [x - 1 for x in close],
            "close": close,
            "volume": [1000 + index for index in range(periods)],
        }
    )


def test_market_context_is_fail_safe_without_benchmark_files(tmp_path) -> None:
    context = build_core_market_context(
        _frame("2026-07-01", 50, 0.4),
        benchmark_root=tmp_path,
    )
    assert context.status == "unavailable"
    assert len(context.benchmarks) == 4
    assert all(item.available is False for item in context.benchmarks)
    assert context.mutates_harmonic_identity is False
    assert context.mutates_source_raw_prz is False
    assert context.owns_lifecycle is False


def test_market_context_exposes_raw_trend_and_relative_strength_without_score(
    tmp_path,
) -> None:
    store = CoreBenchmarkStore(tmp_path)
    benchmark = _frame("2026-07-01", 50, 0.2)
    for key in ("star50", "chinext", "csi300", "sse_composite"):
        store.upsert(key, benchmark)

    stock = _frame("2026-07-01", 50, 0.6)
    context = build_core_market_context(stock, benchmark_root=tmp_path)
    assert context.status == "complete"
    first = context.benchmarks[0]
    assert first.trend_state == "above_rising_ma20"
    assert first.return_20d_pct is not None
    assert first.instrument_relative_20d_pct is not None
    assert first.instrument_relative_20d_pct > 0
    payload = context.as_payload()
    assert "score" not in payload
    assert "market_score" not in payload
