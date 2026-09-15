from __future__ import annotations

from datetime import date
from typing import Protocol

import pandas as pd

from .models import Security


class MarketDataProvider(Protocol):
    """Provider boundary used by HT-CN.

    Core/data logic must depend on this protocol rather than any specific free data source.
    """

    name: str

    def list_securities(self) -> list[Security]: ...

    def get_trade_calendar(self, start: date, end: date) -> list[date]: ...

    def get_daily(
        self,
        instrument_id: str,
        start: date,
        end: date,
    ) -> pd.DataFrame: ...
