from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .discovery import iter_hierarchical_xabc_frontier_windows
from .execution import SourceExecutionAudit
from .models import HarmonicPoint, PatternDirection
from .pivots import detect_pivot_events, visible_confirmed_pivots
from .prz import PotentialReversalZone
from .scanner import project_forming_xabcd


PRODUCTION_MAX_TOTAL_SKIPS = 8


@dataclass(frozen=True, slots=True)
class SourceProjection:
    """First-knowable standard XABCD projection born from a confirmed XABC source."""

    pattern_id: str
    direction: PatternDirection
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint]
    known_at: int
    prz: PotentialReversalZone
    scales: tuple[int, ...]
    min_skipped_pivots: int

    @property
    def node_indices(self) -> tuple[int, ...]:
        return tuple(point.index for point in self.points)

    @property
    def key(self) -> tuple[str, str, tuple[int, ...]]:
        return self.pattern_id, self.direction.value, self.node_indices


    @property
    def xa_length(self) -> float:
        return abs(float(self.points[1].price) - float(self.points[0].price))

    @property
    def source_prz_width_xa(self) -> float:
        """Frozen Source Raw PRZ width normalized by XA; quality/audit only."""

        if not self.prz.has_source_prz:
            raise ValueError("Source Raw PRZ is unavailable")
        if self.xa_length <= 0:
            raise ValueError("XA length must be positive")
        assert self.prz.source_prz_low is not None
        assert self.prz.source_prz_high is not None
        return (
            float(self.prz.source_prz_high) - float(self.prz.source_prz_low)
        ) / self.xa_length


@dataclass(frozen=True, slots=True)
class SourceCompletionEvent:
    """Observable Source Terminal completion independent from a right-confirmed D pivot."""

    projection: SourceProjection
    audit: SourceExecutionAudit

    def __post_init__(self) -> None:
        if self.audit.state != "terminal_observed":
            raise ValueError("SourceCompletionEvent requires a terminal_observed audit")
        if self.audit.terminal_bar is None or self.audit.terminal_price is None:
            raise ValueError("terminal_observed audit must expose terminal bar/price")
        if self.audit.terminal_bar <= self.projection.known_at:
            raise ValueError("Source Terminal must occur after the projection is knowable")

    @property
    def pattern_id(self) -> str:
        return self.projection.pattern_id

    @property
    def direction(self) -> PatternDirection:
        return self.projection.direction

    @property
    def source_nodes(self) -> tuple[int, ...]:
        return self.projection.node_indices

    @property
    def known_at(self) -> int:
        return self.projection.known_at

    @property
    def terminal_bar(self) -> int:
        assert self.audit.terminal_bar is not None
        return int(self.audit.terminal_bar)

    @property
    def terminal_price(self) -> float:
        assert self.audit.terminal_price is not None
        return float(self.audit.terminal_price)


@dataclass(frozen=True, slots=True)
class SourceProjectionState:
    """Observable lifecycle state for one first-knowable XABC projection.

    Validity is an HT-CN operational policy, not Carney Source identity. The frozen
    Source Raw PRZ and Source Terminal clock are unchanged.
    """

    projection: SourceProjection
    state: str
    audit: SourceExecutionAudit
    closed_bar: int | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        allowed = {"completed", "invalidated", "expired", "active"}
        if self.state not in allowed:
            raise ValueError(f"unsupported SourceProjectionState: {self.state}")
        if self.state == "completed" and self.audit.state != "terminal_observed":
            raise ValueError("completed projection state requires terminal_observed audit")
        if self.state != "completed" and self.audit.state == "terminal_observed":
            raise ValueError("non-completed projection state cannot carry terminal_observed audit")


@dataclass(frozen=True, slots=True)
class SourceCompletionScan:
    projections: tuple[SourceProjection, ...]
    states: tuple[SourceProjectionState, ...]
    completions: tuple[SourceCompletionEvent, ...]
    invalidated_without_terminal: int
    expired_without_terminal: int
    active_without_terminal: int
    policy: str = "confirmed_c_extreme_or_expiry_skip8_v1"


