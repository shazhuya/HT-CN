from __future__ import annotations

from dataclasses import replace

from htcn.harmonic.abcd import ABCDMatch, evaluate_abcd
from htcn.harmonic.engine import CompletedMatch
from htcn.harmonic.evaluator import evaluate_xabcd
from htcn.harmonic.five_zero import FiveZeroMatch, evaluate_five_zero
from htcn.harmonic.models import HarmonicPoint, PatternDirection, PatternState
from htcn.harmonic.prz import PotentialReversalZone
from htcn.harmonic.rsi_bamm import (
    RSIBammDirection,
    RSIBammProfile,
    RSIBammRelation,
    RSIBammSequence,
    RSIBammStructure,
    RSIBammStructureKind,
)
from htcn.harmonic.rsi_bamm_confluence import confirm_rsi_bamm_with_match
from htcn.harmonic.rules import CARNEY_RULES
from htcn.harmonic.shark import SharkMatch, evaluate_shark


def _sequence(
    *,
    direction: RSIBammDirection,
    terminal_price: float,
    target: float,
    tested: bool,
    ratio: float = 1.13,
) -> RSIBammSequence:
    if direction is RSIBammDirection.BULLISH:
        first_price = terminal_price + 10.0
        first_rsi, second_rsi = 24.0, 27.0
        reaction_price = terminal_price + 20.0
    else:
        first_price = terminal_price - 10.0
        first_rsi, second_rsi = 76.0, 73.0
        reaction_price = terminal_price - 20.0

    first = RSIBammStructure(
        direction=direction,
        kind=RSIBammStructureKind.IMPULSIVE,
        enter_bar=1,
        exit_bar=3,
        rsi_extreme_bar=2,
        rsi_extreme_value=first_rsi,
        price_extreme_bar=2,
        price_extreme_value=first_price,
        exit_rsi=35.0 if direction is RSIBammDirection.BULLISH else 65.0,
    )
    second = RSIBammStructure(
        direction=direction,
        kind=RSIBammStructureKind.IMPULSIVE,
        enter_bar=7,
        exit_bar=9,
        rsi_extreme_bar=8,
        rsi_extreme_value=second_rsi,
        price_extreme_bar=8,
        price_extreme_value=terminal_price,
        exit_rsi=35.0 if direction is RSIBammDirection.BULLISH else 65.0,
    )
    return RSIBammSequence(
        direction=direction,
        profile=RSIBammProfile.SIMPLE_DIVERGENCE,
        relation=RSIBammRelation.DIVERGENCE,
        first_structure=first,
        midpoint_bar=5,
        midpoint_rsi=52.0 if direction is RSIBammDirection.BULLISH else 48.0,
        second_structure=second,
        trigger_bar=3,
        trigger_reference_price=first_price,
        trigger_to_prior_price_extreme_bars=0 if ratio == 1.618 else 1,
        confirmation_extension_ratio=ratio,
        confirmation_extension_basis=(
            "trigger_bar_is_prior_price_extreme"
            if ratio == 1.618
            else "trigger_bar_is_not_prior_price_extreme"
        ),
        reaction_anchor_bar=5,
        reaction_anchor_price=reaction_price,
        confirmation_projection_price=target,
        price_projection_resolved=True,
        price_projection_tested=tested,
    )


