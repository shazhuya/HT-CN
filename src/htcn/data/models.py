from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class Exchange(StrEnum):
    SSE = "SSE"
    SZSE = "SZSE"
    BSE = "BSE"


class Board(StrEnum):
    MAIN = "MAIN"
    CHINEXT = "CHINEXT"
    STAR = "STAR"
    BSE = "BSE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class Security:
    instrument_id: str
    symbol: str
    exchange: Exchange
    name: str
    board: Board = Board.UNKNOWN
    list_date: date | None = None
    delist_date: date | None = None
    is_st: bool = False
    status: str = "listed"


@dataclass(frozen=True, slots=True)
class DailyBar:
    instrument_id: str
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float | None = None
    pre_close: float | None = None
    pct_change: float | None = None
    turnover: float | None = None
    source: str | None = None
