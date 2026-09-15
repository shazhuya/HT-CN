from datetime import date

import pandas as pd

from htcn.data.adjustment import AdjustmentFactorStore, apply_price_factors, derive_price_factors


def _frame(close_values: list[float], *, adjusted: bool = False) -> pd.DataFrame:
    rows = []
    for index, close in enumerate(close_values, start=1):
        rows.append(
            {
                "instrument_id": "SSE.600000",
                "trade_date": date(2026, 9, index),
                "open": close - 1.0,
                "high": close + 1.0,
                "low": close - 2.0,
                "close": close,
                "volume": 1_000_000.0,
                "source": "adjusted" if adjusted else "raw",
            }
        )
    return pd.DataFrame(rows)


def test_derive_and_apply_price_factors() -> None:
    raw = _frame([100.0, 110.0])
    adjusted = _frame([50.0, 110.0], adjusted=True)
    factors = derive_price_factors(raw, adjusted)

    assert factors["price_factor"].round(6).tolist() == [0.5, 1.0]

    out = apply_price_factors(raw, factors)
    assert out["close"].tolist() == [50.0, 110.0]
    assert out["volume"].tolist() == [1_000_000.0, 1_000_000.0]


def test_adjustment_store_round_trip(tmp_path) -> None:
    raw = _frame([100.0, 110.0])
    adjusted = _frame([50.0, 110.0], adjusted=True)
    factors = derive_price_factors(raw, adjusted)

    store = AdjustmentFactorStore(tmp_path)
    path = store.write(factors)
    assert path.exists()
    restored = store.read("SSE.600000")
    assert restored["price_factor"].round(6).tolist() == [0.5, 1.0]
