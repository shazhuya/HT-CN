from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from typing import Iterator

import pandas as pd

from ..models import Security
from ..symbols import classify_symbol, instrument_id_from_symbol, symbol_from_instrument_id


class BaoStockProvider:
    """Free fallback provider backed by BaoStock."""

    name = "baostock"

    def __init__(self) -> None:
        import baostock as bs

        self._bs = bs

    @contextmanager
    def _session(self) -> Iterator[None]:
        result = self._bs.login()
        if getattr(result, "error_code", "0") != "0":
            raise RuntimeError(f"BaoStock login failed: {result.error_code} {result.error_msg}")
        try:
            yield
        finally:
            self._bs.logout()

    @staticmethod
    def _result_frame(result: object) -> pd.DataFrame:
        fields = list(getattr(result, "fields", []))
        rows: list[list[str]] = []
        while getattr(result, "error_code", "0") == "0" and result.next():
            rows.append(result.get_row_data())
        if getattr(result, "error_code", "0") != "0":
            raise RuntimeError(
                f"BaoStock query failed: {result.error_code} {getattr(result, 'error_msg', '')}"
            )
        return pd.DataFrame(rows, columns=fields)

    @staticmethod
    def _provider_code(instrument_id: str) -> str:
        symbol = symbol_from_instrument_id(instrument_id)
        prefix = instrument_id.split(".", 1)[0]
        if prefix == "SSE":
            return f"sh.{symbol}"
        if prefix == "SZSE":
            return f"sz.{symbol}"
        if prefix == "BSE":
            return f"bj.{symbol}"
        raise ValueError(f"unsupported instrument_id: {instrument_id!r}")

    def list_securities(self) -> list[Security]:
        with self._session():
            frame = self._result_frame(self._bs.query_stock_basic())

        securities: list[Security] = []
        for row in frame.to_dict("records"):
            provider_code = str(row.get("code", ""))
            if "." not in provider_code:
                continue
            symbol = provider_code.split(".", 1)[1]
            try:
                exchange, board = classify_symbol(symbol)
            except ValueError:
                continue

            stock_type = str(row.get("type", "1"))
            if stock_type not in {"", "1"}:
                continue
            name = str(row.get("code_name", row.get("name", ""))).strip()
            list_date = pd.to_datetime(row.get("ipoDate"), errors="coerce")
            out_date = pd.to_datetime(row.get("outDate"), errors="coerce")
            securities.append(
                Security(
                    instrument_id=instrument_id_from_symbol(symbol),
                    symbol=symbol,
                    exchange=exchange,
                    name=name,
                    board=board,
                    list_date=None if pd.isna(list_date) else list_date.date(),
                    delist_date=None if pd.isna(out_date) else out_date.date(),
                    is_st="ST" in name.upper(),
                    status="listed" if str(row.get("status", "1")) in {"", "1"} else "delisted",
                )
            )
        return securities

    def get_trade_calendar(self, start: date, end: date) -> list[date]:
        with self._session():
            frame = self._result_frame(
                self._bs.query_trade_dates(
                    start_date=start.isoformat(),
                    end_date=end.isoformat(),
                )
            )
        if frame.empty:
            return []
        frame = frame[frame["is_trading_day"].astype(str) == "1"]
        return pd.to_datetime(frame["calendar_date"], errors="raise").dt.date.tolist()

    def _get_daily_with_adjustflag(
        self,
        instrument_id: str,
        start: date,
        end: date,
        *,
        adjustflag: str,
        source: str,
    ) -> pd.DataFrame:
        fields = (
            "date,code,open,high,low,close,preclose,volume,amount,turn,"
            "tradestatus,pctChg,isST"
        )
        with self._session():
            frame = self._result_frame(
                self._bs.query_history_k_data_plus(
                    self._provider_code(instrument_id),
                    fields,
                    start_date=start.isoformat(),
                    end_date=end.isoformat(),
                    frequency="d",
                    adjustflag=adjustflag,
                )
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
            "pre_close",
            "pct_change",
            "turnover",
            "source",
        ]
        if frame.empty:
            return pd.DataFrame(columns=columns)

        if "tradestatus" in frame.columns:
            frame = frame[frame["tradestatus"].astype(str) == "1"].copy()

        out = frame.rename(
            columns={
                "date": "trade_date",
                "preclose": "pre_close",
                "pctChg": "pct_change",
                "turn": "turnover",
            }
        )
        keep = [
            "trade_date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "amount",
            "pre_close",
            "pct_change",
            "turnover",
        ]
        out = out[keep].copy()
        out.insert(0, "instrument_id", instrument_id)
        out["source"] = source
        return out

    def get_daily(self, instrument_id: str, start: date, end: date) -> pd.DataFrame:
        # BaoStock: 3=unadjusted, 2=QFQ, 1=HFQ.
        return self._get_daily_with_adjustflag(
            instrument_id,
            start,
            end,
            adjustflag="3",
            source=self.name,
        )

    def get_daily_adjusted(
        self,
        instrument_id: str,
        start: date,
        end: date,
        *,
        mode: str = "qfq",
    ) -> pd.DataFrame:
        if mode not in {"qfq", "hfq"}:
            raise ValueError("mode must be 'qfq' or 'hfq'")
        adjustflag = "2" if mode == "qfq" else "1"
        return self._get_daily_with_adjustflag(
            instrument_id,
            start,
            end,
            adjustflag=adjustflag,
            source=f"{self.name}_{mode}",
        )
