from datetime import date

import pandas as pd

from htcn.data.providers.akshare_provider import AkShareProvider
from htcn.data.validation import normalize_daily


class FakeAkShare:
    def stock_info_a_code_name(self):
        return pd.DataFrame(
            [
                {"code": "688256", "name": "寒武纪"},
                {"code": "300820", "name": "英杰电气"},
            ]
        )

    def tool_trade_date_hist_sina(self):
        return pd.DataFrame({"trade_date": ["2026-09-14", "2026-09-15"]})

    def stock_zh_a_hist(self, **kwargs):
        assert kwargs["symbol"] == "688256"
        assert kwargs["adjust"] == ""
        return pd.DataFrame(
            [
                {
                    "日期": "2026-09-15",
                    "开盘": 100.0,
                    "收盘": 108.0,
                    "最高": 110.0,
                    "最低": 99.0,
                    "成交量": 12345,
                    "成交额": 999999.0,
                    "涨跌幅": 8.0,
                    "换手率": 2.5,
                }
            ]
        )


def provider() -> AkShareProvider:
    result = object.__new__(AkShareProvider)
    result._ak = FakeAkShare()
    return result


def test_security_master_translation() -> None:
    securities = provider().list_securities()
    assert [item.instrument_id for item in securities] == ["SSE.688256", "SZSE.300820"]


def test_calendar_translation() -> None:
    dates = provider().get_trade_calendar(date(2026, 9, 14), date(2026, 9, 15))
    assert dates == [date(2026, 9, 14), date(2026, 9, 15)]


def test_daily_translation_matches_htcn_schema() -> None:
    frame = provider().get_daily("SSE.688256", date(2026, 9, 1), date(2026, 9, 15))
    normalized = normalize_daily(frame)
    assert len(normalized) == 1
    assert normalized.loc[0, "close"] == 108.0
    assert normalized.loc[0, "source"] == "akshare"
