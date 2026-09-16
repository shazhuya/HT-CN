import math

import pandas as pd

from htcn.harmonic.indicators import wilder_rsi


def test_wilder_rsi_monotonic_gain_reaches_100() -> None:
    series = pd.Series([1, 2, 3, 4, 5, 6, 7, 8], dtype=float)
    rsi = wilder_rsi(series, period=3)
    assert rsi.iloc[:3].isna().all()
    assert all(math.isclose(float(value), 100.0) for value in rsi.iloc[3:])


def test_wilder_rsi_monotonic_loss_reaches_zero() -> None:
    series = pd.Series([8, 7, 6, 5, 4, 3, 2, 1], dtype=float)
    rsi = wilder_rsi(series, period=3)
    assert rsi.iloc[:3].isna().all()
    assert all(math.isclose(float(value), 0.0) for value in rsi.iloc[3:])


def test_wilder_rsi_flat_seed_is_neutral() -> None:
    series = pd.Series([5, 5, 5, 5, 5, 5], dtype=float)
    rsi = wilder_rsi(series, period=3)
    assert math.isclose(float(rsi.iloc[3]), 50.0)


def test_wilder_rsi_rejects_invalid_period() -> None:
    try:
        wilder_rsi(pd.Series([1.0, 2.0, 3.0]), period=1)
    except ValueError as exc:
        assert "period" in str(exc).lower()
    else:
        raise AssertionError("expected ValueError")
