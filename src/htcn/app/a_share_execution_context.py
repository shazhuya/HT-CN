from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
import math

import pandas as pd

from htcn.data.models import Board
from htcn.data.symbols import classify_symbol, symbol_from_instrument_id


MAIN_RISK_WARNING_10_PCT_EFFECTIVE = date(2026, 7, 6)


@dataclass(frozen=True, slots=True)
class SecurityMetadata:
    board: Board
    list_date: date | None
    is_st: bool
    source: str | None = None


@dataclass(frozen=True, slots=True)
class AShareExecutionContext:
    """A-share tradability/volatility context kept outside harmonic identity.

    This layer may explain whether an already-observed source lifecycle event is practical
    to act on, but it must never create, repair, rank as valid, or invalidate a harmonic
    identity or Source Raw PRZ.
    """

    instrument_id: str
    symbol: str
    board: str
    as_of_trade_date: str | None
    metadata_available: bool
    metadata_source: str | None
    list_date: str | None
    is_st: bool | None
    t_plus_one: bool
    same_day_sell_after_buy: bool
    earliest_sell_offset_sessions_after_buy: int
    nominal_price_limit_pct: float | None
    exact_price_limit_pct: float | None
    price_limit_status: str
    ipo_first_five_sessions: bool | None
    special_event_exceptions_unresolved: bool
    atr_period: int
    atr: float | None
    atr_pct: float | None
    latest_range_pct: float | None
    avg_volume_20: float | None
    volume_ratio_20: float | None
    bse_deferred: bool
    mutates_harmonic_identity: bool
    mutates_source_raw_prz: bool

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


def load_security_metadata(
    catalog_path: str | Path,
    instrument_id: str,
) -> SecurityMetadata | None:
    """Load security metadata when the M1 catalog is available; otherwise fail softly.

    DuckDB is imported lazily so pure lifecycle/execution-context tests do not depend on a
    local market database. Missing catalog/table/row is treated as metadata unavailable,
    never as permission to guess ST/IPO exceptions.
    """

    path = Path(catalog_path)
    if not path.exists():
        return None
    try:
        import duckdb

        with duckdb.connect(str(path), read_only=True) as con:
            row = con.execute(
                """
                SELECT board, list_date, is_st, source
                FROM security_master
                WHERE instrument_id = ?
                """,
                [instrument_id],
            ).fetchone()
    except Exception:
        return None
    if row is None:
        return None

    board_raw, list_date_raw, is_st_raw, source_raw = row
    try:
        board = Board(str(board_raw))
    except ValueError:
        board = Board.UNKNOWN

    resolved_list_date: date | None
    if list_date_raw is None:
        resolved_list_date = None
    elif isinstance(list_date_raw, date):
        resolved_list_date = list_date_raw
    else:
        resolved_list_date = pd.Timestamp(list_date_raw).date()

    return SecurityMetadata(
        board=board,
        list_date=resolved_list_date,
        is_st=bool(is_st_raw),
        source=None if source_raw is None else str(source_raw),
    )


def _finite(value: float | int | None) -> float | None:
    if value is None:
        return None
    resolved = float(value)
    return resolved if math.isfinite(resolved) else None


def _wilder_atr(frame: pd.DataFrame, *, period: int) -> float | None:
    if period < 2:
        raise ValueError("ATR period must be >= 2")
    if len(frame) < period:
        return None

    high = pd.to_numeric(frame["high"], errors="coerce")
    low = pd.to_numeric(frame["low"], errors="coerce")
    close = pd.to_numeric(frame["close"], errors="coerce")
    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    values = [float(value) for value in true_range if math.isfinite(float(value))]
    if len(values) < period:
        return None

    atr = sum(values[:period]) / period
    for value in values[period:]:
        atr = ((period - 1) * atr + value) / period
    return float(atr)


def _nominal_price_limit_pct(board: Board) -> float | None:
    if board is Board.MAIN:
        return 10.0
    if board in {Board.STAR, Board.CHINEXT}:
        return 20.0
    return None


def _ipo_first_five_sessions(
    frame: pd.DataFrame,
    *,
    list_date: date | None,
) -> bool | None:
    if list_date is None or "trade_date" not in frame.columns or frame.empty:
        return None
    trade_dates = pd.to_datetime(frame["trade_date"], errors="coerce").dt.date
    listed_sessions = sorted({item for item in trade_dates if item is not None and item >= list_date})
    if not listed_sessions:
        return None
    current = trade_dates.iloc[-1]
    if current is None or current < list_date:
        return None
    try:
        ordinal = listed_sessions.index(current) + 1
    except ValueError:
        return None
    return ordinal <= 5


