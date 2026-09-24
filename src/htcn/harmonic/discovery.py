from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import pandas as pd

from .candidates import SwingWindow
from .models import HarmonicPoint, PatternDirection, Pivot
from .pivots import build_pivot_consensus, detect_multi_scale_pivots
from .prz import PotentialReversalZone, build_xabcd_prz
from .ratios import leg_length
from .rules import CARNEY_RULES, PatternRule


DISCOVERY_SCALES: tuple[int, ...] = (5, 10, 20)
DEFAULT_C_FAMILY_TOLERANCE = 0.03


@dataclass(frozen=True, slots=True)
class DiscoveryCandidate:
    """Non-authoritative XABC candidate used only for high-recall product discovery.

    Discovery deliberately sits *before* canonical completed identity. It may retain an XABC
    projection after later pivots exist and may use a bounded graph path that skips one complete
    minor swing pair. It never fabricates D, mutates Source Raw PRZ, or owns lifecycle state.
    """

    pattern_id: str
    direction: PatternDirection
    scale: int
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint]
    pivots: tuple[Pivot, Pivot, Pivot, Pivot]
    prz: PotentialReversalZone
    b_xa: float
    c_ab: float
    c_family_target: float | None
    c_family_relative_error: float | None
    source_family_aligned: bool
    source_tolerance_used: bool
    skipped_pivots: int
    path_kind: str
    known_from_bar: int
    bars_since_c: int
    prz_status: str
    first_prz_test_bar: int | None
    distance_to_source_prz_xa: float
    geometry_score: float
    conflict_key: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.prz.has_source_prz:
            raise ValueError("discovery candidate requires a frozen Source PRZ")
        if self.prz_status not in {"projected", "tested"}:
            raise ValueError("invalid discovery PRZ status")
        if self.known_from_bar < self.points[-1].index:
            raise ValueError("candidate cannot be knowable before C")
        if self.skipped_pivots < 0:
            raise ValueError("skipped_pivots must be non-negative")


@dataclass(frozen=True, slots=True)
class DiscoveryScan:
    candidates: tuple[DiscoveryCandidate, ...]
    pivots_by_scale: dict[int, tuple[Pivot, ...]]
    pivot_consensus: dict
    diagnostics: dict[str, int]


@dataclass(frozen=True, slots=True)
class _DiscoveryWindow:
    window: SwingWindow
    skipped_pivots: int
    path_kind: str


def _validate_pivots(pivots: tuple[Pivot, ...]) -> None:
    if any(left.index >= right.index for left, right in zip(pivots, pivots[1:])):
        raise ValueError("pivot sequence must be strictly increasing")
    if len({pivot.scale for pivot in pivots}) > 1:
        raise ValueError("discovery path must remain on one pivot scale")


def iter_discovery_xabc_windows(
    pivots: tuple[Pivot, ...] | list[Pivot],
    *,
    recent_pivots: int = 18,
    max_total_skips: int = 4,
) -> tuple[_DiscoveryWindow, ...]:
    """Enumerate bounded recent XABC graph paths instead of only the latest four pivots.

    A leg may use the adjacent confirmed swing (step=1) or skip exactly one complete minor
    swing pair (step=3). A step of two would connect same-direction pivots in an alternating
    sequence and is therefore invalid. This gives the candidate builder limited noise
    tolerance without allowing arbitrary historical node stitching.
    """

    source = tuple(pivots)
    _validate_pivots(source)
    if len(source) < 4:
        return ()

    offset = max(0, len(source) - max(4, int(recent_pivots)))
    recent = source[offset:]
    scale = int(recent[0].scale)
    out: list[_DiscoveryWindow] = []

    for positions in combinations(range(len(recent)), 4):
        steps = tuple(right - left for left, right in zip(positions, positions[1:]))
        if any(step not in (1, 3) for step in steps):
            continue
        skipped = sum(step - 1 for step in steps)
        if skipped > max_total_skips:
            continue

        chunk = tuple(recent[position] for position in positions)
        if any(left.kind == right.kind for left, right in zip(chunk, chunk[1:])):
            continue

        path_kind = "consecutive" if skipped == 0 else "minor_swing_skip"
        out.append(
            _DiscoveryWindow(
                window=SwingWindow(scale=scale, pivots=chunk),
                skipped_pivots=skipped,
                path_kind=path_kind,
            )
        )

    return tuple(out)


def _source_cleared_xabcd_rules() -> tuple[PatternRule, ...]:
    return tuple(
        rule
        for rule in CARNEY_RULES.values()
        if rule.schema == "XABCD"
        and rule.executable_identity
        and not rule.source_conflict
    )


def _nearest_relative_error(
    value: float,
    targets: tuple[float, ...],
) -> tuple[float | None, float | None]:
    if not targets:
        return None, None
    target = min(targets, key=lambda item: abs(float(value) - float(item)) / float(item))
    return float(target), abs(float(value) - float(target)) / float(target)


