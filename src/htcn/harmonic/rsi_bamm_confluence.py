from __future__ import annotations

from dataclasses import dataclass
import math
from typing import TypeAlias

from .abcd import ABCDMatch
from .abcd_source import with_abcd_source_prz
from .engine import CompletedMatch
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
# RSI BAMM extension for Bat/Gartley-type completions.  Do not broaden this list by analogy.
RSI_BAMM_113_RETRACEMENT_PRECEDENCE = frozenset({"gartley", "bat"})


@dataclass(frozen=True, slots=True)
class RSIBammHarmonicConfluence:
    """Source-gated binding between one BAMM sequence and one real harmonic match.

    This object is confirmation/execution evidence only.  It cannot create or mutate harmonic
    identity, Source Raw PRZ, geometry score, or the underlying RSI BAMM sequence.
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
    # object.  Resolve that source layer here rather than pretending the generic Ideal Core is
    # already a Source Raw PRZ.
    if isinstance(match, ABCDMatch):
        return with_abcd_source_prz(match.evaluation.prz)
    return match.evaluation.prz


def _direction_matches(sequence: RSIBammSequence, direction: PatternDirection) -> bool:
    return sequence.direction.value == direction.value


def _in_closed_interval(value: float, low: float, high: float) -> bool:
    pad = 1e-12 * max(1.0, abs(value), abs(low), abs(high))
    return low - pad <= value <= high + pad


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
) -> RSIBammHarmonicConfluence:
    terminal = match.points[-1] if match.points else None
    return RSIBammHarmonicConfluence(
        sequence=sequence,
        pattern_id=str(match.pattern_id),
        match_kind=_match_kind(match),
        terminal_bar=None if terminal is None else int(terminal.index),
        terminal_price=None if terminal is None else float(terminal.price),
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
    )


def confirm_rsi_bamm_with_match(
    sequence: RSIBammSequence,
    match: HarmonicCompletedMatch,
) -> RSIBammHarmonicConfluence:
    """Bind a BAMM sequence to an actual source-cleared harmonic completion.

    Hard gates, in order:
    1. 5-0 remains production-quarantined;
    2. the supplied object and its evaluation must both be completed;
    3. BAMM and harmonic directions must agree;
    4. a frozen Source Raw PRZ must be available;
    5. the observed harmonic terminal price must itself lie inside that Source Raw PRZ;
    6. the harmonic terminal bar must occur during the secondary impulsive RSI extreme test.

    Only after those gates pass does the low-level BAMM combiner receive
    ``harmonic_pattern_completed=True``.  Therefore a caller boolean can no longer create a
    source-confirmed claim through the canonical adapter.
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
    )
