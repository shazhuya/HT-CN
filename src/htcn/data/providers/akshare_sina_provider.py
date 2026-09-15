from __future__ import annotations

from datetime import date

import pandas as pd

from ..models import Security
from ..symbols import classify_symbol, instrument_id_from_symbol, symbol_from_instrument_id


class AkShareSinaProvider:
    """Secondary free A-share feed using AKShare's Sina daily endpoint.

    This is intentionally separate from AkShareProvider, which uses another upstream
    daily endpoint. Keeping them separate lets HT-CN audit upstream disagreement.
    """

    name = "akshare_sina"

    def __init__(self) -> None:
        import akshare as ak

        self._ak = ak

    @staticmethod
    def _column(frame: pd.DataFrame, *candidates: str) -> str:
        for candidate in candidates:
            if candidate in frame.columns:
                return candidate
        raise KeyError(f"none of columns {candidates!r} found in {list(frame.columns)!r}")

    def list_securities(self) -> list[Security]:
        frame = self._ak.stock_info_a_code_name()
        code_col = self._column(frame, "code", "代码", "证券代码")
        name_col = self._column(frame, "name", "名称", "证券简称")
        result: list[Security] = []
        for code, raw_name in frame[[code_col, name_col]].itertuples(index=False, name=None):
            symbol = str(code).zfill(6)
            try:
                exchange, board = classify_symbol(symbol)
            except ValueError:
                continue
            name = str(raw_name).strip()
            result.append(
                Security(
                    instrument_id=instrument_id_from_symbol(symbol),
                    symbol=symbol,
                    exchange=exchange,
                    name=name,
                    board=board,
                    is_st="ST" in name.upper(),
                )
            )
        return result

    def get_trade_calendar(self, start: date, end: date) -> list[date]:
        frame = self._ak.tool_trade_date_hist_sina()
        column = self._column(frame, "trade_date", "日期")
        values = pd.to_datetime(frame[column], errors="raise").dt.date
        return [value for value in values if start <= value <= end]

    @staticmethod
    def _provider_symbol(instrument_id: str) -> str:
        symbol = symbol_from_instrument_id(instrument_id)
        exchange = instrument_id.split(".", 1)[0]
        if exchange == "SSE":
            return f"sh{symbol}"
        if exchange == "SZSE":
            return f"sz{symbol}"
        raise ValueError(f"Sina daily endpoint unsupported for {instrument_id!r}")

    def get_daily(self, instrument_id: str, start: date, end: date) -> pd.DataFrame:
        frame = self._ak.stock_zh_a_daily(
            symbol=self._provider_symbol(instrument_id),
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust="",
        )
        columns = [
            "instrument_id",
            "trade_date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "amount",
            "source",
        ]
        if frame is None or frame.empty:
            return pd.DataFrame(columns=columns)

        mapping = {
            self._column(frame, "date", "日期"): "trade_date",
            self._column(frame, "open", "开盘"): "open",
            self._column(frame, "high", "最高"): "high",
            self._column(frame, "low", "最低"): "low",
            self._column(frame, "close", "收盘"): "close",
            self._column(frame, "volume", "成交量"): "volume",
        }
        if "amount" in frame.columns:
            mapping["amount"] = "amount"
        elif "成交额" in frame.columns:
            mapping["成交额"] = "amount"

        out = frame.rename(columns=mapping)[list(dict.fromkeys(mapping.values()))].copy()
        out.insert(0, "instrument_id", instrument_id)
        out["source"] = self.name
        return out
