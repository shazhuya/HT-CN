import pandas as pd
import pytest

from htcn.harmonic.execution import observe_source_execution
from htcn.harmonic.models import PatternDirection
from htcn.harmonic.prz import PotentialReversalZone, PRZComponent


def _prz(
    direction: PatternDirection,
    *,
    source_low: float | None = 118.0,
    source_high: float | None = 122.0,
) -> PotentialReversalZone:
    component = PRZComponent(
        name="audit-component",
        ratio_low=1.0,
        ratio_high=1.0,
        price_low=119.5,
        price_high=120.5,
    )
    return PotentialReversalZone(
        pattern_id="test",
        direction=direction,
        components=(component,),
        source_prz_low=source_low,
        source_prz_high=source_high,
    )


def test_missing_source_prz_blocks_execution_clock() -> None:
    frame = pd.DataFrame(
        {
            "high": [140, 130, 124, 121],
            "low": [135, 126, 120, 117],
        }
    )
    audit = observe_source_execution(
        frame,
        signal_bar=1,
        direction=PatternDirection.BULLISH,
        prz=_prz(PatternDirection.BULLISH, source_low=None, source_high=None),
        reaction_anchor_price=150.0,
    )

    assert audit.state == "source_prz_unresolved"
    assert audit.source_prz_available is False
    assert audit.first_prz_entry_bar is None
    assert audit.terminal_bar is None
    assert audit.pez_low is None
    assert audit.target_382 is None


def test_bullish_clock_records_entry_then_terminal_overspill_and_pez() -> None:
    # Projection becomes observable at bar 1. Bar 2 only enters the frozen source PRZ;
    # bar 3 tests the lower/final side and overspills to 116, becoming the T-Bar.
    frame = pd.DataFrame(
        {
            "high": [145, 138, 123, 121, 130],
            "low": [140, 132, 120, 116, 124],
        }
    )
    audit = observe_source_execution(
        frame,
        signal_bar=1,
        direction=PatternDirection.BULLISH,
        prz=_prz(PatternDirection.BULLISH),
        reaction_anchor_price=150.0,
    )

    assert audit.state == "terminal_observed"
    assert audit.first_prz_entry_bar == 2
    assert audit.terminal_bar == 3
    assert audit.terminal_bar > audit.signal_bar
    assert audit.terminal_price == pytest.approx(116.0)
    assert audit.execution_start_bar == 4
    assert audit.pez_low == pytest.approx(116.0)
    assert audit.pez_high == pytest.approx(122.0)
    assert audit.target_382 == pytest.approx(116.0 + 0.382 * 34.0)
    assert audit.target_618 == pytest.approx(116.0 + 0.618 * 34.0)


def test_bearish_clock_uses_upper_terminal_side_and_pez() -> None:
    frame = pd.DataFrame(
        {
            "high": [95, 105, 119, 125, 116],
            "low": [90, 100, 116, 120, 110],
        }
    )
    audit = observe_source_execution(
        frame,
        signal_bar=1,
        direction=PatternDirection.BEARISH,
        prz=_prz(PatternDirection.BEARISH),
        reaction_anchor_price=90.0,
    )

    assert audit.state == "terminal_observed"
    assert audit.first_prz_entry_bar == 2
    assert audit.terminal_bar == 3
    assert audit.terminal_price == pytest.approx(125.0)
    assert audit.execution_start_bar == 4
    assert audit.pez_low == pytest.approx(118.0)
    assert audit.pez_high == pytest.approx(125.0)
    assert audit.target_382 == pytest.approx(125.0 - 0.382 * 35.0)
    assert audit.target_618 == pytest.approx(125.0 - 0.618 * 35.0)


def test_same_bar_touch_is_not_retroactively_promoted() -> None:
    # The signal bar itself already reaches the terminal side, but execution observation
    # starts strictly at signal+1. The next bar has not reached the source PRZ at all.
    frame = pd.DataFrame(
        {
            "high": [140, 121, 130, 131],
            "low": [135, 117, 125, 126],
        }
    )
    audit = observe_source_execution(
        frame,
        signal_bar=1,
        direction=PatternDirection.BULLISH,
        prz=_prz(PatternDirection.BULLISH),
        reaction_anchor_price=150.0,
    )

    assert audit.state == "awaiting_prz_entry"
    assert audit.first_prz_entry_bar is None
    assert audit.terminal_bar is None


def test_retirement_bar_prevents_later_terminal_claim() -> None:
    frame = pd.DataFrame(
        {
            "high": [145, 138, 123, 124, 121],
            "low": [140, 132, 120, 119, 116],
        }
    )
    audit = observe_source_execution(
        frame,
        signal_bar=1,
        observation_end_bar=3,
        direction=PatternDirection.BULLISH,
        prz=_prz(PatternDirection.BULLISH),
        reaction_anchor_price=150.0,
    )

    assert audit.state == "prz_entered_waiting_terminal"
    assert audit.first_prz_entry_bar == 2
    assert audit.terminal_bar is None
