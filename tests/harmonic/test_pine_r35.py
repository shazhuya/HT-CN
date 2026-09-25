import pytest

from htcn.harmonic.pine_r35 import (
    PINE_R35_SOURCE_SHA256,
    PineR35Neighborhood,
    neighborhood_pad,
    step_neighborhood,
)


def _step(
    state: PineR35Neighborhood,
    *,
    bar: int,
    low: float,
    high: float,
    open_price: float,
    close: float,
    previous_high: float,
    previous_low: float,
    strict_tested: bool = False,
    live: bool = True,
    direction: int = 1,
) -> bool:
    return step_neighborhood(
        state,
        direction=direction,
        prz_low=100.0,
        prz_high=100.0,
        atr_at_birth=8.0,
        low=low,
        high=high,
        open_price=open_price,
        close=close,
        previous_high=previous_high,
        previous_low=previous_low,
        bar=bar,
        strict_tested=strict_tested,
        live=live,
        window=60,
        away_fraction=0.75,
        tick_size=0.01,
    )


def test_r35_source_digest_and_neighborhood_pad_match_retained_source() -> None:
    assert PINE_R35_SOURCE_SHA256 == (
        "8bc49dc1ac2d0e6b829968aea0e72450c413bb0a0d8c1b1f6eabef57061ad68f"
    )
    assert neighborhood_pad(8.2, 1091.21) == pytest.approx(2.05)
    assert neighborhood_pad(100.0, 10.0) == pytest.approx(0.05)


def test_r35_bullish_neighborhood_first_and_second_reaction_then_stops() -> None:
    state = PineR35Neighborhood(pad=2.0)

    assert _step(
        state,
        bar=10,
        low=101.0,
        high=103.0,
        open_price=102.0,
        close=101.5,
        previous_high=104.0,
        previous_low=100.0,
    )
    assert state.state == 1
    assert state.first_extreme == pytest.approx(101.0)

    assert _step(
        state,
        bar=11,
        low=101.0,
        high=110.0,
        open_price=101.5,
        close=109.0,
        previous_high=103.0,
        previous_low=101.0,
    )
    assert state.state == 2
    assert state.away
    assert state.away_bar == 11
    assert "非严格Type-I" in state.reason

    assert _step(
        state,
        bar=12,
        low=101.5,
        high=104.0,
        open_price=103.0,
        close=102.0,
        previous_high=110.0,
        previous_low=101.0,
    )
    assert state.state == 3
    assert state.second_extreme == pytest.approx(101.5)

    assert _step(
        state,
        bar=13,
        low=101.7,
        high=106.0,
        open_price=102.0,
        close=105.0,
        previous_high=104.0,
        previous_low=101.5,
    )
    assert state.state == 4
    assert state.second_response_price == pytest.approx(105.0)
    assert "严格Type-II尚未成立" in state.reason

    assert _step(
        state,
        bar=14,
        low=101.0,
        high=103.0,
        open_price=102.5,
        close=102.0,
        previous_high=106.0,
        previous_low=101.7,
    )
    assert state.state == 5
    assert "不生成Type-III" in state.reason


def test_r35_strict_test_takes_over_without_rewriting_neighbor_history() -> None:
    state = PineR35Neighborhood(
        pad=2.0,
        state=2,
        born=10,
        first_extreme=101.0,
        first_bar=10,
        response_bar=11,
        response_price=109.0,
        reaction_peak=110.0,
    )

    assert _step(
        state,
        bar=12,
        low=99.0,
        high=102.0,
        open_price=101.0,
        close=100.0,
        previous_high=110.0,
        previous_low=101.0,
        strict_tested=True,
    )
    assert state.state == 6
    assert state.response_bar == 11
    assert "不改写成T-Bar" in state.reason
    payload = state.as_payload(prz_low=100.0, prz_high=100.0)
    assert payload["strict_takeover"] is True
    assert payload["strict_prz_expanded"] is False
    assert payload["creates_tbar"] is False


def test_r35_neighborhood_timeout_and_parent_close_are_terminal() -> None:
    timed = PineR35Neighborhood(pad=2.0, state=1, born=10, first_extreme=101.0)
    assert _step(
        timed,
        bar=70,
        low=105.0,
        high=106.0,
        open_price=105.0,
        close=105.5,
        previous_high=106.0,
        previous_low=104.0,
    )
    assert timed.state == 5
    assert timed.reason == "邻域观察超时"

    closed = PineR35Neighborhood(pad=2.0, state=1, born=10, first_extreme=101.0)
    assert _step(
        closed,
        bar=11,
        low=101.0,
        high=103.0,
        open_price=102.0,
        close=102.0,
        previous_high=103.0,
        previous_low=101.0,
        live=False,
    )
    assert closed.state == 5
    assert closed.reason == "母结构关闭；邻域观察结束"


def test_r35_bearish_neighborhood_is_exact_mirror() -> None:
    state = PineR35Neighborhood(pad=2.0)
    assert _step(
        state,
        bar=20,
        low=97.0,
        high=99.0,
        open_price=98.0,
        close=98.5,
        previous_high=100.0,
        previous_low=96.0,
        direction=-1,
    )
    assert state.state == 1
    assert state.first_extreme == pytest.approx(99.0)

    assert _step(
        state,
        bar=21,
        low=90.0,
        high=99.0,
        open_price=98.5,
        close=91.0,
        previous_high=99.0,
        previous_low=97.0,
        direction=-1,
    )
    assert state.state == 2
    assert state.away


def test_r35_state_never_claims_strict_execution_artifacts() -> None:
    state = PineR35Neighborhood(pad=2.0, state=4, born=1)
    payload = state.as_payload(prz_low=100.0, prz_high=101.0)
    assert payload["zone_low"] == pytest.approx(98.0)
    assert payload["zone_high"] == pytest.approx(103.0)
    assert payload["creates_tbar"] is False
    assert payload["creates_type_i"] is False
    assert payload["creates_type_ii"] is False
    assert payload["creates_trade_plan"] is False
