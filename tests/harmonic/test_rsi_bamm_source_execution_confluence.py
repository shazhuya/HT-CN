from __future__ import annotations

from dataclasses import replace

import pandas as pd

from htcn.harmonic.engine import CompletedMatch
from htcn.harmonic.evaluator import evaluate_xabcd
from htcn.harmonic.models import HarmonicPoint, PatternState
from htcn.harmonic.rsi_bamm import (
    RSIBammDirection,
    RSIBammProfile,
    RSIBammRelation,
    RSIBammSequence,
    RSIBammStructure,
    RSIBammStructureKind,
)
from htcn.harmonic.rsi_bamm_confluence import (
    confirm_rsi_bamm_with_source_execution,
    observe_source_execution_for_match,
)
from htcn.harmonic.rules import CARNEY_RULES


def _live_observable_gartley() -> CompletedMatch:
    points = (
        HarmonicPoint("X", 0, 100.0),
        HarmonicPoint("A", 2, 200.0),
        HarmonicPoint("B", 4, 138.2),
        HarmonicPoint("C", 6, 183.2),
        HarmonicPoint("D", 12, 121.4),
    )
    evaluation = evaluate_xabcd(CARNEY_RULES["gartley"], points)
    assert evaluation.state is PatternState.COMPLETED
    assert evaluation.prz.has_source_prz is True
    return CompletedMatch(
        pattern_id="gartley",
        direction=evaluation.direction,
        state=PatternState.COMPLETED,
        scale=3,
        points=points,
        evaluation=evaluation,
        geometry_score=100.0,
        conflict_key=tuple(point.index for point in points),
    )


def _source_clock_frame(match: CompletedMatch) -> pd.DataFrame:
    assert match.evaluation.prz.source_prz_low is not None
    assert match.evaluation.prz.source_prz_high is not None
    low = float(match.evaluation.prz.source_prz_low)
    high = float(match.evaluation.prz.source_prz_high)
    frame = pd.DataFrame(
        {
            "high": [250.0] * 13,
            "low": [150.0] * 13,
            "close": [180.0] * 13,
        }
    )
    # C at bar 6 with scale 3 becomes observable at bar 9. The first active future
    # bar then tests through the lower source boundary. This is valid PEZ overspill.
    frame.loc[10, "low"] = low - 0.5
    frame.loc[10, "high"] = high + 1.0
    frame.loc[10, "close"] = low + 0.1
    return frame


def _sequence(terminal_price: float) -> RSIBammSequence:
    first = RSIBammStructure(
        direction=RSIBammDirection.BULLISH,
        kind=RSIBammStructureKind.IMPULSIVE,
        enter_bar=1,
        exit_bar=3,
        rsi_extreme_bar=2,
        rsi_extreme_value=24.0,
        price_extreme_bar=2,
        price_extreme_value=terminal_price + 10.0,
        exit_rsi=35.0,
    )
    second = RSIBammStructure(
        direction=RSIBammDirection.BULLISH,
        kind=RSIBammStructureKind.IMPULSIVE,
        enter_bar=9,
        exit_bar=11,
        rsi_extreme_bar=10,
        rsi_extreme_value=27.0,
        price_extreme_bar=10,
        price_extreme_value=terminal_price,
        exit_rsi=35.0,
    )
    return RSIBammSequence(
        direction=RSIBammDirection.BULLISH,
        profile=RSIBammProfile.SIMPLE_DIVERGENCE,
        relation=RSIBammRelation.DIVERGENCE,
        first_structure=first,
        midpoint_bar=5,
        midpoint_rsi=52.0,
        second_structure=second,
        trigger_bar=3,
        trigger_reference_price=terminal_price + 10.0,
        trigger_to_prior_price_extreme_bars=1,
        confirmation_extension_ratio=1.13,
        confirmation_extension_basis="trigger_bar_is_not_prior_price_extreme",
        reaction_anchor_bar=5,
        reaction_anchor_price=terminal_price + 20.0,
        confirmation_projection_price=terminal_price + 0.1,
        price_projection_resolved=True,
        price_projection_tested=True,
    )


def test_completed_match_reconstructs_source_terminal_from_preterminal_projection() -> None:
    match = _live_observable_gartley()
    frame = _source_clock_frame(match)
    audit = observe_source_execution_for_match(frame, match)

    assert audit is not None
    assert audit.signal_bar == 9
    assert audit.terminal_bar == 10
    assert audit.state == "terminal_observed"
    assert audit.terminal_bar != match.points[-1].index
    assert audit.terminal_price is not None
    assert audit.source_prz_low is not None
    assert audit.terminal_price < audit.source_prz_low
    assert audit.pez_low == audit.terminal_price


def test_source_terminal_overspill_can_confirm_bamm_without_relabeling_geometry_d() -> None:
    match = _live_observable_gartley()
    frame = _source_clock_frame(match)
    audit = observe_source_execution_for_match(frame, match)
    assert audit is not None and audit.terminal_price is not None

    result = confirm_rsi_bamm_with_source_execution(
        _sequence(float(audit.terminal_price)),
        match,
        audit,
    )

    assert result.source_confirmed is True
    assert result.status == "source_confirmed"
    assert result.terminal_source == "source_terminal_price_bar"
    assert result.terminal_bar == 10
    assert result.terminal_tests_source_prz is True
    # Overspill is permitted by the PEZ concept; static-interval membership is diagnostic only.
    assert result.terminal_in_source_prz is False
    assert result.terminal_bar != match.points[-1].index


def test_source_clock_unavailable_when_preterminal_pivot_was_not_confirmed_before_d() -> None:
    match = _live_observable_gartley()
    cramped_points = (*match.points[:-2], match.points[-2], replace(match.points[-1], index=8))
    cramped = replace(match, points=cramped_points)

    assert observe_source_execution_for_match(_source_clock_frame(match), cramped) is None