def _resolve_price_limit(
    *,
    board: Board,
    as_of: date | None,
    metadata: SecurityMetadata | None,
    ipo_first_five: bool | None,
) -> tuple[float | None, float | None, str, bool]:
    nominal = _nominal_price_limit_pct(board)
    if board is Board.BSE:
        return None, None, "bse_deferred", True

    if metadata is None:
        return nominal, None, "nominal_only_security_metadata_unavailable", True

    if ipo_first_five is True and board in {Board.MAIN, Board.STAR, Board.CHINEXT}:
        return nominal, None, "ipo_first_five_sessions_no_price_limit", True

    if as_of is None:
        return nominal, None, "metadata_known_trade_date_unavailable", True

    if metadata.is_st and board is Board.MAIN and as_of < MAIN_RISK_WARNING_10_PCT_EFFECTIVE:
        return nominal, 5.0, "historical_main_risk_warning_5pct_before_2026_07_06", True

    # From 2026-07-06, SSE/SZSE main-board risk-warning stocks use the same 10% band;
    # STAR/ChiNext use their board-level 20% band. We still keep special-event exceptions
    # unresolved because suspension/resumption and other security-specific rules require
    # richer exchange metadata than this daily catalog currently stores.
    return nominal, nominal, "exact_current_board_profile_with_known_listing_metadata", True


def build_a_share_execution_context(
    frame: pd.DataFrame,
    *,
    instrument_id: str,
    metadata: SecurityMetadata | None = None,
    atr_period: int = 14,
) -> AShareExecutionContext:
    required = {"high", "low", "close", "volume"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"A-share execution context missing columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("A-share execution context requires at least one bar")

    symbol = symbol_from_instrument_id(instrument_id)
    _, classified_board = classify_symbol(symbol)
    board = metadata.board if metadata is not None and metadata.board is not Board.UNKNOWN else classified_board

    as_of: date | None = None
    if "trade_date" in frame.columns:
        latest_stamp = pd.to_datetime(frame["trade_date"].iloc[-1], errors="coerce")
        if not pd.isna(latest_stamp):
            as_of = latest_stamp.date()

    ipo_first_five = _ipo_first_five_sessions(
        frame,
        list_date=None if metadata is None else metadata.list_date,
    )
    nominal_limit, exact_limit, price_limit_status, exceptions_unresolved = _resolve_price_limit(
        board=board,
        as_of=as_of,
        metadata=metadata,
        ipo_first_five=ipo_first_five,
    )

    atr = _wilder_atr(frame, period=atr_period)
    latest_close = _finite(frame["close"].iloc[-1])
    atr_pct = (
        None
        if atr is None or latest_close is None or latest_close <= 0
        else 100.0 * atr / latest_close
    )

    latest_high = _finite(frame["high"].iloc[-1])
    latest_low = _finite(frame["low"].iloc[-1])
    if len(frame) >= 2:
        range_denominator = _finite(frame["close"].iloc[-2])
    else:
        range_denominator = latest_close
    latest_range_pct = (
        None
        if latest_high is None
        or latest_low is None
        or range_denominator is None
        or range_denominator <= 0
        else 100.0 * (latest_high - latest_low) / range_denominator
    )

    volumes = pd.to_numeric(frame["volume"], errors="coerce")
    prior = volumes.iloc[max(0, len(volumes) - 21) : max(0, len(volumes) - 1)]
    finite_prior = [float(value) for value in prior if math.isfinite(float(value)) and float(value) >= 0]
    avg_volume_20 = sum(finite_prior) / len(finite_prior) if finite_prior else None
    latest_volume = _finite(volumes.iloc[-1])
    volume_ratio_20 = (
        None
        if avg_volume_20 is None or avg_volume_20 <= 0 or latest_volume is None
        else latest_volume / avg_volume_20
    )

    return AShareExecutionContext(
        instrument_id=instrument_id,
        symbol=symbol,
        board=board.value,
        as_of_trade_date=None if as_of is None else as_of.isoformat(),
        metadata_available=metadata is not None,
        metadata_source=None if metadata is None else metadata.source,
        list_date=(
            None if metadata is None or metadata.list_date is None else metadata.list_date.isoformat()
        ),
        is_st=None if metadata is None else bool(metadata.is_st),
        t_plus_one=True,
        same_day_sell_after_buy=False,
        earliest_sell_offset_sessions_after_buy=1,
        nominal_price_limit_pct=nominal_limit,
        exact_price_limit_pct=exact_limit,
        price_limit_status=price_limit_status,
        ipo_first_five_sessions=ipo_first_five,
        special_event_exceptions_unresolved=exceptions_unresolved,
        atr_period=atr_period,
        atr=atr,
        atr_pct=atr_pct,
        latest_range_pct=latest_range_pct,
        avg_volume_20=avg_volume_20,
        volume_ratio_20=volume_ratio_20,
        bse_deferred=board is Board.BSE,
        mutates_harmonic_identity=False,
        mutates_source_raw_prz=False,
    )