def _gartley_match() -> CompletedMatch:
    points = (
        HarmonicPoint("X", 0, 100.0),
        HarmonicPoint("A", 2, 200.0),
        HarmonicPoint("B", 4, 138.2),
        HarmonicPoint("C", 6, 183.2),
        HarmonicPoint("D", 8, 121.4),
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


def test_real_xabcd_match_can_source_confirm_bamm() -> None:
    match = _gartley_match()
    sequence = _sequence(
        direction=RSIBammDirection.BULLISH,
        terminal_price=121.4,
        target=122.0,
        tested=True,
    )
    result = confirm_rsi_bamm_with_match(sequence, match)

    assert result.source_confirmed is True
    assert result.status == "source_confirmed"
    assert result.match_kind == "xabcd"
    assert result.terminal_bar == 8
    assert result.direction_aligned is True
    assert result.temporal_alignment is True
    assert result.terminal_in_source_prz is True


def test_direction_mismatch_fails_before_confirmation() -> None:
    match = _gartley_match()
    sequence = _sequence(
        direction=RSIBammDirection.BEARISH,
        terminal_price=121.4,
        target=120.0,
        tested=True,
    )
    result = confirm_rsi_bamm_with_match(sequence, match)

    assert result.source_confirmed is False
    assert result.status == "blocked_direction_mismatch"
    assert result.confirmation is None


def test_terminal_must_occur_inside_secondary_impulsive_retest_window() -> None:
    match = _gartley_match()
    sequence = _sequence(
        direction=RSIBammDirection.BULLISH,
        terminal_price=121.4,
        target=122.0,
        tested=True,
    )
    late_second = replace(
        sequence.second_structure,
        enter_bar=9,
        exit_bar=11,
        rsi_extreme_bar=10,
        price_extreme_bar=10,
    )
    result = confirm_rsi_bamm_with_match(replace(sequence, second_structure=late_second), match)

    assert result.source_confirmed is False
    assert result.status == "blocked_terminal_outside_secondary_rsi_retest"


def test_unresolved_source_prz_fails_closed() -> None:
    match = _gartley_match()
    unresolved_prz = PotentialReversalZone(
        pattern_id=match.evaluation.prz.pattern_id,
        direction=match.evaluation.prz.direction,
        components=match.evaluation.prz.components,
        source_prz_reason="test_unresolved",
    )
    unresolved_eval = replace(match.evaluation, prz=unresolved_prz)
    unresolved_match = replace(match, evaluation=unresolved_eval)
    sequence = _sequence(
        direction=RSIBammDirection.BULLISH,
        terminal_price=121.4,
        target=122.0,
        tested=True,
    )
    result = confirm_rsi_bamm_with_match(sequence, unresolved_match)

    assert result.source_confirmed is False
    assert result.status == "blocked_source_prz_unresolved"


def test_terminal_price_itself_must_be_inside_frozen_source_prz() -> None:
    match = _gartley_match()
    bad_points = (*match.points[:-1], HarmonicPoint("D", 8, 130.0))
    malformed = replace(match, points=bad_points)
    sequence = _sequence(
        direction=RSIBammDirection.BULLISH,
        terminal_price=130.0,
        target=131.0,
        tested=True,
    )
    result = confirm_rsi_bamm_with_match(sequence, malformed)

    assert result.source_confirmed is False
    assert result.status == "blocked_terminal_outside_source_prz"


def test_113_gartley_precedence_is_derived_from_real_match_not_caller_flag() -> None:
    match = _gartley_match()
    sequence = _sequence(
        direction=RSIBammDirection.BULLISH,
        terminal_price=121.4,
        target=120.0,
        tested=False,
        ratio=1.13,
    )
    result = confirm_rsi_bamm_with_match(sequence, match)

    assert result.source_confirmed is True
    assert result.retracement_precedence_eligible is True
    assert result.status == "source_confirmed_retracement_pattern_precedence"


def test_1618_setup_cannot_use_113_retracement_precedence() -> None:
    match = _gartley_match()
    sequence = _sequence(
        direction=RSIBammDirection.BULLISH,
        terminal_price=121.4,
        target=120.0,
        tested=False,
        ratio=1.618,
    )
    result = confirm_rsi_bamm_with_match(sequence, match)

    assert result.source_confirmed is False
    assert result.retracement_precedence_eligible is False
    assert result.status == "harmonic_pattern_without_price_confirmation"


def test_standalone_abcd_uses_m228_source_prz_resolver() -> None:
    points = (
        HarmonicPoint("A", 0, 200.0),
        HarmonicPoint("B", 2, 100.0),
        HarmonicPoint("C", 5, 161.8),
        HarmonicPoint("D", 8, 61.8),
    )
    evaluation = evaluate_abcd(points)
    assert evaluation.state is PatternState.COMPLETED
    # Generic AB=CD evaluation intentionally does not masquerade as source PRZ.
    assert evaluation.prz.has_source_prz is False
    match = ABCDMatch(
        pattern_id="abcd",
        direction=evaluation.direction,
        state=PatternState.COMPLETED,
        scale=3,
        points=points,
        evaluation=evaluation,
        geometry_score=evaluation.geometry_score,
        conflict_key=tuple(point.index for point in points),
    )
    sequence = _sequence(
        direction=RSIBammDirection.BULLISH,
        terminal_price=61.8,
        target=62.0,
        tested=True,
    )
    result = confirm_rsi_bamm_with_match(sequence, match)

    assert result.source_confirmed is True
    assert result.match_kind == "abcd"
    assert result.source_prz_low == result.source_prz_high == 61.8


def test_shark_source_completion_can_confirm_bamm_but_not_113_precedence() -> None:
    points = (
        HarmonicPoint("0", 0, 100.0),
        HarmonicPoint("X", 2, 120.0),
        HarmonicPoint("A", 4, 110.0),
        HarmonicPoint("B", 6, 125.0),
        HarmonicPoint("C", 8, 100.0),
    )
    evaluation = evaluate_shark(points)
    assert evaluation.state is PatternState.COMPLETED
    assert evaluation.prz.has_source_prz is True
    match = SharkMatch(
        pattern_id="shark",
        direction=evaluation.direction,
        state=PatternState.COMPLETED,
        scale=3,
        points=points,
        evaluation=evaluation,
        geometry_score=evaluation.geometry_score,
        conflict_key=tuple(point.index for point in points),
    )
    sequence = _sequence(
        direction=RSIBammDirection.BULLISH,
        terminal_price=100.0,
        target=101.0,
        tested=True,
    )
    result = confirm_rsi_bamm_with_match(sequence, match)

    assert result.source_confirmed is True
    assert result.match_kind == "shark"
    assert result.retracement_precedence_eligible is False


def test_five_zero_remains_blocked_even_when_geometry_is_completed() -> None:
    points = (
        HarmonicPoint("X", 0, 100.0),
        HarmonicPoint("A", 2, 120.0),
        HarmonicPoint("B", 4, 90.0),
        HarmonicPoint("C", 6, 150.0),
        HarmonicPoint("D", 8, 120.0),
    )
    evaluation = evaluate_five_zero(points)
    assert evaluation.state is PatternState.COMPLETED
    match = FiveZeroMatch(
        pattern_id="five_zero",
        direction=evaluation.direction,
        state=PatternState.COMPLETED,
        scale=3,
        points=points,
        evaluation=evaluation,
        geometry_score=evaluation.geometry_score,
        conflict_key=tuple(point.index for point in points),
    )
    sequence = _sequence(
        direction=RSIBammDirection.BULLISH,
        terminal_price=120.0,
        target=121.0,
        tested=True,
    )
    result = confirm_rsi_bamm_with_match(sequence, match)

    assert result.source_confirmed is False
    assert result.status == "blocked_five_zero_production_quarantine"
    assert result.confirmation is None
