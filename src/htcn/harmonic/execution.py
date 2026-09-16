from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from .models import PatternDirection
from .prz import PotentialReversalZone


@dataclass(frozen=True, slots=True)
class SourceExecutionAudit:
    """No-lookahead execution-clock observation for one already-observable projection.

    The projection must exist at ``signal_bar``. Observation starts strictly after that
    bar. The audit refuses to substitute an HT-CN ideal core or component envelope when
    the source Raw PRZ has not been frozen.

    This object is intentionally independent from a right-confirmed historical D Pivot.
    It represents the Volume-3 execution clock:

    forming signal -> source PRZ entry -> Terminal Price Bar -> PEZ -> T-Bar+1.
    """

    signal_bar: int
    direction: PatternDirection
    state: str
    source_prz_available: bool
    source_prz_low: float | None
    source_prz_high: float | None
    first_prz_entry_bar: int | None
    terminal_bar: int | None
    terminal_price: float | None
    execution_start_bar: int | None
    pez_low: float | None
    pez_high: float | None
    target_382: float | None
    target_618: float | None

    def as_payload(self) -> dict[str, object]:
        payload = asdict(self)
        payload["direction"] = self.direction.value
        return payload


def _validate_frame(frame: pd.DataFrame, signal_bar: int) -> None:
    missing = {"high", "low"}.difference(frame.columns)
    if missing:
        raise ValueError(f"source execution audit missing columns: {sorted(missing)}")
    if signal_bar < 0 or signal_bar >= len(frame):
        raise ValueError("signal_bar is outside the supplied frame")


def _reaction_targets(
    *,
    terminal_price: float,
    reaction_anchor_price: float,
    direction: PatternDirection,
) -> tuple[float, float]:
    span = abs(float(reaction_anchor_price) - float(terminal_price))
    if span <= 0:
        raise ValueError("reaction anchor and Terminal Price Bar must define a positive span")
    sign = 1.0 if direction is PatternDirection.BULLISH else -1.0
    return (
        float(terminal_price) + sign * 0.382 * span,
        float(terminal_price) + sign * 0.618 * span,
    )


def _pez_bounds(
    *,
    source_prz_low: float,
    source_prz_high: float,
    terminal_price: float,
    direction: PatternDirection,
) -> tuple[float, float]:
    """Volume-3 PEZ: source PRZ integrated with the observed T-Bar extreme.

    For bullish structures the overspill risk is below harmonic support, while bearish
    structures can overspill above harmonic resistance. If the T-Bar does not overspill,
    the PEZ remains the source PRZ itself.
    """
    if direction is PatternDirection.BULLISH:
        return min(source_prz_low, terminal_price), source_prz_high
    return source_prz_low, max(source_prz_high, terminal_price)


def observe_source_execution(
    frame: pd.DataFrame,
    *,
    signal_bar: int,
    direction: PatternDirection,
    prz: PotentialReversalZone,
    reaction_anchor_price: float,
    observation_end_bar: int | None = None,
) -> SourceExecutionAudit:
    """Observe the source-aligned Terminal Price Bar clock without future leakage.

    ``signal_bar`` is the bar where the forming projection became observable. The search
    starts at ``signal_bar + 1``; a same-bar or historical PRZ touch is never retroactively
    promoted into a Terminal event.

    ``observation_end_bar`` can retire a forming projection. When supplied, no later bar
    may claim a Terminal event.

    A bullish Terminal Price Bar is the first active future bar whose low tests the lower
    terminal side of the frozen source PRZ. A bearish Terminal Price Bar analogously tests
    the upper terminal side. A mere overlap is recorded as entry but is not completion.
    """

    _validate_frame(frame, signal_bar)
    if observation_end_bar is not None and observation_end_bar < signal_bar:
        raise ValueError("observation_end_bar must be >= signal_bar")

    if not prz.has_source_prz:
        return SourceExecutionAudit(
            signal_bar=signal_bar,
            direction=direction,
            state="source_prz_unresolved",
            source_prz_available=False,
            source_prz_low=None,
            source_prz_high=None,
            first_prz_entry_bar=None,
            terminal_bar=None,
            terminal_price=None,
            execution_start_bar=None,
            pez_low=None,
            pez_high=None,
            target_382=None,
            target_618=None,
        )

    assert prz.source_prz_low is not None and prz.source_prz_high is not None
    source_low = float(prz.source_prz_low)
    source_high = float(prz.source_prz_high)
    end_bar = len(frame) - 1 if observation_end_bar is None else min(observation_end_bar, len(frame) - 1)

    first_entry: int | None = None
    terminal_bar: int | None = None
    terminal_price: float | None = None

    for absolute in range(signal_bar + 1, end_bar + 1):
        row = frame.iloc[absolute]
        low = float(row["low"])
        high = float(row["high"])
        overlaps = high >= source_low and low <= source_high
        if first_entry is None and overlaps:
            first_entry = absolute

        if direction is PatternDirection.BULLISH and low <= source_low:
            terminal_bar = absolute
            terminal_price = low
            break
        if direction is PatternDirection.BEARISH and high >= source_high:
            terminal_bar = absolute
            terminal_price = high
            break

    if terminal_bar is None or terminal_price is None:
        state = "prz_entered_waiting_terminal" if first_entry is not None else "awaiting_prz_entry"
        return SourceExecutionAudit(
            signal_bar=signal_bar,
            direction=direction,
            state=state,
            source_prz_available=True,
            source_prz_low=source_low,
            source_prz_high=source_high,
            first_prz_entry_bar=first_entry,
            terminal_bar=None,
            terminal_price=None,
            execution_start_bar=None,
            pez_low=None,
            pez_high=None,
            target_382=None,
            target_618=None,
        )

    pez_low, pez_high = _pez_bounds(
        source_prz_low=source_low,
        source_prz_high=source_high,
        terminal_price=terminal_price,
        direction=direction,
    )
    target_382, target_618 = _reaction_targets(
        terminal_price=terminal_price,
        reaction_anchor_price=float(reaction_anchor_price),
        direction=direction,
    )

    return SourceExecutionAudit(
        signal_bar=signal_bar,
        direction=direction,
        state="terminal_observed",
        source_prz_available=True,
        source_prz_low=source_low,
        source_prz_high=source_high,
        first_prz_entry_bar=first_entry,
        terminal_bar=terminal_bar,
        terminal_price=terminal_price,
        execution_start_bar=terminal_bar + 1,
        pez_low=pez_low,
        pez_high=pez_high,
        target_382=target_382,
        target_618=target_618,
    )
