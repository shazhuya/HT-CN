from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

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
class DailyTradingMetadata:
    """Optional per-session exchange/event metadata for execution-rule resolution.

    ``resolution_complete`` means the upstream event feed explicitly certifies that the
    session-level trading/price-limit exception state is complete for this instrument/date.
    A missing/incomplete record must never be interpreted as "no exception".
    """

    trade_date: date
    trading_status: str
    no_price_limit: bool | None
    price_limit_pct_override: float | None
    resolution_complete: bool
    source: str | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class AShareExecutionContext:
    """A-share tradability/volatility context kept outside harmonic identity."""

    instrument_id: str
    symbol: str
    board: str
    as_of_trade_date: str | None
    metadata_available: bool
    metadata_source: str | None
    list_date: str | None
    is_st: bool | None
    daily_event_available: bool
    daily_trading_status: str | None
    tradable_on_as_of_date: bool | None
    daily_no_price_limit: bool | None
    daily_price_limit_override_pct: float | None
    daily_event_resolution_complete: bool
    daily_event_source: str | None
    daily_event_reason: str | None
    t_plus_one: bool
    same_day_sell_after_buy: bool
    earliest_sell_offset_sessions_after_buy: int
    nominal_price_limit_pct: float | None
    rule_based_price_limit_pct: float | None
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
    if list_date_raw is None or pd.isna(list_date_raw):
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


def load_daily_trading_metadata(
    catalog_path: str | Path,
    instrument_id: str,
    trade_date: date | None,
) -> DailyTradingMetadata | None:
    """Read optional session-level event metadata without mutating the M1 catalog.

    The table is intentionally optional during the migration. Missing table/row fails soft
    and leaves special-event resolution unresolved. Expected schema is documented and can
    be created by ``htcn.data.trading_events.ensure_security_daily_event_schema``.
    """

    if trade_date is None:
        return None
    path = Path(catalog_path)
    if not path.exists():
        return None
    try:
        import duckdb

        with duckdb.connect(str(path), read_only=True) as con:
            row = con.execute(
                """
                SELECT trading_status,
                       no_price_limit,
                       price_limit_pct_override,
                       resolution_complete,
                       source,
                       reason
                FROM security_daily_event
                WHERE instrument_id = ? AND trade_date = ?
                """,
                [instrument_id, trade_date],
            ).fetchone()
    except Exception:
        return None
    if row is None:
        return None

    status, no_limit, override, complete, source, reason = row
    override_value = None if override is None else float(override)
    if override_value is not None and (not math.isfinite(override_value) or override_value <= 0):
        override_value = None
    return DailyTradingMetadata(
        trade_date=trade_date,
        trading_status=str(status or "unknown").strip().lower(),
        no_price_limit=None if no_limit is None else bool(no_limit),
        price_limit_pct_override=override_value,
        resolution_complete=bool(complete),
        source=None if source is None else str(source),
        reason=None if reason is None else str(reason),
    )


