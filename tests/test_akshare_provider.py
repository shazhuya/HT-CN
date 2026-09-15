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

    def stock_zh_a_spot_em(self):
        return pd.DataFrame(
            [
                {
                    "代码": "688256",
                    "今开": 100.0,
                    "最高": 110.0,
                    "最低": 99.0,
                    "最新价": 108.0,
                    "成交量": 12345,
                    "成交额": 999999.0,
                    "昨收": 100.0,
                    "涨跌幅": 8.0,
                    "换手率": 2.5,
                },
                {
                    "代码": "300820",
                    "今开": 56.0,
                    "最高": 58.0,
                    "最低": 55.5,
                    "最新价": 57.2,
                    "成交量": 4321,
                    "成交额": 333333.0,
                    "昨收": 56.2,
                    "涨跌幅": 1.78,
                    "换手率": 1.2,
                },
            ]
        )

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
    assert normalized.loc[0, "volume"] == 1_234_500.0
    assert normalized.loc[0, "source"] == "akshare"


def test_market_snapshot_translates_two_symbols_in_one_call() -> None:
    frame = provider().get_market_daily_snapshot(date(2026, 9, 15))
    normalized = normalize_daily(frame)
    assert normalized["instrument_id"].tolist() == ["SSE.688256", "SZSE.300820"]
    assert normalized["trade_date"].dt.date.unique().tolist() == [date(2026, 9, 15)]
    assert normalized.loc[0, "volume"] == 1_234_500.0
    assert set(normalized["source"]) == {"akshare_spot"}
