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
        return pd.DataFrame(
            [
                {
                    "instrument_id": instrument_id,
                    "trade_date": start,
                    "open": 10.0,
                    "high": 11.0,
                    "low": 9.0,
                    "close": 10.5,
                    "volume": 1000.0,
                    "source": f"good_{mode}",
                }
            ]
        )


def test_adjusted_fetch_retries_then_fails_over() -> None:
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
