from datetime import date

import pandas as pd

from htcn.data.providers.akshare_sina_provider import AkShareSinaProvider
from htcn.data.validation import normalize_daily


class FakeAkShareSina:
    def stock_info_a_code_name(self):
        return pd.DataFrame([{"code": "688256", "name": "寒武纪"}])

    def tool_trade_date_hist_sina(self):
        return pd.DataFrame({"trade_date": ["2026-09-14"]})

    def stock_zh_a_daily(self, **kwargs):
        assert kwargs["symbol"] == "sh688256"
        assert kwargs["adjust"] == ""
        return pd.DataFrame(
            [
                {
                    "date": "2026-09-14",
                    "open": 100.0,
                    "high": 110.0,
                    "low": 99.0,
                    "close": 108.0,
                    "volume": 1_234_500.0,
                    "amount": 99_999_999.0,
                }
            ]
        )


def provider() -> AkShareSinaProvider:
    result = object.__new__(AkShareSinaProvider)
    result._ak = FakeAkShareSina()
    return result


def test_sina_daily_translation_keeps_share_volume() -> None:
    frame = provider().get_daily("SSE.688256", date(2026, 9, 1), date(2026, 9, 14))
    normalized = normalize_daily(frame)
    assert normalized.loc[0, "volume"] == 1_234_500.0
    assert normalized.loc[0, "source"] == "akshare_sina"
