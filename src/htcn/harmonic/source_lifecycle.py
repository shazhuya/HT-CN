from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum

import pandas as pd

from .execution import SourceExecutionAudit
from .models import PatternDirection


class SourceLifecycleState(str, Enum):
    """Canonical observable product states for the source execution clock."""

    SOURCE_CLOCK_UNAVAILABLE = "source_clock_unavailable"
    SOURCE_PRZ_UNRESOLVED = "source_prz_unresolved"
    APPROACHING_SOURCE_PRZ = "approaching_source_prz"
    ENTERED_SOURCE_PRZ = "entered_source_prz"
    WAITING_TERMINAL = "waiting_terminal"
    SOURCE_TERMINAL_COMPLETE = "source_terminal_complete"
    T_PLUS_1 = "t_plus_1"
    TYPE_I_EARLY_REACTION = "type_i_early_reaction"
    TYPE_I_CONFIRMED = "type_i_confirmed"
    TYPE_I_FAILED = "type_i_failed"
    REACTION_ONLY = "reaction_only"
    TYPE_II_RETEST_FORMING = "type_ii_retest_forming"
    TYPE_II_TERMINAL = "type_ii_terminal"
    REVERSAL_EVIDENCE = "reversal_evidence"
    INVALIDATED = "invalidated"


@dataclass(frozen=True, slots=True)
class SourceLifecycleSnapshot:
    """Current observable lifecycle derived only from the source execution clock.

    Historical D/C geometry is deliberately absent from the transition inputs. The
    snapshot is an execution/product interpretation layer; it cannot create harmonic
    identity or mutate Source Raw PRZ.
    """

    state: SourceLifecycleState
    state_reason: str
    clock_source: str
    current_bar: int
    signal_bar: int | None
    source_prz_entry_bar: int | None
    source_terminal_bar: int | None
    execution_start_bar: int | None
    bars_since_terminal: int | None
    type_i_t1_bar: int | None
    type_i_t2_bar: int | None
    first_source_prz_exit_bar: int | None
    type_ii_retest_entry_bar: int | None
    type_ii_terminal_bar: int | None
    reversal_exit_after_type_ii_bar: int | None
    source_prz_low: float | None
    source_prz_high: float | None
    pez_low: float | None
    pez_high: float | None
    target_382: float | None
    target_618: float | None
    next_key_price: float | None
    next_key_price_role: str | None
    strict_type_ii_full_retest: bool
    retrospective_geometry_clock_used: bool

    def as_payload(self) -> dict[str, object]:
        payload = asdict(self)
        payload["state"] = self.state.value
        return payload


def unavailable_source_lifecycle(*, current_bar: int, reason: str) -> SourceLifecycleSnapshot:
    return SourceLifecycleSnapshot(
        state=SourceLifecycleState.SOURCE_CLOCK_UNAVAILABLE,
        state_reason=reason,
        clock_source="source_terminal_price_bar",
        current_bar=current_bar,
        signal_bar=None,
        source_prz_entry_bar=None,
        source_terminal_bar=None,
        execution_start_bar=None,
        bars_since_terminal=None,
        type_i_t1_bar=None,
        type_i_t2_bar=None,
        first_source_prz_exit_bar=None,
        type_ii_retest_entry_bar=None,
        type_ii_terminal_bar=None,
        reversal_exit_after_type_ii_bar=None,
        source_prz_low=None,
        source_prz_high=None,
        pez_low=None,
        pez_high=None,
        target_382=None,
        target_618=None,
        next_key_price=None,
        next_key_price_role=None,
        strict_type_ii_full_retest=True,
        retrospective_geometry_clock_used=False,
    )


def _overlaps_source_prz(low: float, high: float, source_low: float, source_high: float) -> bool:
    return high >= source_low and low <= source_high


def _tests_terminal_side(
    low: float,
    high: float,
    *,
    direction: PatternDirection,
    source_low: float,
    source_high: float,
) -> bool:
    if not _overlaps_source_prz(low, high, source_low, source_high):
        return False
    if direction is PatternDirection.BULLISH:
        return low <= source_low
    return high >= source_high


def _exited_in_reversal_direction(
    low: float,
    high: float,
    *,
    direction: PatternDirection,
    source_low: float,
    source_high: float,
) -> bool:
    if direction is PatternDirection.BULLISH:
        return low > source_high
    return high < source_low


def _target_hit(row: pd.Series, *, direction: PatternDirection, target: float | None) -> bool:
    if target is None:
        return False
    if direction is PatternDirection.BULLISH:
        return float(row["high"]) >= target
    return float(row["low"]) <= target


