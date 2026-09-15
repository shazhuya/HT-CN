from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .abcd import ABCDMatch, scan_abcd_pivots
from .candidates import iter_completed_xabcd_windows, iter_forming_xabc_windows
from .evaluator import PatternEvaluation
from .models import HarmonicPoint, PatternDirection, PatternState, Pivot
from .pivots import detect_multi_scale_pivots
from .prz import PotentialReversalZone
from .scanner import FormingPattern, classify_completed_xabcd, project_forming_xabcd


@dataclass(frozen=True, slots=True)
class CompletedMatch:
    pattern_id: str
    direction: PatternDirection
    state: PatternState
    scale: int
    points: tuple[HarmonicPoint, ...]
    evaluation: PatternEvaluation
    geometry_score: float
    conflict_key: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class FormingMatch:
    pattern_id: str
    direction: PatternDirection
    state: PatternState
    scale: int
    points: tuple[HarmonicPoint, ...]
    projection: FormingPattern
    geometry_score: float
    conflict_key: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class HarmonicScan:
    completed: tuple[CompletedMatch, ...]
    forming: tuple[FormingMatch, ...]
    pivots_by_scale: dict[int, tuple[Pivot, ...]]
    abcd_completed: tuple[ABCDMatch, ...] = ()


def _prz_width_ratio(prz: PotentialReversalZone, points: tuple[HarmonicPoint, ...]) -> float:
    if len(points) < 2:
        return 1.0
    xa = abs(points[1].price - points[0].price)
    if xa <= 0:
        return 1.0
    return prz.width / xa


def _completed_score(evaluation: PatternEvaluation, points: tuple[HarmonicPoint, ...]) -> float:
    """Soft geometry quality, deliberately separate from pass/fail identity.

    Preferred AB=CD variants are useful for ranking but the books often describe them as
    minimum/common/preferred rather than an exact identity tolerance. Therefore a large
    AB=CD deviation is capped as a quality penalty instead of zeroing a source-valid Crab,
    Bat, etc. This score is never a probability or expected return.
    """
    check_error = sum(check.distance_to_canonical for check in evaluation.checks)
    raw_abcd_error = 0.0 if evaluation.abcd_distance == float("inf") else evaluation.abcd_distance
    abcd_error = min(raw_abcd_error, 0.20)
    width_error = min(_prz_width_ratio(evaluation.prz, points), 0.35)
    penalty = (2.2 * check_error) + (0.9 * abcd_error) + (1.2 * width_error)
    return round(max(0.0, min(100.0, 100.0 * (1.0 - penalty))), 2)


def _forming_score(projection: FormingPattern, points: tuple[HarmonicPoint, ...]) -> float:
    # Forming patterns cannot be scored on D because D does not exist yet. Keep the
    # score deliberately conservative and based only on B alignment + PRZ compactness.
    width_error = _prz_width_ratio(projection.prz, points)
    tolerance_penalty = 0.08 if projection.source_tolerance_used else 0.0
    penalty = tolerance_penalty + min(width_error, 0.8)
    return round(max(0.0, min(100.0, 100.0 * (1.0 - penalty))), 2)


def _dedupe_completed(items: list[CompletedMatch]) -> list[CompletedMatch]:
    """Collapse the same semantic geometry rediscovered at multiple pivot scales.

    Different pattern identities on the same node set are intentionally preserved so
    genuine identity conflicts stay visible and auditable.
    """
    out: list[CompletedMatch] = []
    seen: set[tuple[str, PatternDirection, tuple[int, ...]]] = set()
    for item in items:
        key = (item.pattern_id, item.direction, item.conflict_key)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _dedupe_forming(items: list[FormingMatch]) -> list[FormingMatch]:
    out: list[FormingMatch] = []
    seen: set[tuple[str, PatternDirection, tuple[int, ...]]] = set()
    for item in items:
        key = (item.pattern_id, item.direction, item.conflict_key)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def scan_pivots(
    pivots_by_scale: dict[int, tuple[Pivot, ...] | list[Pivot]],
    *,
    include_source_tolerance: bool = True,
    abcd_relative_tolerance: float = 0.03,
    max_completed: int = 40,
    max_forming: int = 40,
) -> HarmonicScan:
    completed: list[CompletedMatch] = []
    forming: list[FormingMatch] = []
    normalized: dict[int, tuple[Pivot, ...]] = {
        int(scale): tuple(pivots) for scale, pivots in pivots_by_scale.items()
    }

    for scale, pivots in normalized.items():
        for window in iter_completed_xabcd_windows(pivots):
            points = window.harmonic_points()
            for evaluation in classify_completed_xabcd(
                window,
                include_source_tolerance=include_source_tolerance,
                abcd_relative_tolerance=abcd_relative_tolerance,
            ):
                completed.append(
                    CompletedMatch(
                        pattern_id=evaluation.pattern_id,
                        direction=evaluation.direction,
                        state=PatternState.COMPLETED,
                        scale=scale,
                        points=points,
                        evaluation=evaluation,
                        geometry_score=_completed_score(evaluation, points),
                        conflict_key=tuple(point.index for point in points),
                    )
                )

        for window in iter_forming_xabc_windows(pivots):
            points = window.harmonic_points()
            for projection in project_forming_xabcd(
                window, include_source_tolerance=include_source_tolerance
            ):
                forming.append(
                    FormingMatch(
                        pattern_id=projection.pattern_id,
                        direction=projection.direction,
                        state=PatternState.FORMING,
                        scale=scale,
                        points=points,
                        projection=projection,
                        geometry_score=_forming_score(projection, points),
                        conflict_key=tuple(point.index for point in points),
                    )
                )

    completed.sort(
        key=lambda item: (
            -item.points[-1].index,
            -item.geometry_score,
            -item.scale,
            item.pattern_id,
        )
    )
    forming.sort(
        key=lambda item: (
            -item.points[-1].index,
            -item.geometry_score,
            -item.scale,
            item.pattern_id,
        )
    )
    completed = _dedupe_completed(completed)
    forming = _dedupe_forming(forming)
    standalone_abcd = scan_abcd_pivots(
        normalized,
        c_relative_tolerance=abcd_relative_tolerance,
        bc_relative_tolerance=abcd_relative_tolerance,
        abcd_relative_tolerance=abcd_relative_tolerance,
        max_completed=max_completed,
    )
    return HarmonicScan(
        completed=tuple(completed[:max_completed]),
        forming=tuple(forming[:max_forming]),
        pivots_by_scale=normalized,
        abcd_completed=standalone_abcd,
    )


def scan_frame(
    frame: pd.DataFrame,
    *,
    scales: tuple[int, ...] = (3, 5, 8, 13),
    include_source_tolerance: bool = True,
    abcd_relative_tolerance: float = 0.03,
    max_completed: int = 40,
    max_forming: int = 40,
) -> HarmonicScan:
    """Run the deterministic geometry pipeline on one OHLC history frame.

    Input prices are expected to already be the desired continuous view (QFQ for HT-CN's
    normal A-share harmonic workflow). This function never adjusts prices or injects A-share
    market context into Carney geometry.
    """
    if frame.empty:
        return HarmonicScan(completed=(), forming=(), pivots_by_scale={}, abcd_completed=())
    pivots = detect_multi_scale_pivots(frame, scales=scales)
    return scan_pivots(
        pivots,
        include_source_tolerance=include_source_tolerance,
        abcd_relative_tolerance=abcd_relative_tolerance,
        max_completed=max_completed,
        max_forming=max_forming,
    )
