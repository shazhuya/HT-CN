from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from htcn.data.providers.akshare_provider import AkShareProvider


def test_concept_board_and_constituent_normalization() -> None:
    provider = object.__new__(AkShareProvider)
    provider._ak = SimpleNamespace(
        stock_board_concept_name_em=lambda: pd.DataFrame([
            {"板块代码": "BK0980", "板块名称": "CPO概念"},
            {"板块代码": "BK1122", "板块名称": "国产芯片"},
        ]),
        stock_board_concept_cons_em=lambda symbol: pd.DataFrame([
            {"代码": "300394", "名称": "天孚通信"},
            {"代码": "688256", "名称": "寒武纪"},
        ]),
    )
    boards = provider.list_concept_boards()
    assert boards["sector_name"].tolist() == ["CPO概念", "国产芯片"]
    members = provider.get_concept_constituents("BK0980")
    assert members["instrument_id"].tolist() == ["SZSE.300394", "SSE.688256"]
