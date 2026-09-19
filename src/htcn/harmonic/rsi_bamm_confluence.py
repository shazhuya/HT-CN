from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TypeAlias

import pandas as pd

from .abcd import ABCDMatch
from .abcd_source import with_abcd_source_prz
from .engine import CompletedMatch
from .execution import SourceExecutionAudit, observe_source_execution
from .five_zero import FiveZeroMatch
from .models import PatternDirection, PatternState
from .prz import PotentialReversalZone
from .rsi_bamm import (
    RSIBammConfirmation,
    RSIBammDirection,
    RSIBammSequence,
    confirm_rsi_bamm,
)
from .shark import SharkMatch

HarmonicCompletedMatch: TypeAlias = CompletedMatch | ABCDMatch | SharkMatch | FiveZeroMatch

# Volume Two explicitly discusses retracement-pattern precedence before the minimum 1.13
# RSI BAMM extension for Bat/Gartley-type completions. Do not broaden this list by analogy.
RSI_BAMM_113_RETRACEMENT_PRECEDENCE = frozenset({"gartley", "bat"})


@dataclass(frozen=True, slots=True)
class RSIBammHarmonicConfluence:
    """Source-gated binding between one BAMM sequence and one real harmonic match.

    This object is confirmation/execution evidence only. It cannot create or mutate harmonic
    identity, Source Raw PRZ, geometry score, or the underlying RSI BAMM sequence.

    ``terminal_source`` distinguishes the historical geometry-end compatibility adapter from the
    M2.31 Phase-4 Source Terminal Price Bar adapter. Production/lifecycle evidence should use the
    source execution clock.
    """

    sequence: RSIBammSequence
    pattern_id: str
    match_kind: str
    terminal_bar: int | None
    terminal_price: float | None
    source_prz_low: float | None
    source_prz_high: float | None
    direction_aligned: bool
    temporal_alignment: bool
    terminal_in_source_prz: bool
    retracement_precedence_eligible: bool
    confirmation: RSIBammConfirmation | None
    status: str
    terminal_source: str = "geometry_terminal"
    terminal_tests_source_prz: bool = False

    @property
    def source_confirmed(self) -> bool:
        return self.confirmation is not None and self.confirmation.source_confirmed


def _match_kind(match: HarmonicCompletedMatch) -> str:
    if isinstance(match, FiveZeroMatch):
        return "five_zero"
    if isinstance(match, ABCDMatch):
        return "abcd"
    if isinstance(match, SharkMatch):
        return "shark"
    if isinstance(match, CompletedMatch):
        return "xabcd"
    raise TypeError(f"unsupported harmonic match type: {type(match)!r}")


def _source_prz(match: HarmonicCompletedMatch) -> PotentialReversalZone:
    # Standalone AB=CD keeps the M2.28 source resolver separate from its generic projection
    # object. Resolve that source layer here rather than pretending the generic Ideal Core is
    # already a Source Raw PRZ.
    if isinstance(match, ABCDMatch):
        return with_abcd_source_prz(match.evaluation.prz)
    return match.evaluation.prz


def _direction_matches(sequence: RSIBammSequence, direction: PatternDirection) -> bool:
    return sequence.direction.value == direction.value


def _in_closed_interval(value: float, low: float, high: float) -> bool:
    pad = 1e-12 * max(1.0, abs(value), abs(low), abs(high))
    return low - pad <= value <= high + pad


def _same_price(left: float, right: float) -> bool:
    return math.isclose(float(left), float(right), rel_tol=1e-10, abs_tol=1e-10)


def _precedes_113_projection(
    sequence: RSIBammSequence,
    *,
    pattern_id: str,
    match_kind: str,
    terminal_price: float,
) -> bool:
    if match_kind != "xabcd" or pattern_id not in RSI_BAMM_113_RETRACEMENT_PRECEDENCE:
        return False
    if not math.isclose(float(sequence.confirmation_extension_ratio), 1.13, rel_tol=0.0, abs_tol=1e-12):
        return False
    if sequence.price_projection_tested or sequence.confirmation_projection_price is None:
        return False

    target = float(sequence.confirmation_projection_price)
    if sequence.direction is RSIBammDirection.BULLISH:
        return terminal_price > target
    return terminal_price < target


