import pandas as pd

from htcn.harmonic.lifecycle import audit_completed_reaction
from htcn.harmonic.models import HarmonicPoint, PatternDirection
from htcn.harmonic.prz import PotentialReversalZone, PRZComponent


def _points_bullish():
    return (
        HarmonicPoint("X", 0, 100.0),
        HarmonicPoint("A", 1, 200.0),
        HarmonicPoint("B", 2, 140.0),
        HarmonicPoint("C", 3, 180.0),
        HarmonicPoint("D", 4, 120.0),
    )


def _prz(low=118.0, high=122.0):
    component = PRZComponent(
        name="test",
        ratio_low=1.0,
        ratio_high=1.0,
        price_low=low,
        price_high=high,
    )
    return PotentialReversalZone(
        price_low=low,
        price_high=high,
        width=high - low,
        component_price_low=low,
        component_price_high=high,
        components=(component,),
    )


def test_bullish_reaction_hits_382_618_then_retests_prz() -> None:
    frame = pd.DataFrame(
        {
            "high": [101, 201, 141, 181, 121, 130, 153, 171, 150, 122],
            "low": [99, 199, 139, 179, 119, 123, 145, 160, 140, 119],
        }
    )
    audit = audit_completed_reaction(
        frame,
        points=_points_bullish(),
        direction=PatternDirection.BULLISH,
        prz=_prz(),
    )
    assert audit.target_382 == 150.56
    assert audit.target_618 == 169.44
    assert audit.bars_to_382 == 2
    assert audit.bars_to_618 == 3
    assert audit.first_prz_exit_bar == 1
    assert audit.secondary_prz_retest_bar == 5
    assert audit.no_prz_retest_first_3_bars is True
    assert audit.no_prz_retest_first_5_bars is False
    assert audit.type_ii_candidate is True
    assert audit.max_favorable_retracement > 0.61


def test_bearish_reaction_targets_move_down_from_d_toward_a() -> None:
    points = (
        HarmonicPoint("X", 0, 200.0),
        HarmonicPoint("A", 1, 100.0),
        HarmonicPoint("B", 2, 160.0),
        HarmonicPoint("C", 3, 120.0),
        HarmonicPoint("D", 4, 180.0),
    )
    frame = pd.DataFrame(
        {
            "high": [201, 101, 161, 121, 181, 176, 150, 132],
            "low": [199, 99, 159, 119, 179, 170, 145, 125],
        }
    )
    audit = audit_completed_reaction(
        frame,
        points=points,
        direction=PatternDirection.BEARISH,
        prz=_prz(178.0, 182.0),
    )
    assert audit.target_382 == 149.44
    assert audit.target_618 == 130.56
    assert audit.bars_to_382 == 2
    assert audit.bars_to_618 == 3
    assert audit.type_ii_candidate is False


def test_no_future_bars_returns_observation_not_failure() -> None:
    frame = pd.DataFrame(
        {
            "high": [101, 201, 141, 181, 121],
            "low": [99, 199, 139, 179, 119],
        }
    )
    audit = audit_completed_reaction(
        frame,
        points=_points_bullish(),
        direction=PatternDirection.BULLISH,
        prz=_prz(),
    )
    assert audit.bars_observed == 0
    assert audit.bars_to_382 is None
    assert audit.bars_to_618 is None
    assert audit.no_prz_retest_first_3_bars is None
    assert audit.type_ii_candidate is False
