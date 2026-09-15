from datetime import date

import pandas as pd

from htcn.data.models import Board, Exchange, Security
from htcn.data.providers.failover import FailoverProvider


class BrokenProvider:
    name = "broken"

    def list_securities(self):
        raise RuntimeError("boom")

    def get_trade_calendar(self, start, end):
        raise RuntimeError("boom")

    def get_daily(self, instrument_id, start, end):
        raise RuntimeError("boom")


class GoodProvider:
    name = "good"

    def list_securities(self):
        return [
            Security(
                instrument_id="SSE.688256",
                symbol="688256",
                exchange=Exchange.SSE,
                name="test",
                board=Board.STAR,
            )
        ]

    def get_trade_calendar(self, start, end):
        return [date(2026, 9, 15)]

    def get_daily(self, instrument_id, start, end):
        return pd.DataFrame(
            [
                {
                    "instrument_id": instrument_id,
                    "trade_date": "2026-09-15",
                    "open": 100.0,
                    "high": 110.0,
                    "low": 99.0,
                    "close": 108.0,
                    "volume": 12345,
                    "source": self.name,
                }
            ]
        )


def test_failover_uses_backup() -> None:
    provider = FailoverProvider(BrokenProvider(), GoodProvider())
    assert provider.list_securities()[0].symbol == "688256"
    assert provider.last_provider == "good"
    assert provider.get_trade_calendar(date(2026, 9, 1), date(2026, 9, 30))
    frame = provider.get_daily("SSE.688256", date(2026, 9, 1), date(2026, 9, 30))
    assert not frame.empty
    assert provider.last_provider == "good"