def _turning_geometry_ok(
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
    direction: PatternDirection,
) -> bool:
    _, a, b, c = points
    if direction is PatternDirection.BULLISH:
        return b.price < a.price and c.price > b.price
    return b.price > a.price and c.price < b.price


def _source_prz_bounds(prz: PotentialReversalZone) -> tuple[float, float]:
    if prz.source_prz_low is None or prz.source_prz_high is None:
        raise ValueError("Source PRZ unavailable")
    return float(prz.source_prz_low), float(prz.source_prz_high)


def _first_source_prz_test(
    frame: pd.DataFrame,
    *,
    start_bar: int,
    prz: PotentialReversalZone,
) -> int | None:
    low, high = _source_prz_bounds(prz)
    if frame.empty or start_bar >= len(frame):
        return None
    start = max(0, int(start_bar))
    for index in range(start, len(frame)):
        row = frame.iloc[index]
        if float(row["high"]) >= low and float(row["low"]) <= high:
            return int(index)
    return None


def _distance_to_source_prz(
    price: float,
    *,
    prz: PotentialReversalZone,
) -> float:
    low, high = _source_prz_bounds(prz)
    if price < low:
        return low - price
    if price > high:
        return price - high
    return 0.0


def _score_candidate(
    *,
    c_family_relative_error: float | None,
    skipped_pivots: int,
    source_tolerance_used: bool,
    prz: PotentialReversalZone,
    xa: float,
    bars_since_c: int,
    distance_to_source_prz_xa: float,
    tested: bool,
) -> float:
    """Rank discovery candidates only; this score never owns Source identity."""

    family_penalty = (
        0.0
        if c_family_relative_error is None
        else min(30.0, float(c_family_relative_error) * 200.0)
    )
    skip_penalty = min(16.0, float(skipped_pivots) * 4.0)
    tolerance_penalty = 4.0 if source_tolerance_used else 0.0
    source_low, source_high = _source_prz_bounds(prz)
    width_penalty = min(
        20.0,
        (source_high - source_low) / max(xa, 1e-12) * 160.0,
    )
    age_penalty = min(20.0, max(0, bars_since_c) * 0.08)
    distance_penalty = min(25.0, max(0.0, distance_to_source_prz_xa) * 80.0)
    tested_bonus = 4.0 if tested else 0.0
    raw = 100.0 - family_penalty - skip_penalty - tolerance_penalty - width_penalty - age_penalty - distance_penalty + tested_bonus
    return round(max(0.0, min(100.0, raw)), 2)


def _project_window(
    candidate_window: _DiscoveryWindow,
    frame: pd.DataFrame,
    *,
    max_age_bars: int,
    c_family_tolerance: float,
) -> tuple[DiscoveryCandidate, ...]:
    window = candidate_window.window
    points = window.harmonic_points()
    if len(points) != 4:
        return ()
    x, a, b, c = points
    xa = leg_length(x.price, a.price)
    ab = leg_length(a.price, b.price)
    bc = leg_length(b.price, c.price)
    if min(xa, ab, bc) <= 0:
        return ()

    direction = PatternDirection.BULLISH if a.price > x.price else PatternDirection.BEARISH
    if not _turning_geometry_ok(points, direction):  # type: ignore[arg-type]
        return ()

    b_xa = ab / xa
    c_ab = bc / ab
    latest_index = max(len(frame) - 1, 0)
    c_pivot = window.pivots[-1]
    known_from_bar = int(c_pivot.confirmed_at)
    bars_since_c = max(0, latest_index - int(c.index))
    if bars_since_c > max_age_bars:
        return ()

    latest_close = float(frame.iloc[-1]["close"]) if not frame.empty else float(c.price)
    out: list[DiscoveryCandidate] = []

    for rule in _source_cleared_xabcd_rules():
        b_constraint = rule.constraints.get("b_xa")
        c_constraint = rule.constraints.get("c_ab")
        if b_constraint is None or c_constraint is None:
            continue
        if not b_constraint.contains(b_xa, include_tolerance=True):
            continue
        if not c_constraint.contains(c_ab, include_tolerance=True):
            continue

        try:
            prz = build_xabcd_prz(rule, points)  # type: ignore[arg-type]
        except ValueError:
            continue
        if not prz.has_source_prz:
            continue

        c_target, c_error = _nearest_relative_error(
            c_ab,
            tuple(rule.harmonic_targets.get("c_ab", ())),
        )
        source_family_aligned = bool(c_error is not None and c_error <= c_family_tolerance)
        tolerance_used = (
            not b_constraint.contains(b_xa, include_tolerance=False)
            or not c_constraint.contains(c_ab, include_tolerance=False)
        )

        first_test = _first_source_prz_test(
            frame,
            start_bar=known_from_bar,
            prz=prz,
        )
        tested = first_test is not None
        distance_ratio = _distance_to_source_prz(latest_close, prz=prz) / max(xa, 1e-12)
        score = _score_candidate(
            c_family_relative_error=c_error,
            skipped_pivots=candidate_window.skipped_pivots,
            source_tolerance_used=tolerance_used,
            prz=prz,
            xa=xa,
            bars_since_c=bars_since_c,
            distance_to_source_prz_xa=distance_ratio,
            tested=tested,
        )
        out.append(
            DiscoveryCandidate(
                pattern_id=rule.pattern_id,
                direction=direction,
                scale=int(window.scale),
                points=points,  # type: ignore[arg-type]
                pivots=window.pivots,  # type: ignore[arg-type]
                prz=prz,
                b_xa=float(b_xa),
                c_ab=float(c_ab),
                c_family_target=c_target,
                c_family_relative_error=c_error,
                source_family_aligned=source_family_aligned,
                source_tolerance_used=tolerance_used,
                skipped_pivots=candidate_window.skipped_pivots,
                path_kind=candidate_window.path_kind,
                known_from_bar=known_from_bar,
                bars_since_c=bars_since_c,
                prz_status="tested" if tested else "projected",
                first_prz_test_bar=first_test,
                distance_to_source_prz_xa=float(distance_ratio),
                geometry_score=score,
                conflict_key=tuple(int(point.index) for point in points),
            )
        )

    return tuple(out)


