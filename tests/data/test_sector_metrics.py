from __future__ import annotations

import pandas as pd
import pytest

from htcn.data.sectors import _metrics


def test_sector_metrics_fall_back_to_close_when_pct_change_is_missing() -> None:
    trade_days = list(pd.bdate_range("2026-08-03", periods=25))
    bars = pd.DataFrame({
        "trade_date": trade_days,
        "close": [100.0 + index for index in range(25)],
        "volume": [1000.0] * 25,
    })
    metrics = _metrics(bars, trade_days=trade_days, list_date=None)
    assert metrics["return_5d"] == pytest.approx(100.0 * (124.0 / 119.0 - 1.0))
    assert metrics["return_20d"] == pytest.approx(100.0 * (124.0 / 104.0 - 1.0))
    assert metrics["above_ma20"] == 1.0


def test_sector_metrics_treat_missing_session_for_listed_stock_as_flat_when_pct_available() -> None:
    trade_days = list(pd.bdate_range("2026-08-03", periods=25))
    bars = pd.DataFrame({
        "trade_date": [day for index, day in enumerate(trade_days) if index != 23],
        "close": [100.0 + index for index in range(24)],
        "volume": [1000.0] * 24,
        "pct_change": [1.0] * 24,
    })
    metrics = _metrics(bars, trade_days=trade_days, list_date=None)
    assert metrics["return_1d"] == pytest.approx(1.0)
    expected_5d = 100.0 * ((1.01 ** 4) - 1.0)
    assert metrics["return_5d"] == pytest.approx(expected_5d)
