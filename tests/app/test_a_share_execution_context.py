from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from htcn.app.a_share_execution_context import (
    SecurityMetadata,
    build_a_share_execution_context,
)
from htcn.data.models import Board


def _frame(*, start: str = "2026-08-03", periods: int = 24) -> pd.DataFrame:
    dates = pd.bdate_range(start=start, periods=periods)
    base = [100.0 + index * 0.6 for index in range(periods)]
    return pd.DataFrame(
        {
            "trade_date": dates,
            "open": [value - 0.3 for value in base],
            "high": [value + 1.0 for value in base],
            "low": [value - 1.0 for value in base],
            "close": base,
            "volume": [1_000_000 + index * 20_000 for index in range(periods)],
        }
    )


def test_star_context_exposes_t_plus_one_atr_and_20pct_board_rule() -> None:
    context = build_a_share_execution_context(
        _frame(),
        instrument_id="SSE.688256",
        metadata=SecurityMetadata(
            board=Board.STAR,
            list_date=date(2020, 7, 20),
            is_st=False,
            source="test",
        ),
    )

    assert context.board == "STAR"
    assert context.t_plus_one is True
    assert context.same_day_sell_after_buy is False
    assert context.earliest_sell_offset_sessions_after_buy == 1
    assert context.nominal_price_limit_pct == pytest.approx(20.0)
    assert context.rule_based_price_limit_pct == pytest.approx(20.0)
    assert context.price_limit_status == "board_rule_profile_resolved_special_events_unresolved"
    assert context.special_event_exceptions_unresolved is True
    assert context.atr is not None and context.atr > 0
    assert context.atr_pct is not None and context.atr_pct > 0
    assert context.latest_range_pct is not None and context.latest_range_pct > 0
    assert context.avg_volume_20 is not None and context.avg_volume_20 > 0
    assert context.volume_ratio_20 is not None and context.volume_ratio_20 > 0
    assert context.mutates_harmonic_identity is False
    assert context.mutates_source_raw_prz is False


def test_main_board_risk_warning_limit_switch_is_date_gated_at_2026_07_06() -> None:
    metadata = SecurityMetadata(
        board=Board.MAIN,
        list_date=date(2010, 1, 1),
        is_st=True,
        source="test",
    )

    before = build_a_share_execution_context(
        _frame(start="2026-05-04"),
        instrument_id="SSE.600000",
        metadata=metadata,
    )
    after = build_a_share_execution_context(
        _frame(start="2026-08-03"),
        instrument_id="SSE.600000",
        metadata=metadata,
    )

    assert before.as_of_trade_date < "2026-07-06"
    assert before.rule_based_price_limit_pct == pytest.approx(5.0)
    assert before.price_limit_status == "historical_main_risk_warning_5pct_before_2026_07_06"

    assert after.as_of_trade_date > "2026-07-06"
    assert after.rule_based_price_limit_pct == pytest.approx(10.0)
    assert after.price_limit_status == "board_rule_profile_resolved_special_events_unresolved"


def test_first_five_listing_sessions_leave_rule_based_limit_unset() -> None:
    frame = _frame(start="2026-09-07", periods=5)
    list_date = pd.Timestamp(frame["trade_date"].iloc[0]).date()
    context = build_a_share_execution_context(
        frame,
        instrument_id="SZSE.300001",
        metadata=SecurityMetadata(
            board=Board.CHINEXT,
            list_date=list_date,
            is_st=False,
            source="test",
        ),
    )

    assert context.ipo_first_five_sessions is True
    assert context.nominal_price_limit_pct == pytest.approx(20.0)
    assert context.rule_based_price_limit_pct is None
    assert context.price_limit_status == "ipo_first_five_sessions_no_price_limit"
    assert context.special_event_exceptions_unresolved is True


def test_missing_security_metadata_never_guesses_st_or_ipo_exception() -> None:
    context = build_a_share_execution_context(
        _frame(),
        instrument_id="SZSE.000001",
        metadata=None,
    )

    assert context.board == "MAIN"
    assert context.metadata_available is False
    assert context.is_st is None
    assert context.ipo_first_five_sessions is None
    assert context.nominal_price_limit_pct == pytest.approx(10.0)
    assert context.rule_based_price_limit_pct is None
    assert context.price_limit_status == "nominal_only_security_metadata_unavailable"
    assert context.special_event_exceptions_unresolved is True
    assert context.mutates_harmonic_identity is False
    assert context.mutates_source_raw_prz is False