def _merge_projection(
    store: dict[tuple[str, str, tuple[int, ...]], SourceProjection],
    item: SourceProjection,
) -> None:
    prior = store.get(item.key)
    if prior is None:
        store[item.key] = item
        return
    store[item.key] = SourceProjection(
        pattern_id=item.pattern_id,
        direction=item.direction,
        points=item.points,
        known_at=min(prior.known_at, item.known_at),
        prz=prior.prz,
        scales=tuple(sorted(set(prior.scales) | set(item.scales))),
        min_skipped_pivots=min(
            prior.min_skipped_pivots,
            item.min_skipped_pivots,
        ),
    )


def event_sourced_hierarchical_xabc_projections(
    frame: pd.DataFrame,
    *,
    scales: tuple[int, ...] = (3, 5, 8),
    recent_pivots: int = 20,
    max_leg_step: int = 7,
    max_total_skips: int = PRODUCTION_MAX_TOTAL_SKIPS,
) -> tuple[SourceProjection, ...]:
    """Return XABC projections at their first live-knowable confirmation bar.

    Production eligibility defaults to total skip budget 8. The broader hierarchical graph
    still supports 12 for research/diagnostics, but Gate 3 blind ablation showed no holdout
    recall gain above 8 while real-market candidate pressure increased.
    """

    born: dict[tuple[str, str, tuple[int, ...]], SourceProjection] = {}
    for scale in sorted({int(value) for value in scales}):
        events = detect_pivot_events(
            frame,
            left=scale,
            right=scale,
            scale=scale,
        )
        for cutoff in sorted({int(event.confirmed_at) for event in events}):
            pivots = visible_confirmed_pivots(events, cutoff=cutoff)
            for candidate in iter_hierarchical_xabc_frontier_windows(
                pivots,
                recent_pivots=recent_pivots,
                max_leg_step=max_leg_step,
                max_total_skips=max_total_skips,
            ):
                window = candidate.window
                points = window.harmonic_points()
                for projection in project_forming_xabcd(
                    window,
                    include_source_conflict_patterns=False,
                ):
                    if not projection.prz.has_source_prz:
                        continue
                    item = SourceProjection(
                        pattern_id=projection.pattern_id,
                        direction=projection.direction,
                        points=(
                            points[0],
                            points[1],
                            points[2],
                            points[3],
                        ),
                        known_at=cutoff,
                        prz=projection.prz,
                        scales=(scale,),
                        min_skipped_pivots=int(candidate.skipped_pivots),
                    )
                    _merge_projection(born, item)

    return tuple(
        sorted(
            born.values(),
            key=lambda item: (
                item.known_at,
                item.points[-1].index,
                item.pattern_id,
                item.direction.value,
                item.node_indices,
            ),
        )
    )


def _recognition_source_execution(
    frame: pd.DataFrame,
    *,
    signal_bar: int,
    direction: PatternDirection,
    prz: PotentialReversalZone,
    reaction_anchor_price: float,
    observation_end_bar: int,
) -> SourceExecutionAudit:
    """Recognition-V2 Source clock with an explicit PRZ-contact requirement.

    The frozen M4 observer is preserved unchanged for historical prospective evidence.
    Recognition V2 fixes a semantic inconsistency with source_lifecycle: a terminal-side
    test must occur on a bar that actually overlaps Source Raw PRZ. A bar wholly beyond
    the zone is a gap-through, not an observable PRZ test.
    """

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
    end_bar = min(int(observation_end_bar), len(frame) - 1)
    first_entry: int | None = None
    terminal_bar: int | None = None
    terminal_price: float | None = None

    for bar in range(signal_bar + 1, end_bar + 1):
        row = frame.iloc[bar]
        low = float(row["low"])
        high = float(row["high"])
        overlaps = high >= source_low and low <= source_high
        if not overlaps:
            continue
        if first_entry is None:
            first_entry = bar
        if direction is PatternDirection.BULLISH and low <= source_low:
            terminal_bar = bar
            terminal_price = low
            break
        if direction is PatternDirection.BEARISH and high >= source_high:
            terminal_bar = bar
            terminal_price = high
            break

    if terminal_bar is None or terminal_price is None:
        state = (
            "prz_entered_waiting_terminal"
            if first_entry is not None
            else "awaiting_prz_entry"
        )
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

    if direction is PatternDirection.BULLISH:
        pez_low = min(source_low, terminal_price)
        pez_high = source_high
        sign = 1.0
    else:
        pez_low = source_low
        pez_high = max(source_high, terminal_price)
        sign = -1.0
    span = abs(float(reaction_anchor_price) - terminal_price)
    if span <= 0:
        raise ValueError(
            "reaction anchor and Terminal Price Bar must define a positive span"
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
        target_382=terminal_price + sign * 0.382 * span,
        target_618=terminal_price + sign * 0.618 * span,
    )


