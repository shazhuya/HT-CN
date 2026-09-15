from datetime import date

import pandas as pd

from htcn.data.adjusted_fetch import fetch_adjusted_history


class BrokenProvider:
    name = "broken"

    def __init__(self) -> None:
        self.calls = 0

    def get_daily_adjusted(self, instrument_id, start, end, *, mode="qfq"):
        self.calls += 1
        raise ConnectionError("remote closed")


class GoodProvider:
    name = "good"

    def __init__(self) -> None:
        self.calls = 0

    def get_daily_adjusted(self, instrument_id, start, end, *, mode="qfq"):
        self.calls += 1
        # Intentionally use strings to emulate providers such as BaoStock.
        return pd.DataFrame(
            [
                {
                    "instrument_id": instrument_id,
                    "trade_date": start.isoformat(),
                    "open": "10.0",
                    "high": "11.0",
                    "low": "9.0",
                    "close": "10.5",
                    "volume": "1000",
                    "source": f"good_{mode}",
                }
            ]
        )


class MalformedProvider:
    name = "malformed"

    def __init__(self) -> None:
        self.calls = 0

    def get_daily_adjusted(self, instrument_id, start, end, *, mode="qfq"):
        self.calls += 1
        return pd.DataFrame(
            [
                {
                    "instrument_id": instrument_id,
                    "trade_date": start,
                    "open": 10.0,
                    "high": 8.0,
                    "low": 9.0,
                    "close": 10.5,
                    "volume": 1000,
                    "source": f"malformed_{mode}",
                }
            ]
        )


def test_adjusted_fetch_retries_then_fails_over_and_normalizes() -> None:
    broken = BrokenProvider()
    good = GoodProvider()
    result = fetch_adjusted_history(
        instrument_id="SSE.600000",
        start=date(2026, 9, 1),
        end=date(2026, 9, 15),
        providers=[broken, good],
        retries_per_provider=1,
        base_delay=0,
    )
    assert broken.calls == 2
    assert good.calls == 1
    assert result.source == "good_qfq"
    assert len(result.frame) == 1
    assert result.attempts == 3
    assert result.frame.loc[0, "close"] == 10.5
    assert float(result.frame.loc[0, "close"] - 10.0) == 0.5
    assert pd.api.types.is_numeric_dtype(result.frame["close"])
    assert pd.api.types.is_datetime64_any_dtype(result.frame["trade_date"])


def test_adjusted_fetch_rejects_malformed_frame_and_uses_next_provider() -> None:
    malformed = MalformedProvider()
    good = GoodProvider()
    result = fetch_adjusted_history(
        instrument_id="SSE.600000",
        start=date(2026, 9, 1),
        end=date(2026, 9, 15),
        providers=[malformed, good],
        retries_per_provider=0,
        base_delay=0,
    )

    assert malformed.calls == 1
    assert good.calls == 1
    assert result.source == "good_qfq"
    assert result.attempts == 2
    assert result.frame.loc[0, "high"] == 11.0