def _blocked(
    sequence: RSIBammSequence,
    match: HarmonicCompletedMatch,
    *,
    status: str,
    source_prz: PotentialReversalZone | None = None,
    direction_aligned: bool = False,
    temporal_alignment: bool = False,
    terminal_in_source_prz: bool = False,
    retracement_precedence_eligible: bool = False,
    terminal_bar: int | None = None,
    terminal_price: float | None = None,
    terminal_source: str = "geometry_terminal",
    terminal_tests_source_prz: bool = False,
) -> RSIBammHarmonicConfluence:
    geometry_terminal = match.points[-1] if match.points else None
    resolved_bar = (
        terminal_bar
        if terminal_bar is not None
        else (None if geometry_terminal is None else int(geometry_terminal.index))
    )
    resolved_price = (
        terminal_price
        if terminal_price is not None
        else (None if geometry_terminal is None else float(geometry_terminal.price))
    )
    return RSIBammHarmonicConfluence(
        sequence=sequence,
        pattern_id=str(match.pattern_id),
        match_kind=_match_kind(match),
        terminal_bar=resolved_bar,
        terminal_price=resolved_price,
        source_prz_low=(
            None if source_prz is None or source_prz.source_prz_low is None else float(source_prz.source_prz_low)
        ),
        source_prz_high=(
            None if source_prz is None or source_prz.source_prz_high is None else float(source_prz.source_prz_high)
        ),
        direction_aligned=direction_aligned,
        temporal_alignment=temporal_alignment,
        terminal_in_source_prz=terminal_in_source_prz,
        retracement_precedence_eligible=retracement_precedence_eligible,
        confirmation=None,
        status=status,
        terminal_source=terminal_source,
        terminal_tests_source_prz=terminal_tests_source_prz,
    )


def observe_source_execution_for_match(
    frame: pd.DataFrame,
    match: HarmonicCompletedMatch,
) -> SourceExecutionAudit | None:
    """Reconstruct the no-lookahead Source Terminal Price Bar for a completed match.

    A completed historical match is only eligible if its pre-terminal pivot had already become
    observable before the historical terminal pivot. The source execution search begins after
    ``pre_terminal.index + scale`` and is capped at the historical terminal-pivot bar so a later,
    unrelated PRZ touch cannot be retroactively attached to the match.

    This helper does not certify the match by itself. It only reconstructs the same source clock
    used by forming projections so BAMM can be evaluated against the observable T-Bar rather than
    a right-confirmed historical D/C pivot.
    """
    if isinstance(match, FiveZeroMatch):
        return None
    if len(match.points) < 2:
        return None

    evaluation_state = getattr(match.evaluation, "state", None)
    if match.state is not PatternState.COMPLETED or evaluation_state is not PatternState.COMPLETED:
        return None

    prz = _source_prz(match)
    if not prz.has_source_prz:
        return None

    pre_terminal = match.points[-2]
    historical_terminal = match.points[-1]
    signal_bar = int(pre_terminal.index) + int(match.scale)
    observation_end = int(historical_terminal.index)
    if signal_bar < 0 or signal_bar >= len(frame) or signal_bar >= observation_end:
        return None

    reaction_anchor_label = "B" if isinstance(match, SharkMatch) else "A"
    reaction_anchor = next(
        (point for point in match.points if point.label == reaction_anchor_label),
        None,
    )
    if reaction_anchor is None:
        return None

    return observe_source_execution(
        frame,
        signal_bar=signal_bar,
        direction=match.direction,
        prz=prz,
        reaction_anchor_price=float(reaction_anchor.price),
        observation_end_bar=observation_end,
    )


