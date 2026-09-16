from __future__ import annotations

import pandas as pd

from htcn.harmonic.models import Pivot, PivotKind
from htcn.research.walk_forward import walk_forward_forming_signals


def _frame(*, stale_on_signal: bool = False) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=15, freq="D")
    high = [161.0] * 15
    low = [159.0] * 15
    close = [160.0] * 15

    # The projected bullish Bat PRZ is approximately 111.40-111.50.
    if stale_on_signal:
        high[8], low[8], close[8] = 112.0, 111.4, 111.6
    high[9], low[9], close[9] = 141.0, 139.0, 140.0
    high[10], low[10], close[10] = 112.0, 111.35, 111.6
    high[11], low[11], close[11] = 120.0, 114.0, 118.0
    return pd.DataFrame(
        {
            "trade_date": dates,
            "open": close,
            "high": high,
            "low": low,
            "close": close,
            "volume": [1_000.0] * 15,
        }
    )


def _bat_events(scale: int) -> list[Pivot]:
    return [
        Pivot(index=1, price=100.0, kind=PivotKind.LOW, scale=scale, confirmed_at=2),
        Pivot(index=3, price=200.0, kind=PivotKind.HIGH, scale=scale, confirmed_at=4),
        Pivot(index=5, price=150.0, kind=PivotKind.LOW, scale=scale, confirmed_at=6),
        Pivot(index=7, price=175.0, kind=PivotKind.HIGH, scale=scale, confirmed_at=8),
        Pivot(index=10, price=111.4, kind=PivotKind.LOW, scale=scale, confirmed_at=11),
    ]


def test_forming_bat_is_emitted_at_c_confirmation_and_completed_later(monkeypatch) -> None:
    def fake_events(frame, *, left, right, scale=None):
        assert left == right == scale == 1
        return _bat_events(1)

    monkeypatch.setattr("htcn.research.walk_forward.detect_pivot_events", fake_events)
    records = walk_forward_forming_signals(_frame(), scales=(1,), horizon=6)
    bat = next(row for row in records if row["pattern_id"] == "bat")

    assert bat["signal_bar"] == 8
    assert bat["terminal_pivot_bar"] == 7
    assert bat["confirmation_lag_bars"] == 1
    assert bat["outcome"]["pre_signal_prz_touch_bar"] is None
    assert bat["outcome"]["bars_to_first_future_prz_touch"] == 2
    assert bat["outcome"]["bars_to_completion_terminal"] == 2
    assert bat["outcome"]["bars_to_completion_confirmation"] == 3
    assert bat["outcome"]["outcome_class"] == "engine_completed_within_horizon"
    assert bat["anti_leakage"]["signal_uses_only_confirmed_pivots"] is True


def test_prz_touched_before_signal_is_explicitly_marked_late(monkeypatch) -> None:
    def fake_events(frame, *, left, right, scale=None):
        return _bat_events(1)

    monkeypatch.setattr("htcn.research.walk_forward.detect_pivot_events", fake_events)
    records = walk_forward_forming_signals(_frame(stale_on_signal=True), scales=(1,), horizon=6)
    bat = next(row for row in records if row["pattern_id"] == "bat")

    assert bat["outcome"]["pre_signal_prz_touch_bar"] == 8
    assert bat["outcome"]["outcome_class"] == "late_signal_prz_already_touched"