def _next_key_price(
    state: SourceLifecycleState,
    *,
    direction: PatternDirection,
    source_low: float | None,
    source_high: float | None,
    target_382: float | None,
    target_618: float | None,
) -> tuple[float | None, str | None]:
    if source_low is None or source_high is None:
        return None, None
    if state is SourceLifecycleState.APPROACHING_SOURCE_PRZ:
        return (
            source_high if direction is PatternDirection.BULLISH else source_low,
            "source_prz_entry_edge",
        )
    if state in {
        SourceLifecycleState.ENTERED_SOURCE_PRZ,
        SourceLifecycleState.WAITING_TERMINAL,
        SourceLifecycleState.TYPE_II_RETEST_FORMING,
    }:
        return (
            source_low if direction is PatternDirection.BULLISH else source_high,
            "source_prz_terminal_side",
        )
    if state in {
        SourceLifecycleState.SOURCE_TERMINAL_COMPLETE,
        SourceLifecycleState.T_PLUS_1,
        SourceLifecycleState.TYPE_I_EARLY_REACTION,
        SourceLifecycleState.TYPE_I_FAILED,
    }:
        return target_382, "type_i_38_2_target"
    if state in {SourceLifecycleState.TYPE_I_CONFIRMED, SourceLifecycleState.REACTION_ONLY}:
        return target_618, "type_i_61_8_target"
    if state is SourceLifecycleState.TYPE_II_TERMINAL:
        return (
            source_high if direction is PatternDirection.BULLISH else source_low,
            "type_ii_reversal_exit_edge",
        )
    return None, None


