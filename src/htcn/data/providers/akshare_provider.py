from __future__ import annotations

from datetime import date

import pandas as pd

from ..models import Security
from ..symbols import classify_symbol, instrument_id_from_symbol, symbol_from_instrument_id


class AkShareProvider:
    """Free A-share provider backed by AKShare.

    The adapter translates provider-specific columns into HT-CN's stable schema.
    Core code must never depend on AKShare column names directly.

    HT-CN canonical volume unit is shares. AKShare stock_zh_a_hist and the
    Eastmoney all-market snapshot expose volume in hands (1 hand = 100 shares),
    so this adapter converts volume to shares before returning data.
    """

    name = "akshare"

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

        securities: list[Security] = []
        for row in frame[[code_col, name_col]].itertuples(index=False, name=None):
            symbol = str(row[0]).zfill(6)
            try:
                exchange, board = classify_symbol(symbol)
            except ValueError:
                continue
            name = str(row[1]).strip()
            securities.append(
                Security(
                    instrument_id=instrument_id_from_symbol(symbol),
                    symbol=symbol,
                    exchange=exchange,
                    name=name,
                    board=board,
                    is_st="ST" in name.upper(),
                )
            )
        return securities

    def get_trade_calendar(self, start: date, end: date) -> list[date]:
        frame = self._ak.tool_trade_date_hist_sina()
        column = self._column(frame, "trade_date", "日期")
        values = pd.to_datetime(frame[column], errors="raise").dt.date
        return [value for value in values if start <= value <= end]

    def get_market_daily_snapshot(self, trade_date: date) -> pd.DataFrame:
        """Fetch one all-market SSE/SZSE daily snapshot in a single HTTP request."""
        frame = self._ak.stock_zh_a_spot_em()
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
        if frame is None or frame.empty:
            return pd.DataFrame(columns=columns)

        code_col = self._column(frame, "代码", "code", "证券代码")
        mapping = {
            self._column(frame, "今开", "开盘", "open"): "open",
            self._column(frame, "最高", "high"): "high",
            self._column(frame, "最低", "low"): "low",
            self._column(frame, "最新价", "收盘", "close"): "close",
            self._column(frame, "成交量", "volume"): "volume",
        }
        optional = {
            "成交额": "amount",
            "昨收": "pre_close",
            "涨跌幅": "pct_change",
            "换手率": "turnover",
            "amount": "amount",
            "pre_close": "pre_close",
            "pct_change": "pct_change",
            "turnover": "turnover",
        }
        for provider_name, stable_name in optional.items():
            if provider_name in frame.columns:
                mapping[provider_name] = stable_name

        records: list[dict[str, object]] = []
        for raw in frame.to_dict("records"):
            symbol = str(raw.get(code_col, "")).zfill(6)
            try:
                instrument_id = instrument_id_from_symbol(symbol)
            except ValueError:
                continue
            if not instrument_id.startswith(("SSE.", "SZSE.")):
                continue

            record: dict[str, object] = {
                "instrument_id": instrument_id,
                "trade_date": trade_date,
                "source": "akshare_spot",
            }
            valid = True
            for provider_name, stable_name in mapping.items():
                value = raw.get(provider_name)
                numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
                if pd.isna(numeric):
                    if stable_name in {"open", "high", "low", "close", "volume"}:
                        valid = False
                        break
                    continue
                record[stable_name] = float(numeric)
            if not valid:
                continue
            if any(float(record[name]) <= 0 for name in ("open", "high", "low", "close")):
                continue
            record["volume"] = float(record["volume"]) * 100.0
            records.append(record)

        if not records:
            return pd.DataFrame(columns=columns)
        out = pd.DataFrame.from_records(records)
        ordered = [column for column in columns if column in out.columns]
        return out[ordered].copy()

    def _get_daily_with_adjust(
        self,
        instrument_id: str,
        start: date,
        end: date,
        *,
        adjust: str,
        source: str,
    ) -> pd.DataFrame:
        symbol = symbol_from_instrument_id(instrument_id)
        frame = self._ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust=adjust,
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
            "pct_change",
            "turnover",
            "source",
        ]
        if frame is None or frame.empty:
            return pd.DataFrame(columns=columns)

        mapping = {
            self._column(frame, "日期", "date"): "trade_date",
            self._column(frame, "开盘", "open"): "open",
            self._column(frame, "最高", "high"): "high",
            self._column(frame, "最低", "low"): "low",
            self._column(frame, "收盘", "close"): "close",
            self._column(frame, "成交量", "volume"): "volume",
        }
        optional = {
            "成交额": "amount",
            "涨跌幅": "pct_change",
            "换手率": "turnover",
            "amount": "amount",
            "pct_change": "pct_change",
            "turnover": "turnover",
        }
        for provider_name, stable_name in optional.items():
            if provider_name in frame.columns:
                mapping[provider_name] = stable_name

        out = frame.rename(columns=mapping)[list(dict.fromkeys(mapping.values()))].copy()
        out["volume"] = pd.to_numeric(out["volume"], errors="raise") * 100.0
        out.insert(0, "instrument_id", instrument_id)
        out["source"] = source
        return out

    def get_daily(self, instrument_id: str, start: date, end: date) -> pd.DataFrame:
        return self._get_daily_with_adjust(
            instrument_id,
            start,
            end,
            adjust="",
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
        """Return provider-adjusted history for factor derivation.

        HT-CN keeps raw OHLCV as the durable source of truth. This method is used to
        derive an effective adjustment factor by comparing adjusted and raw closes on the
        same trade dates. The adjusted series itself is not treated as the canonical raw
        history.
        """
        if mode not in {"qfq", "hfq"}:
            raise ValueError("mode must be 'qfq' or 'hfq'")
        return self._get_daily_with_adjust(
            instrument_id,
            start,
            end,
            adjust=mode,
            source=f"{self.name}_{mode}",
        )
