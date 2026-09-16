import pandas as pd
import pytest

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


def _prz(low=118.0, high=122.0, direction=PatternDirection.BULLISH):
    component = PRZComponent(
        name="test",
        ratio_low=1.0,
        ratio_high=1.0,
        price_low=low,
        price_high=high,
    )
    # This fixture deliberately leaves source_prz_* unresolved. It exercises the
    # retrospective D-clock reaction audit without granting permission to promote a
    # secondary overlap into a Volume-3 Type-II event.
    return PotentialReversalZone(
        pattern_id="test",
        direction=direction,
        components=(component,),
    )


def test_bullish_reaction_hits_382_618_then_reenters_unresolved_zone() -> None:
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
    assert audit.target_382 == pytest.approx(150.56)
    assert audit.target_618 == pytest.approx(169.44)
    assert audit.bars_to_382 == 2
    assert audit.bars_to_618 == 3
    assert audit.first_prz_exit_bar == 1
    assert audit.secondary_prz_retest_bar == 5
    assert audit.no_prz_retest_first_3_bars is True
    assert audit.no_prz_retest_first_5_bars is False
    assert audit.source_prz_available is False
    assert audit.full_prz_retest_bar is None
    assert audit.type_ii_candidate is False
    assert audit.type_ii_evidence_state == "source_prz_unresolved"
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
        prz=_prz(178.0, 182.0, PatternDirection.BEARISH),
    )
    assert audit.target_382 == pytest.approx(149.44)
    assert audit.target_618 == pytest.approx(130.56)
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