def derive_source_lifecycle(
    frame: pd.DataFrame,
    audit: SourceExecutionAudit,
) -> SourceLifecycleSnapshot:
    """Derive the current M3 lifecycle from an already-observable source clock.

    The function is prefix-safe: it only scans rows contained in ``frame`` and never uses
    a historical D/C pivot. Type-I timing is an HT-CN execution-state operationalization:
    38.2% reached within five bars after Source T-Bar is classified as early confirmation;
    a later 38.2% reach is retained as ``reaction_only``. This does not alter Carney
    pattern identity or Source Raw PRZ.

    Type-II uses the existing conservative production policy: after a reversal-direction
    exit, price must re-enter the frozen Source Raw PRZ and retest its terminal side before
    ``type_ii_terminal`` may be emitted.
    """
    missing = {"high", "low"}.difference(frame.columns)
    if missing:
        raise ValueError(f"source lifecycle missing columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("source lifecycle requires at least one bar")

    current_bar = len(frame) - 1
    direction = audit.direction
    source_low = audit.source_prz_low
    source_high = audit.source_prz_high

    if not audit.source_prz_available or source_low is None or source_high is None:
        return SourceLifecycleSnapshot(
            state=SourceLifecycleState.SOURCE_PRZ_UNRESOLVED,
            state_reason="Source Raw PRZ is unresolved; lifecycle fails closed.",
            clock_source="source_terminal_price_bar",
            current_bar=current_bar,
            signal_bar=audit.signal_bar,
            source_prz_entry_bar=None,
            source_terminal_bar=None,
            execution_start_bar=None,
            bars_since_terminal=None,
            type_i_t1_bar=None,
            type_i_t2_bar=None,
            first_source_prz_exit_bar=None,
            type_ii_retest_entry_bar=None,
            type_ii_terminal_bar=None,
            reversal_exit_after_type_ii_bar=None,
            source_prz_low=None,
            source_prz_high=None,
            pez_low=None,
            pez_high=None,
            target_382=None,
            target_618=None,
            next_key_price=None,
            next_key_price_role=None,
            strict_type_ii_full_retest=True,
            retrospective_geometry_clock_used=False,
        )

    source_low = float(source_low)
    source_high = float(source_high)

    if audit.terminal_bar is None:
        if audit.first_prz_entry_bar is None:
            state = SourceLifecycleState.APPROACHING_SOURCE_PRZ
            reason = "Projection is observable; Source Raw PRZ has not been entered yet."
        elif current_bar == int(audit.first_prz_entry_bar):
            state = SourceLifecycleState.ENTERED_SOURCE_PRZ
            reason = "Price has entered Source Raw PRZ but has not tested the terminal side."
        else:
            state = SourceLifecycleState.WAITING_TERMINAL
            reason = "Price is/has been inside Source Raw PRZ; waiting for a terminal-side test."
        next_price, next_role = _next_key_price(
            state,
            direction=direction,
            source_low=source_low,
            source_high=source_high,
            target_382=audit.target_382,
            target_618=audit.target_618,
        )
        return SourceLifecycleSnapshot(
            state=state,
            state_reason=reason,
            clock_source="source_terminal_price_bar",
            current_bar=current_bar,
            signal_bar=audit.signal_bar,
            source_prz_entry_bar=audit.first_prz_entry_bar,
            source_terminal_bar=None,
            execution_start_bar=None,
            bars_since_terminal=None,
            type_i_t1_bar=None,
            type_i_t2_bar=None,
            first_source_prz_exit_bar=None,
            type_ii_retest_entry_bar=None,
            type_ii_terminal_bar=None,
            reversal_exit_after_type_ii_bar=None,
            source_prz_low=source_low,
            source_prz_high=source_high,
            pez_low=None,
            pez_high=None,
            target_382=None,
            target_618=None,
            next_key_price=next_price,
            next_key_price_role=next_role,
            strict_type_ii_full_retest=True,
            retrospective_geometry_clock_used=False,
        )

    terminal_bar = int(audit.terminal_bar)
    if terminal_bar > current_bar:
        raise ValueError("source terminal bar is outside the supplied frame prefix")

    type_i_t1_bar: int | None = None
    type_i_t2_bar: int | None = None
    first_exit: int | None = None
    retest_entry: int | None = None
    type_ii_terminal: int | None = None
    reversal_exit_after_type_ii: int | None = None

    for absolute in range(terminal_bar + 1, current_bar + 1):
        row = frame.iloc[absolute]
        low = float(row["low"])
        high = float(row["high"])

        if type_i_t1_bar is None and _target_hit(row, direction=direction, target=audit.target_382):
            type_i_t1_bar = absolute
        if type_i_t2_bar is None and _target_hit(row, direction=direction, target=audit.target_618):
            type_i_t2_bar = absolute

        if first_exit is None and _exited_in_reversal_direction(
            low,
            high,
            direction=direction,
            source_low=source_low,
            source_high=source_high,
        ):
            first_exit = absolute
            continue

        if first_exit is not None and retest_entry is None and absolute > first_exit:
            if _overlaps_source_prz(low, high, source_low, source_high):
                retest_entry = absolute

        if retest_entry is not None and type_ii_terminal is None and absolute >= retest_entry:
            if _tests_terminal_side(
                low,
                high,
                direction=direction,
                source_low=source_low,
                source_high=source_high,
            ):
                type_ii_terminal = absolute
                continue

        if type_ii_terminal is not None and reversal_exit_after_type_ii is None and absolute > type_ii_terminal:
            if _exited_in_reversal_direction(
                low,
                high,
                direction=direction,
                source_low=source_low,
                source_high=source_high,
            ):
                reversal_exit_after_type_ii = absolute

    bars_since_terminal = current_bar - terminal_bar
    if reversal_exit_after_type_ii is not None:
        state = SourceLifecycleState.REVERSAL_EVIDENCE
        reason = "Strict Type-II terminal retest was followed by a reversal-direction Source PRZ exit."
    elif type_ii_terminal is not None:
        state = SourceLifecycleState.TYPE_II_TERMINAL
        reason = "Secondary retest reached the terminal side of the frozen Source Raw PRZ."
    elif retest_entry is not None:
        state = SourceLifecycleState.TYPE_II_RETEST_FORMING
        reason = "After a reversal-direction exit, price re-entered Source Raw PRZ without a full terminal-side retest yet."
    elif current_bar == terminal_bar:
        state = SourceLifecycleState.SOURCE_TERMINAL_COMPLETE
        reason = "Source Terminal Price Bar has completed; execution assessment starts at T-Bar+1."
    elif audit.execution_start_bar is not None and current_bar == int(audit.execution_start_bar):
        state = SourceLifecycleState.T_PLUS_1
        reason = "This is T-Bar+1, the first source-aligned execution observation bar."
    elif type_i_t1_bar is not None and type_i_t1_bar - terminal_bar <= 5:
        state = SourceLifecycleState.TYPE_I_CONFIRMED
        reason = "The 38.2% Type-I objective was reached within the first five bars after Source T-Bar."
    elif bars_since_terminal <= 5:
        state = SourceLifecycleState.TYPE_I_EARLY_REACTION
        reason = "Source T-Bar is inside the first five-bar Type-I reaction window; 38.2% has not been reached yet."
    elif type_i_t1_bar is not None:
        state = SourceLifecycleState.REACTION_ONLY
        reason = "A 38.2% reaction occurred only after the five-bar early Type-I window."
    else:
        state = SourceLifecycleState.TYPE_I_FAILED
        reason = "The first five bars after Source T-Bar ended without reaching the 38.2% Type-I objective."

    next_price, next_role = _next_key_price(
        state,
        direction=direction,
        source_low=source_low,
        source_high=source_high,
        target_382=audit.target_382,
        target_618=audit.target_618,
    )
    return SourceLifecycleSnapshot(
        state=state,
        state_reason=reason,
        clock_source="source_terminal_price_bar",
        current_bar=current_bar,
        signal_bar=audit.signal_bar,
        source_prz_entry_bar=audit.first_prz_entry_bar,
        source_terminal_bar=terminal_bar,
        execution_start_bar=audit.execution_start_bar,
        bars_since_terminal=bars_since_terminal,
        type_i_t1_bar=type_i_t1_bar,
        type_i_t2_bar=type_i_t2_bar,
        first_source_prz_exit_bar=first_exit,
        type_ii_retest_entry_bar=retest_entry,
        type_ii_terminal_bar=type_ii_terminal,
        reversal_exit_after_type_ii_bar=reversal_exit_after_type_ii,
        source_prz_low=source_low,
        source_prz_high=source_high,
        pez_low=audit.pez_low,
        pez_high=audit.pez_high,
        target_382=audit.target_382,
        target_618=audit.target_618,
        next_key_price=next_price,
        next_key_price_role=next_role,
        strict_type_ii_full_retest=True,
        retrospective_geometry_clock_used=False,
    )
