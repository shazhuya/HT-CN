from __future__ import annotations

from datetime import date

import pandas as pd

from ..models import Security
from ..provider import MarketDataProvider


class FailoverProvider:
    """Use a primary provider and transparently fall back on provider failure/empty daily data."""

    name = "failover"

    def __init__(self, primary: MarketDataProvider, fallback: MarketDataProvider) -> None:
        self.primary = primary
        self.fallback = fallback
        self.last_provider: str | None = None

    def list_securities(self) -> list[Security]:
        try:
            result = self.primary.list_securities()
            if result:
                self.last_provider = self.primary.name
                return result
        except Exception:
            pass
        result = self.fallback.list_securities()
        self.last_provider = self.fallback.name
        return result

    def get_trade_calendar(self, start: date, end: date) -> list[date]:
        try:
            result = self.primary.get_trade_calendar(start, end)
            if result:
                self.last_provider = self.primary.name
                return result
        except Exception:
            pass
        result = self.fallback.get_trade_calendar(start, end)
        self.last_provider = self.fallback.name
        return result

    def get_daily(self, instrument_id: str, start: date, end: date) -> pd.DataFrame:
        try:
            result = self.primary.get_daily(instrument_id, start, end)
            if result is not None and not result.empty:
                self.last_provider = self.primary.name
                return result
        except Exception:
            pass
        result = self.fallback.get_daily(instrument_id, start, end)
        self.last_provider = self.fallback.name
        return result