def confirm_rsi_bamm_with_match(
    sequence: RSIBammSequence,
    match: HarmonicCompletedMatch,
) -> RSIBammHarmonicConfluence:
    """Compatibility adapter using the historical geometry terminal.

    This preserves M2.31 Phase-3 golden/regression semantics. Production lifecycle integration
    must use :func:`confirm_rsi_bamm_with_source_execution` so the BAMM clock is bound to the
    observable Source Terminal Price Bar instead of silently equating D/C with T-Bar.
    """

    kind = _match_kind(match)
    if isinstance(match, FiveZeroMatch):
        return _blocked(sequence, match, status="blocked_five_zero_production_quarantine")

    evaluation_state = getattr(match.evaluation, "state", None)
    if match.state is not PatternState.COMPLETED or evaluation_state is not PatternState.COMPLETED:
        return _blocked(sequence, match, status="blocked_harmonic_match_not_completed")

    direction_aligned = _direction_matches(sequence, match.direction)
    if not direction_aligned:
        return _blocked(
            sequence,
            match,
            status="blocked_direction_mismatch",
            direction_aligned=False,
        )

    prz = _source_prz(match)
    if not prz.has_source_prz:
        return _blocked(
            sequence,
            match,
            status="blocked_source_prz_unresolved",
            source_prz=prz,
            direction_aligned=True,
        )

    terminal = match.points[-1]
    assert prz.source_prz_low is not None and prz.source_prz_high is not None
    terminal_in_source_prz = _in_closed_interval(
        float(terminal.price),
        float(prz.source_prz_low),
        float(prz.source_prz_high),
    )
    if not terminal_in_source_prz:
        return _blocked(
            sequence,
            match,
            status="blocked_terminal_outside_source_prz",
            source_prz=prz,
            direction_aligned=True,
            terminal_in_source_prz=False,
        )

    second = sequence.second_structure
    temporal_alignment = int(second.enter_bar) <= int(terminal.index) <= int(second.exit_bar)
    if not temporal_alignment:
        return _blocked(
            sequence,
            match,
            status="blocked_terminal_outside_secondary_rsi_retest",
            source_prz=prz,
            direction_aligned=True,
            terminal_in_source_prz=True,
            temporal_alignment=False,
        )

    precedence = _precedes_113_projection(
        sequence,
        pattern_id=str(match.pattern_id),
        match_kind=kind,
        terminal_price=float(terminal.price),
    )
    confirmation = confirm_rsi_bamm(
        sequence,
        harmonic_pattern_completed=True,
        harmonic_pattern_precedes_projection=precedence,
    )
    return RSIBammHarmonicConfluence(
        sequence=sequence,
        pattern_id=str(match.pattern_id),
        match_kind=kind,
        terminal_bar=int(terminal.index),
        terminal_price=float(terminal.price),
        source_prz_low=float(prz.source_prz_low),
        source_prz_high=float(prz.source_prz_high),
        direction_aligned=True,
        temporal_alignment=True,
        terminal_in_source_prz=True,
        retracement_precedence_eligible=precedence,
        confirmation=confirmation,
        status=confirmation.status,
        terminal_source="geometry_terminal",
        terminal_tests_source_prz=True,
    )


