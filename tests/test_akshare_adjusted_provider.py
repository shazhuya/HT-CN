from datetime import date

import pandas as pd

from htcn.data.providers.akshare_provider import AkShareProvider


class FakeAkShareAdjusted:
    def __init__(self) -> None:
        self.adjust_seen = None

    def stock_zh_a_hist(self, **kwargs):
        self.adjust_seen = kwargs["adjust"]
        return pd.DataFrame(
            [
                {
                    "日期": "2026-09-15",
                    "开盘": 50.0,
                    "收盘": 54.0,
                    "最高": 55.0,
                    "最低": 49.0,
                    "成交量": 123,
                }
            ]
        )


def test_get_daily_adjusted_uses_qfq() -> None:
    fake = FakeAkShareAdjusted()
    provider = object.__new__(AkShareProvider)
    provider._ak = fake

    frame = provider.get_daily_adjusted(
        "SSE.688256",
        date(2026, 9, 1),
        date(2026, 9, 15),
        mode="qfq",
    )

    assert fake.adjust_seen == "qfq"
    assert frame.loc[0, "close"] == 54.0
    assert frame.loc[0, "volume"] == 12_300.0
    assert frame.loc[0, "source"] == "akshare_qfq"
