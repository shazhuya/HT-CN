from datetime import date

import pandas as pd

from htcn.data.providers.baostock_provider import BaoStockProvider


class FakeResult:
    error_code = "0"
    error_msg = "success"
    fields = [
        "date",
        "code",
        "open",
        "high",
        "low",
        "close",
        "preclose",
        "volume",
        "amount",
        "turn",
        "tradestatus",
        "pctChg",
        "isST",
    ]

    def __init__(self):
        self._done = False

    def next(self):
        if self._done:
            return False
        self._done = True
        return True

    def get_row_data(self):
        return [
            "2026-09-15",
            "sh.600000",
            "10",
            "11",
            "9",
            "10.5",
            "10",
            "1000",
            "10000",
            "1",
            "1",
            "5",
            "0",
        ]


class FakeLogin:
    error_code = "0"
    error_msg = "success"


class FakeBaoStock:
    def __init__(self):
        self.flags = []

    def login(self):
        return FakeLogin()

    def logout(self):
        return None

    def query_history_k_data_plus(self, code, fields, **kwargs):
        self.flags.append(kwargs["adjustflag"])
        return FakeResult()


def provider():
    result = object.__new__(BaoStockProvider)
    result._bs = FakeBaoStock()
    return result


def test_baostock_adjusted_modes_use_documented_flags_and_numeric_schema() -> None:
    p = provider()
    qfq = p.get_daily_adjusted(
        "SSE.600000", date(2026, 9, 1), date(2026, 9, 15), mode="qfq"
    )
    hfq = p.get_daily_adjusted(
        "SSE.600000", date(2026, 9, 1), date(2026, 9, 15), mode="hfq"
    )
    raw = p.get_daily("SSE.600000", date(2026, 9, 1), date(2026, 9, 15))

    assert p._bs.flags == ["2", "1", "3"]
    assert qfq.iloc[0]["source"] == "baostock_qfq"
    assert hfq.iloc[0]["source"] == "baostock_hfq"
    assert raw.iloc[0]["source"] == "baostock"

    for frame in (qfq, hfq, raw):
        assert frame.loc[0, "close"] == 10.5
        assert frame.loc[0, "volume"] == 1000
        assert pd.api.types.is_numeric_dtype(frame["open"])
        assert pd.api.types.is_numeric_dtype(frame["high"])
        assert pd.api.types.is_numeric_dtype(frame["low"])
        assert pd.api.types.is_numeric_dtype(frame["close"])
        assert pd.api.types.is_numeric_dtype(frame["volume"])
        assert pd.api.types.is_datetime64_any_dtype(frame["trade_date"])

    # Exact regression for the live failure: arithmetic must work without a
    # float-vs-string TypeError when the fallback provider supplied the data.
    assert float(qfq.loc[0, "close"] - 10.0) == 0.5