def confirm_rsi_bamm_with_source_execution(
    sequence: RSIBammSequence,
    match: HarmonicCompletedMatch,
    audit: SourceExecutionAudit | None,
) -> RSIBammHarmonicConfluence:
    """Phase-4 canonical adapter: bind BAMM to the observable Source Terminal Price Bar.

    The execution audit must be generated from the same frozen Source Raw PRZ. A T-Bar may
    penetrate the terminal harmonic number and create PEZ overspill; therefore the T-Bar extreme
    is *not* required to remain inside the static Raw PRZ interval. What matters is that the audit
    proves a terminal-side test on the same source zone and that the T-Bar occurs during the
    secondary impulsive RSI retest.
    """
    kind = _match_kind(match)
    if isinstance(match, FiveZeroMatch):
        return _blocked(
            sequence,
            match,
            status="blocked_five_zero_production_quarantine",
            terminal_source="source_terminal_price_bar",
        )

    evaluation_state = getattr(match.evaluation, "state", None)
    if match.state is not PatternState.COMPLETED or evaluation_state is not PatternState.COMPLETED:
        return _blocked(
            sequence,
            match,
            status="blocked_harmonic_match_not_completed",
            terminal_source="source_terminal_price_bar",
        )

    direction_aligned = _direction_matches(sequence, match.direction)
    if not direction_aligned:
        return _blocked(
            sequence,
            match,
            status="blocked_direction_mismatch",
            direction_aligned=False,
            terminal_source="source_terminal_price_bar",
        )

    prz = _source_prz(match)
    if not prz.has_source_prz:
        return _blocked(
            sequence,
            match,
            status="blocked_source_prz_unresolved",
            source_prz=prz,
            direction_aligned=True,
            terminal_source="source_terminal_price_bar",
        )

    if audit is None:
        return _blocked(
            sequence,
            match,
            status="blocked_source_execution_clock_unavailable",
            source_prz=prz,
            direction_aligned=True,
            terminal_source="source_terminal_price_bar",
        )

    assert prz.source_prz_low is not None and prz.source_prz_high is not None
    same_zone = (
        audit.source_prz_available
        and audit.source_prz_low is not None
        and audit.source_prz_high is not None
        and _same_price(audit.source_prz_low, float(prz.source_prz_low))
        and _same_price(audit.source_prz_high, float(prz.source_prz_high))
    )
    if not same_zone:
        return _blocked(
            sequence,
            match,
            status="blocked_source_execution_prz_mismatch",
            source_prz=prz,
            direction_aligned=True,
            terminal_source="source_terminal_price_bar",
        )

    if audit.direction is not match.direction:
        return _blocked(
            sequence,
            match,
            status="blocked_source_execution_direction_mismatch",
            source_prz=prz,
            direction_aligned=True,
            terminal_source="source_terminal_price_bar",
        )

    if audit.state != "terminal_observed" or audit.terminal_bar is None or audit.terminal_price is None:
        return _blocked(
            sequence,
            match,
            status="blocked_source_terminal_not_observed",
            source_prz=prz,
            direction_aligned=True,
            terminal_source="source_terminal_price_bar",
        )

    terminal_bar = int(audit.terminal_bar)
    terminal_price = float(audit.terminal_price)
    terminal_in_source_prz = _in_closed_interval(
        terminal_price,
        float(prz.source_prz_low),
        float(prz.source_prz_high),
    )
    terminal_tests_source_prz = (
        terminal_price <= float(prz.source_prz_low)
        if match.direction is PatternDirection.BULLISH
        else terminal_price >= float(prz.source_prz_high)
    )
    if not terminal_tests_source_prz:
        return _blocked(
            sequence,
            match,
            status="blocked_source_terminal_does_not_test_terminal_side",
            source_prz=prz,
            direction_aligned=True,
            terminal_in_source_prz=terminal_in_source_prz,
            terminal_bar=terminal_bar,
            terminal_price=terminal_price,
            terminal_source="source_terminal_price_bar",
            terminal_tests_source_prz=False,
        )

    second = sequence.second_structure
    temporal_alignment = int(second.enter_bar) <= terminal_bar <= int(second.exit_bar)
    if not temporal_alignment:
        return _blocked(
            sequence,
            match,
            status="blocked_source_terminal_outside_secondary_rsi_retest",
            source_prz=prz,
            direction_aligned=True,
            terminal_in_source_prz=terminal_in_source_prz,
            terminal_bar=terminal_bar,
            terminal_price=terminal_price,
            terminal_source="source_terminal_price_bar",
            terminal_tests_source_prz=True,
        )

    precedence = _precedes_113_projection(
        sequence,
        pattern_id=str(match.pattern_id),
        match_kind=kind,
        terminal_price=terminal_price,
    )
    confirmation = confirm_rsi_bamm(
        sequence,
        harmonic_pattern_completed=True,
        harmonic_pattern_precedes_projection=precedence,
    )
    return RSIBammHarmonicConfluence(
        sequence=sequence,
        pattern_id=str(match.pattern_id),
        match_kind=kind,
        terminal_bar=terminal_bar,
        terminal_price=terminal_price,
        source_prz_low=float(prz.source_prz_low),
        source_prz_high=float(prz.source_prz_high),
        direction_aligned=True,
        temporal_alignment=True,
        terminal_in_source_prz=terminal_in_source_prz,
        retracement_precedence_eligible=precedence,
        confirmation=confirmation,
        status=confirmation.status,
        terminal_source="source_terminal_price_bar",
        terminal_tests_source_prz=True,
    )
