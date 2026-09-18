from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from htcn.data.providers.akshare_provider import AkShareProvider


def test_industry_board_and_constituent_normalization() -> None:
    provider = object.__new__(AkShareProvider)
    provider._ak = SimpleNamespace(
        stock_board_industry_name_em=lambda: pd.DataFrame([
            {"板块代码": "BK1036", "板块名称": "半导体"},
            {"板块代码": "BK0420", "板块名称": "通信设备"},
        ]),
        stock_board_industry_cons_em=lambda symbol: pd.DataFrame([
            {"代码": "688256", "名称": "寒武纪"},
            {"代码": "300394", "名称": "天孚通信"},
        ]),
    )

    boards = provider.list_industry_boards()
    assert boards.to_dict("records") == [
        {"sector_code": "BK1036", "sector_name": "半导体", "source": "akshare_eastmoney_industry"},
        {"sector_code": "BK0420", "sector_name": "通信设备", "source": "akshare_eastmoney_industry"},
    ]
    members = provider.get_industry_constituents("BK1036")
    assert members["instrument_id"].tolist() == ["SSE.688256", "SZSE.300394"]