def discover_pivots(
    pivots_by_scale: dict[int, tuple[Pivot, ...] | list[Pivot]],
    frame: pd.DataFrame,
    *,
    recent_pivots: int = 18,
    max_total_skips: int = 4,
    max_age_bars: int = 240,
    c_family_tolerance: float = DEFAULT_C_FAMILY_TOLERANCE,
    max_candidates: int = 60,
) -> DiscoveryScan:
    """Discover XABC candidates from explicit pivot streams for testing/runtime reuse."""

    if c_family_tolerance < 0:
        raise ValueError("c_family_tolerance must be non-negative")
    if max_candidates < 1:
        raise ValueError("max_candidates must be >= 1")

    normalized = {
        int(scale): tuple(pivots)
        for scale, pivots in pivots_by_scale.items()
    }
    consensus = build_pivot_consensus(normalized)
    windows_considered = 0
    candidates: list[DiscoveryCandidate] = []

    for pivots in normalized.values():
        windows = iter_discovery_xabc_windows(
            pivots,
            recent_pivots=recent_pivots,
            max_total_skips=max_total_skips,
        )
        windows_considered += len(windows)
        for window in windows:
            candidates.extend(
                _project_window(
                    window,
                    frame,
                    max_age_bars=max_age_bars,
                    c_family_tolerance=c_family_tolerance,
                )
            )

    candidates.sort(
        key=lambda item: (
            -item.geometry_score,
            -item.points[-1].index,
            -item.scale,
            item.pattern_id,
        )
    )
    deduped: list[DiscoveryCandidate] = []
    seen: set[tuple[str, PatternDirection, tuple[int, ...]]] = set()
    for item in candidates:
        key = (item.pattern_id, item.direction, item.conflict_key)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= max_candidates:
            break

    return DiscoveryScan(
        candidates=tuple(deduped),
        pivots_by_scale=normalized,
        pivot_consensus=consensus,
        diagnostics={
            "windows_considered": windows_considered,
            "raw_candidates": len(candidates),
            "deduped_candidates": len(deduped),
        },
    )


def discover_frame(
    frame: pd.DataFrame,
    *,
    scales: tuple[int, ...] = DISCOVERY_SCALES,
    recent_pivots: int = 18,
    max_total_skips: int = 4,
    max_age_bars: int = 240,
    c_family_tolerance: float = DEFAULT_C_FAMILY_TOLERANCE,
    max_candidates: int = 60,
) -> DiscoveryScan:
    """Return bounded, persistent high-recall XABC discovery candidates.

    This function is intentionally separate from :func:`scan_frame`. It is a product
    discovery channel, not a substitute for canonical completed/forming identity.
    """

    if frame.empty:
        return DiscoveryScan(
            candidates=(),
            pivots_by_scale={},
            pivot_consensus={},
            diagnostics={
                "windows_considered": 0,
                "raw_candidates": 0,
                "deduped_candidates": 0,
            },
        )

    raw_pivots = detect_multi_scale_pivots(frame, scales=scales)
    return discover_pivots(
        raw_pivots,
        frame,
        recent_pivots=recent_pivots,
        max_total_skips=max_total_skips,
        max_age_bars=max_age_bars,
        c_family_tolerance=c_family_tolerance,
        max_candidates=max_candidates,
    )
