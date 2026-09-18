from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd
import pytest

from htcn.app.a_share_execution_context import (
    DailyTradingMetadata,
    SecurityMetadata,
    build_a_share_execution_context,
    load_daily_trading_metadata,
)
from htcn.data.models import Board
from htcn.data.trading_events import (
    SecurityDailyEventRecord,
    ensure_security_daily_event_schema,
    upsert_security_daily_events,
)


def _frame() -> pd.DataFrame:
    dates = pd.bdate_range(start="2026-08-03", periods=24)
    base = [100.0 + index * 0.5 for index in range(len(dates))]
    return pd.DataFrame(
        {
            "trade_date": dates,
            "open": [value - 0.2 for value in base],
            "high": [value + 1.0 for value in base],
            "low": [value - 1.0 for value in base],
            "close": base,
            "volume": [1_000_000 + index * 10_000 for index in range(len(dates))],
        }
    )


def _metadata() -> SecurityMetadata:
    return SecurityMetadata(
        board=Board.STAR,
        list_date=date(2020, 7, 20),
        is_st=False,
        source="security-master-test",
    )


def test_complete_daily_event_can_resolve_explicit_price_limit_override() -> None:
    frame = _frame()
    as_of = pd.Timestamp(frame["trade_date"].iloc[-1]).date()
    context = build_a_share_execution_context(
        frame,
        instrument_id="SSE.688256",
        metadata=_metadata(),
        daily_event=DailyTradingMetadata(
            trade_date=as_of,
            trading_status="special",
            no_price_limit=False,
            price_limit_pct_override=30.0,
            resolution_complete=True,
            source="event-test",
            reason="explicit special-session override",
        ),
    )

    assert context.daily_event_available is True
    assert context.tradable_on_as_of_date is True
    assert context.rule_based_price_limit_pct == pytest.approx(30.0)
    assert context.price_limit_status == "daily_event_price_limit_override"
    assert context.special_event_exceptions_unresolved is False
    assert context.daily_event_resolution_complete is True


def test_complete_suspension_event_marks_session_not_tradable() -> None:
    frame = _frame()
    as_of = pd.Timestamp(frame["trade_date"].iloc[-1]).date()
    context = build_a_share_execution_context(
        frame,
        instrument_id="SSE.688256",
        metadata=_metadata(),
        daily_event=DailyTradingMetadata(
            trade_date=as_of,
            trading_status="suspended",
            no_price_limit=None,
            price_limit_pct_override=None,
            resolution_complete=True,
            source="event-test",
            reason="suspension",
        ),
    )

    assert context.tradable_on_as_of_date is False
    assert context.rule_based_price_limit_pct is None
    assert context.price_limit_status == "daily_event_trading_suspended"
    assert context.special_event_exceptions_unresolved is False


def test_incomplete_event_never_clears_special_event_uncertainty() -> None:
    frame = _frame()
    as_of = pd.Timestamp(frame["trade_date"].iloc[-1]).date()
    context = build_a_share_execution_context(
        frame,
        instrument_id="SSE.688256",
        metadata=_metadata(),
        daily_event=DailyTradingMetadata(
            trade_date=as_of,
            trading_status="normal",
            no_price_limit=False,
            price_limit_pct_override=None,
            resolution_complete=False,
            source="partial-feed",
        ),
    )

    assert context.rule_based_price_limit_pct == pytest.approx(20.0)
    assert context.price_limit_status == "board_rule_profile_resolved_special_events_unresolved"
    assert context.special_event_exceptions_unresolved is True
    assert context.tradable_on_as_of_date is None


def test_event_for_wrong_date_is_not_applied() -> None:
    frame = _frame()
    context = build_a_share_execution_context(
        frame,
        instrument_id="SSE.688256",
        metadata=_metadata(),
        daily_event=DailyTradingMetadata(
            trade_date=date(2026, 1, 2),
            trading_status="suspended",
            no_price_limit=None,
            price_limit_pct_override=None,
            resolution_complete=True,
            source="stale-event",
        ),
    )

    assert context.daily_event_available is False
    assert context.tradable_on_as_of_date is None
    assert context.special_event_exceptions_unresolved is True


def test_optional_daily_event_table_round_trips_through_duckdb(tmp_path) -> None:
    catalog = tmp_path / "catalog.duckdb"
    ensure_security_daily_event_schema(catalog)
    event_date = date(2026, 9, 17)
    count = upsert_security_daily_events(
        catalog,
        [
            SecurityDailyEventRecord(
                instrument_id="SSE.688256",
                trade_date=event_date,
                trading_status="resumed",
                no_price_limit=True,
                price_limit_pct_override=None,
                resolution_complete=True,
                source="fixture",
                reason="resumption session",
            )
        ],
    )
    assert count == 1

    loaded = load_daily_trading_metadata(catalog, "SSE.688256", event_date)
    assert loaded is not None
    assert loaded.trading_status == "resumed"
    assert loaded.no_price_limit is True
    assert loaded.resolution_complete is True
    assert loaded.source == "fixture"

    with duckdb.connect(str(catalog), read_only=True) as con:
        assert con.execute("SELECT COUNT(*) FROM security_daily_event").fetchone()[0] == 1