def _first_c_extreme_breach(
    frame: pd.DataFrame,
    projection: SourceProjection,
    *,
    end_bar: int,
) -> int | None:
    """Return the first future bar that makes the frozen C extreme obsolete."""

    c_price = float(projection.points[-1].price)
    for bar in range(projection.known_at + 1, end_bar + 1):
        row = frame.iloc[bar]
        if projection.direction is PatternDirection.BULLISH:
            if float(row["high"]) > c_price:
                return bar
        elif float(row["low"]) < c_price:
            return bar
    return None


def _projection_state(
    frame: pd.DataFrame,
    projection: SourceProjection,
    *,
    lifetime_bars: int,
) -> SourceProjectionState:
    """Resolve one projection without invalidated/expired pattern resurrection."""

    max_end = min(
        len(frame) - 1,
        projection.known_at + int(lifetime_bars),
    )
    invalidation_bar = _first_c_extreme_breach(
        frame,
        projection,
        end_bar=max_end,
    )
    observation_end = (
        min(max_end, invalidation_bar - 1)
        if invalidation_bar is not None
        else max_end
    )
    audit = _recognition_source_execution(
        frame,
        signal_bar=projection.known_at,
        direction=projection.direction,
        prz=projection.prz,
        reaction_anchor_price=float(projection.points[1].price),
        observation_end_bar=observation_end,
    )

    if audit.state == "terminal_observed":
        return SourceProjectionState(
            projection=projection,
            state="completed",
            audit=audit,
            closed_bar=audit.terminal_bar,
            reason="source_terminal_observed",
        )

    if invalidation_bar is not None:
        return SourceProjectionState(
            projection=projection,
            state="invalidated",
            audit=audit,
            closed_bar=invalidation_bar,
            reason="confirmed_c_extreme_breached_before_terminal",
        )

    expiry_bar = projection.known_at + int(lifetime_bars)
    if len(frame) - 1 >= expiry_bar:
        return SourceProjectionState(
            projection=projection,
            state="expired",
            audit=audit,
            closed_bar=expiry_bar,
            reason="observation_lifetime_expired",
        )

    return SourceProjectionState(
        projection=projection,
        state="active",
        audit=audit,
        closed_bar=None,
        reason=None,
    )


def scan_source_completion_events(
    frame: pd.DataFrame,
    *,
    scales: tuple[int, ...] = (3, 5, 8),
    recent_pivots: int = 20,
    max_leg_step: int = 7,
    max_total_skips: int = PRODUCTION_MAX_TOTAL_SKIPS,
    lifetime_bars: int = 180,
) -> SourceCompletionScan:
    """Observe Source Terminal completions under an explicit live-validity clock.

    A projection is invalidated if its confirmed C extreme is exceeded before Source
    Terminal. It expires after lifetime_bars. Retired projections are never replayed
    against later price action.
    """

    if lifetime_bars < 1:
        raise ValueError("lifetime_bars must be positive")

    projections = event_sourced_hierarchical_xabc_projections(
        frame,
        scales=scales,
        recent_pivots=recent_pivots,
        max_leg_step=max_leg_step,
        max_total_skips=max_total_skips,
    )
    states: list[SourceProjectionState] = []
    completions: list[SourceCompletionEvent] = []

    for projection in projections:
        state = _projection_state(
            frame,
            projection,
            lifetime_bars=lifetime_bars,
        )
        states.append(state)
        if state.state != "completed":
            continue
        completions.append(
            SourceCompletionEvent(
                projection=projection,
                audit=state.audit,
            )
        )

    return SourceCompletionScan(
        projections=projections,
        states=tuple(states),
        completions=tuple(completions),
        invalidated_without_terminal=sum(item.state == "invalidated" for item in states),
        expired_without_terminal=sum(item.state == "expired" for item in states),
        active_without_terminal=sum(item.state == "active" for item in states),
    )
