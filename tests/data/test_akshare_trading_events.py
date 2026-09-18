from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pandas as pd

from htcn.data.providers.akshare_provider import AkShareProvider


def test_stock_tfp_em_is_filtered_to_target_session_and_preserves_intraday_state() -> None:
    frame = pd.DataFrame(
        [
            {
                "代码": "600001",
                "停牌时间": "2026-09-17",
                "停牌截止时间": "2026-09-19",
                "停牌期限": "连续停牌",
                "停牌原因": "重大事项",
                "预计复牌时间": "2026-09-21",
            },
            {
                "代码": "300001",
                "停牌时间": "2026-09-18",
                "停牌截止时间": "2026-09-18",
                "停牌期限": "盘中停牌",
                "停牌原因": "交易异常波动",
                "预计复牌时间": None,
            },
            {
                "代码": "000001",
                "停牌时间": "2026-08-01",
                "停牌截止时间": "2026-08-02",
                "停牌期限": "停牌一天",
                "停牌原因": "历史旧记录",
                "预计复牌时间": "2026-08-03",
            },
        ]
    )
    provider = object.__new__(AkShareProvider)
    provider._ak = SimpleNamespace(stock_tfp_em=lambda date: frame)

    records = provider.get_daily_trading_events(date(2026, 9, 18))

    assert [(item.instrument_id, item.trading_status) for item in records] == [
        ("SSE.600001", "suspended"),
        ("SZSE.300001", "intraday_suspended"),
    ]
    assert all(item.resolution_complete is False for item in records)
    assert all(item.no_price_limit is None for item in records)
    assert all(item.price_limit_pct_override is None for item in records)
    assert records[0].source == "akshare_stock_tfp_em"


def test_stock_tfp_em_empty_result_does_not_invent_normal_events() -> None:
    provider = object.__new__(AkShareProvider)
    provider._ak = SimpleNamespace(stock_tfp_em=lambda date: pd.DataFrame())
    assert provider.get_daily_trading_events(date(2026, 9, 18)) == []
