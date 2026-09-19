from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass

import pandas as pd

from .rsi_bamm import RSIBammDirection, RSIBammSequence, scan_rsi_bamm_frame


@dataclass(frozen=True, slots=True)
class RSIBammLifecycleEvidence:
    """No-lookahead BAMM evidence attached to an already-observed source clock.

    This channel is descriptive confirmation/execution evidence only. It cannot create a
    harmonic match, alter Source Raw PRZ, or backdate evidence before BAMM completion.
    """

    source_clock_bar: int
    observed_through_bar: int
    direction: str
    sequence_count: int
    latest_completion_bar: int | None
    latest_profile: str | None
    latest_projection_tested: bool | None
    source_confirmed: bool
    evidence_available_at_source_clock: bool
    status: str
    mutates_harmonic_identity: bool = False

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


def _completed_by(sequences: Iterable[RSIBammSequence], bar: int) -> list[RSIBammSequence]:
    return [sequence for sequence in sequences if int(sequence.completion_bar) <= int(bar)]


def audit_rsi_bamm_at_source_clock(
    frame: pd.DataFrame,
    *,
    direction: str,
    source_clock_bar: int,
    observed_through_bar: int | None = None,
) -> RSIBammLifecycleEvidence:
    """Observe BAMM only with data available by ``observed_through_bar``.

    ``source_clock_bar`` can be a source-aligned Terminal Price Bar. A BAMM sequence that
    completes later is never backdated onto that bar; it becomes a later evidence event.
    Source-confirmed harmonic confluence remains owned by ``confirm_rsi_bamm_with_match``.
    """
    if direction not in {"bullish", "bearish"}:
        raise ValueError(f"unsupported direction: {direction}")
    if source_clock_bar < 0 or source_clock_bar >= len(frame):
        raise ValueError("source_clock_bar is outside frame")
    through = source_clock_bar if observed_through_bar is None else int(observed_through_bar)
    if through < source_clock_bar:
        raise ValueError("observed_through_bar cannot precede source_clock_bar")
    through = min(through, len(frame) - 1)

    prefix = frame.iloc[: through + 1].reset_index(drop=True)
    enum_direction = RSIBammDirection(direction)
    sequences = scan_rsi_bamm_frame(prefix, direction=enum_direction)
    visible = _completed_by(sequences, through)
    latest = visible[-1] if visible else None

    if latest is None:
        status = "no_completed_rsi_bamm_observed"
        available_at_clock = False
    else:
        available_at_clock = int(latest.completion_bar) <= int(source_clock_bar)
        status = (
            "rsi_bamm_available_at_source_clock"
            if available_at_clock
            else "rsi_bamm_completed_after_source_clock"
        )

    return RSIBammLifecycleEvidence(
        source_clock_bar=int(source_clock_bar),
        observed_through_bar=int(through),
        direction=direction,
        sequence_count=len(visible),
        latest_completion_bar=None if latest is None else int(latest.completion_bar),
        latest_profile=None if latest is None else str(latest.profile.value),
        latest_projection_tested=None if latest is None else bool(latest.price_projection_tested),
        source_confirmed=False,
        evidence_available_at_source_clock=available_at_clock,
        status=status,
        mutates_harmonic_identity=False,
    )