def _finite(value: float | None) -> float | None:
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
    raw_dates = pd.to_datetime(frame["trade_date"], errors="coerce")
    trade_dates = [stamp.date() for stamp in raw_dates if not pd.isna(stamp)]
    if not trade_dates:
        return None
    listed_sessions = sorted({item for item in trade_dates if item >= list_date})
    current = trade_dates[-1]
    if not listed_sessions or current < list_date:
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
    daily_event: DailyTradingMetadata | None,
) -> tuple[float | None, float | None, str, bool]:
    nominal = _nominal_price_limit_pct(board)
    if board is Board.BSE:
        return None, None, "bse_deferred", True

    if daily_event is not None:
        status = daily_event.trading_status
        if status == "suspended":
            return nominal, None, "daily_event_trading_suspended", not daily_event.resolution_complete
        if daily_event.resolution_complete:
            if daily_event.no_price_limit is True:
                return nominal, None, "daily_event_no_price_limit", False
            if daily_event.price_limit_pct_override is not None:
                return (
                    nominal,
                    float(daily_event.price_limit_pct_override),
                    "daily_event_price_limit_override",
                    False,
                )

    if metadata is None:
        return nominal, None, "nominal_only_security_metadata_unavailable", True

    if ipo_first_five is True and board in {Board.MAIN, Board.STAR, Board.CHINEXT}:
        unresolved = daily_event is None or not daily_event.resolution_complete
        return nominal, None, "ipo_first_five_sessions_no_price_limit", unresolved

    if as_of is None:
        return nominal, None, "metadata_known_trade_date_unavailable", True

    if metadata.is_st and board is Board.MAIN and as_of < MAIN_RISK_WARNING_10_PCT_EFFECTIVE:
        unresolved = daily_event is None or not daily_event.resolution_complete
        return nominal, 5.0, "historical_main_risk_warning_5pct_before_2026_07_06", unresolved

    unresolved = daily_event is None or not daily_event.resolution_complete
    return (
        nominal,
        nominal,
        (
            "board_rule_profile_resolved_daily_event_complete"
            if not unresolved
            else "board_rule_profile_resolved_special_events_unresolved"
        ),
        unresolved,
    )


def build_a_share_execution_context(
    frame: pd.DataFrame,
    *,
    instrument_id: str,
    metadata: SecurityMetadata | None = None,
    daily_event: DailyTradingMetadata | None = None,
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

    if daily_event is not None and as_of is not None and daily_event.trade_date != as_of:
        daily_event = None

    ipo_first_five = _ipo_first_five_sessions(
        frame,
        list_date=None if metadata is None else metadata.list_date,
    )
    nominal_limit, rule_based_limit, price_limit_status, exceptions_unresolved = _resolve_price_limit(
        board=board,
        as_of=as_of,
        metadata=metadata,
        ipo_first_five=ipo_first_five,
        daily_event=daily_event,
    )

    atr = _wilder_atr(frame, period=atr_period)
    latest_close = _finite(frame["close"].iloc[-1])
    atr_pct = None if atr is None or latest_close is None or latest_close <= 0 else 100.0 * atr / latest_close

    latest_high = _finite(frame["high"].iloc[-1])
    latest_low = _finite(frame["low"].iloc[-1])
    range_denominator = _finite(frame["close"].iloc[-2]) if len(frame) >= 2 else latest_close
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

    daily_status = None if daily_event is None else daily_event.trading_status
    if daily_status == "suspended":
        tradable = False
    elif daily_event is not None and daily_event.resolution_complete and daily_status in {"normal", "resumed", "special"}:
        tradable = True
    else:
        tradable = None

    return AShareExecutionContext(
        instrument_id=instrument_id,
        symbol=symbol,
        board=board.value,
        as_of_trade_date=None if as_of is None else as_of.isoformat(),
        metadata_available=metadata is not None,
        metadata_source=None if metadata is None else metadata.source,
        list_date=None if metadata is None or metadata.list_date is None else metadata.list_date.isoformat(),
        is_st=None if metadata is None else bool(metadata.is_st),
        daily_event_available=daily_event is not None,
        daily_trading_status=daily_status,
        tradable_on_as_of_date=tradable,
        daily_no_price_limit=None if daily_event is None else daily_event.no_price_limit,
        daily_price_limit_override_pct=None if daily_event is None else daily_event.price_limit_pct_override,
        daily_event_resolution_complete=False if daily_event is None else daily_event.resolution_complete,
        daily_event_source=None if daily_event is None else daily_event.source,
        daily_event_reason=None if daily_event is None else daily_event.reason,
        t_plus_one=True,
        same_day_sell_after_buy=False,
        earliest_sell_offset_sessions_after_buy=1,
        nominal_price_limit_pct=nominal_limit,
        rule_based_price_limit_pct=rule_based_limit,
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
