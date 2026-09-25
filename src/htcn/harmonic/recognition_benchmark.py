from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import pandas as pd

from .candidates import iter_completed_xabcd_windows
from .discovery import iter_discovery_xabcd_windows
from .engine import scan_frame
from .models import PatternDirection, PivotKind
from .pivots import (
    detect_multi_scale_pivots,
    detect_pivot_events,
    visible_confirmed_pivots,
)
from .scanner import classify_completed_xabcd


@dataclass(frozen=True, slots=True)
class RecognitionTruth:
    case_id: str
    pattern_id: str
    direction: str
    labels: tuple[str, ...]
    node_indices: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.case_id:
            raise ValueError("case_id is required")
        if self.direction not in {"bullish", "bearish"}:
            raise ValueError("direction must be bullish or bearish")
        if len(self.labels) != len(self.node_indices):
            raise ValueError("labels and node_indices must have the same length")
        if len(self.labels) < 3:
            raise ValueError("benchmark truth must contain at least three nodes")
        if any(left >= right for left, right in zip(self.node_indices, self.node_indices[1:])):
            raise ValueError("truth node indices must be strictly increasing")


@dataclass(frozen=True, slots=True)
class RecognitionPrediction:
    prediction_id: str
    pattern_id: str
    direction: str
    labels: tuple[str, ...]
    node_indices: tuple[int, ...]
    known_at: int | None = None


@dataclass(frozen=True, slots=True)
class MatchedRecognition:
    truth: RecognitionTruth
    prediction: RecognitionPrediction
    node_offsets: tuple[int, ...]

    @property
    def exact(self) -> bool:
        return all(offset == 0 for offset in self.node_offsets)

    @property
    def max_abs_offset(self) -> int:
        return max((abs(value) for value in self.node_offsets), default=0)


@dataclass(frozen=True, slots=True)
class RecognitionMetrics:
    truth_count: int
    prediction_count: int
    true_positive: int
    false_positive: int
    false_negative: int
    precision: float
    recall: float
    f1: float
    exact_match_count: int
    exact_match_rate: float
    tolerant_match_rate: float
    node_mae_bars: float | None
    node_mae_by_label: dict[str, float]
    matches: tuple[MatchedRecognition, ...]


FailureStage = Literal[
    "accepted",
    "pivot_missing",
    "candidate_window_missing",
    "rule_rejected",
]


@dataclass(frozen=True, slots=True)
class FailureDiagnosis:
    case_id: str
    stage: FailureStage
    scales_with_all_truth_nodes: tuple[int, ...]
    scales_with_exact_candidate: tuple[int, ...]


def _compatible(truth: RecognitionTruth, prediction: RecognitionPrediction) -> bool:
    return (
        truth.pattern_id == prediction.pattern_id
        and truth.direction == prediction.direction
        and truth.labels == prediction.labels
        and len(truth.node_indices) == len(prediction.node_indices)
    )


def match_predictions(
    truths: Sequence[RecognitionTruth],
    predictions: Sequence[RecognitionPrediction],
    *,
    tolerance_bars: int = 0,
) -> tuple[MatchedRecognition, ...]:
    """Return deterministic one-to-one matches within a predeclared node tolerance.

    Candidate pairs are ordered by max node error, total node error, truth case id and
    prediction id. One truth and one prediction can each be consumed at most once.
    """

    if tolerance_bars < 0:
        raise ValueError("tolerance_bars must be non-negative")

    candidates: list[
        tuple[int, int, str, str, int, int, tuple[int, ...]]
    ] = []
    for truth_index, truth in enumerate(truths):
        for prediction_index, prediction in enumerate(predictions):
            if not _compatible(truth, prediction):
                continue
            offsets = tuple(
                int(predicted) - int(expected)
                for expected, predicted in zip(
                    truth.node_indices,
                    prediction.node_indices,
                    strict=True,
                )
            )
            max_abs = max(abs(value) for value in offsets)
            if max_abs > tolerance_bars:
                continue
            candidates.append(
                (
                    max_abs,
                    sum(abs(value) for value in offsets),
                    truth.case_id,
                    prediction.prediction_id,
                    truth_index,
                    prediction_index,
                    offsets,
                )
            )

    candidates.sort()
    used_truths: set[int] = set()
    used_predictions: set[int] = set()
    matches: list[MatchedRecognition] = []
    for _, _, _, _, truth_index, prediction_index, offsets in candidates:
        if truth_index in used_truths or prediction_index in used_predictions:
            continue
        used_truths.add(truth_index)
        used_predictions.add(prediction_index)
        matches.append(
            MatchedRecognition(
                truth=truths[truth_index],
                prediction=predictions[prediction_index],
                node_offsets=offsets,
            )
        )
    return tuple(matches)


def score_predictions(
    truths: Sequence[RecognitionTruth],
    predictions: Sequence[RecognitionPrediction],
    *,
    tolerance_bars: int = 0,
) -> RecognitionMetrics:
    matches = match_predictions(
        truths,
        predictions,
        tolerance_bars=tolerance_bars,
    )
    tp = len(matches)
    fp = len(predictions) - tp
    fn = len(truths) - tp
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = (
        2.0 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    exact = sum(match.exact for match in matches)
    node_errors: list[int] = []
    by_label: dict[str, list[int]] = defaultdict(list)
    for match in matches:
        for label, offset in zip(
            match.truth.labels,
            match.node_offsets,
            strict=True,
        ):
            error = abs(int(offset))
            node_errors.append(error)
            by_label[label].append(error)

    return RecognitionMetrics(
        truth_count=len(truths),
        prediction_count=len(predictions),
        true_positive=tp,
        false_positive=fp,
        false_negative=fn,
        precision=precision,
        recall=recall,
        f1=f1,
        exact_match_count=exact,
        exact_match_rate=exact / len(truths) if truths else 1.0,
        tolerant_match_rate=tp / len(truths) if truths else 1.0,
        node_mae_bars=(
            sum(node_errors) / len(node_errors)
            if node_errors
            else None
        ),
        node_mae_by_label={
            label: sum(values) / len(values)
            for label, values in sorted(by_label.items())
        },
        matches=matches,
    )


def authoritative_predictions(
    frame: pd.DataFrame,
    *,
    scales: tuple[int, ...],
) -> tuple[RecognitionPrediction, ...]:
    scan = scan_frame(
        frame,
        scales=scales,
        max_completed=500,
        max_forming=500,
    )
    return tuple(
        RecognitionPrediction(
            prediction_id=(
                f"authoritative:{item.pattern_id}:{item.direction.value}:"
                + "-".join(str(point.index) for point in item.points)
            ),
            pattern_id=item.pattern_id,
            direction=item.direction.value,
            labels=tuple(point.label for point in item.points),
            node_indices=tuple(int(point.index) for point in item.points),
        )
        for item in scan.completed
    )


def graph_completed_predictions(
    frame: pd.DataFrame,
    *,
    scales: tuple[int, ...],
    recent_pivots: int = 20,
    max_total_skips: int = 4,
) -> tuple[RecognitionPrediction, ...]:
    """Experimental completed-XABCD predictions using bounded graph candidate generation.

    The classifier remains the canonical source-cleared classifier. Only candidate selection
    differs from production so benchmark deltas can isolate the consecutive-window bottleneck.
    """

    pivots_by_scale = detect_multi_scale_pivots(frame, scales=scales)
    predictions: list[RecognitionPrediction] = []
    seen: set[tuple[str, str, tuple[int, ...]]] = set()
    for scale, pivots in pivots_by_scale.items():
        for candidate in iter_discovery_xabcd_windows(
            pivots,
            recent_pivots=recent_pivots,
            max_total_skips=max_total_skips,
        ):
            window = candidate.window
            points = window.harmonic_points()
            nodes = tuple(int(point.index) for point in points)
            for evaluation in classify_completed_xabcd(window):
                key = (evaluation.pattern_id, evaluation.direction.value, nodes)
                if key in seen:
                    continue
                seen.add(key)
                predictions.append(
                    RecognitionPrediction(
                        prediction_id=(
                            f"graph:{evaluation.pattern_id}:{evaluation.direction.value}:"
                            f"S{scale}:" + "-".join(str(value) for value in nodes)
                        ),
                        pattern_id=evaluation.pattern_id,
                        direction=evaluation.direction.value,
                        labels=tuple(point.label for point in points),
                        node_indices=nodes,
                    )
                )
    return tuple(predictions)


def streaming_graph_completed_predictions(
    frame: pd.DataFrame,
    *,
    scales: tuple[int, ...],
    recent_pivots: int = 20,
    max_total_skips: int = 4,
) -> tuple[RecognitionPrediction, ...]:
    """Event-sourced completed graph predictions at their first knowable cutoff.

    Unlike final-history pivot collapse, this replays confirmed pivot events in time-of-knowledge
    order. Once a completed geometry is observable it remains an immutable historical event even
    if a later same-kind pivot replaces the live swing endpoint.
    """

    born: dict[tuple[str, str, tuple[int, ...]], RecognitionPrediction] = {}
    for scale in sorted({int(value) for value in scales}):
        events = detect_pivot_events(
            frame,
            left=scale,
            right=scale,
            scale=scale,
        )
        cutoffs = sorted({int(event.confirmed_at) for event in events})
        for cutoff in cutoffs:
            pivots = visible_confirmed_pivots(events, cutoff=cutoff)
            for candidate in iter_discovery_xabcd_windows(
                pivots,
                recent_pivots=recent_pivots,
                max_total_skips=max_total_skips,
            ):
                window = candidate.window
                points = window.harmonic_points()
                nodes = tuple(int(point.index) for point in points)
                for evaluation in classify_completed_xabcd(window):
                    key = (evaluation.pattern_id, evaluation.direction.value, nodes)
                    if key in born:
                        continue
                    born[key] = RecognitionPrediction(
                        prediction_id=(
                            f"streaming_graph:{evaluation.pattern_id}:"
                            f"{evaluation.direction.value}:S{scale}:"
                            + "-".join(str(value) for value in nodes)
                        ),
                        pattern_id=evaluation.pattern_id,
                        direction=evaluation.direction.value,
                        labels=tuple(point.label for point in points),
                        node_indices=nodes,
                        known_at=cutoff,
                    )
    return tuple(
        sorted(
            born.values(),
            key=lambda item: (
                item.known_at if item.known_at is not None else -1,
                item.prediction_id,
            ),
        )
    )


def diagnose_truth_pivot_path(
    frame: pd.DataFrame,
    truth: RecognitionTruth,
    *,
    scales: tuple[int, ...],
    recent_pivots: int = 20,
) -> dict[str, object]:
    """Describe whether known truth nodes survive the pivot layer and graph frontier.

    This is benchmark-only diagnostics. It does not change candidate generation or identity.
    """

    direction = PatternDirection(truth.direction)
    expected_kinds = (
        (PivotKind.LOW, PivotKind.HIGH, PivotKind.LOW, PivotKind.HIGH, PivotKind.LOW)
        if direction is PatternDirection.BULLISH
        else (PivotKind.HIGH, PivotKind.LOW, PivotKind.HIGH, PivotKind.LOW, PivotKind.HIGH)
    )
    expected = tuple(
        (int(index), kind)
        for index, kind in zip(truth.node_indices, expected_kinds, strict=True)
    )
    by_scale: dict[str, object] = {}
    for scale, pivots in detect_multi_scale_pivots(frame, scales=scales).items():
        keyed = {(int(pivot.index), pivot.kind): position for position, pivot in enumerate(pivots)}
        positions = tuple(keyed.get(node) for node in expected)
        all_present = all(position is not None for position in positions)
        payload: dict[str, object] = {
            "pivot_count": len(pivots),
            "all_truth_nodes_present": all_present,
            "truth_positions": list(positions),
            "recent_offset": max(0, len(pivots) - max(5, int(recent_pivots))),
        }
        if all_present:
            concrete = tuple(int(position) for position in positions if position is not None)
            steps = tuple(right - left for left, right in pairwise(concrete))
            skipped = tuple(step - 1 for step in steps)
            recent_offset = int(payload["recent_offset"])
            payload.update(
                {
                    "leg_steps": list(steps),
                    "leg_skipped_pivots": list(skipped),
                    "total_skipped_pivots": sum(skipped),
                    "max_leg_step": max(steps),
                    "all_truth_nodes_within_recent_frontier": min(concrete) >= recent_offset,
                    "current_step13_compatible": all(step in (1, 3) for step in steps),
                }
            )
        by_scale[str(scale)] = payload
    return {
        "case_id": truth.case_id,
        "recent_pivots": int(recent_pivots),
        "scales": by_scale,
    }


def diagnose_authoritative_truth(
    frame: pd.DataFrame,
    truth: RecognitionTruth,
    *,
    scales: tuple[int, ...],
) -> FailureDiagnosis:
    """Locate the first authoritative stage that loses one exact completed XABCD truth."""

    if truth.labels != ("X", "A", "B", "C", "D"):
        raise ValueError("authoritative diagnosis currently requires X/A/B/C/D truth")

    pivots_by_scale = detect_multi_scale_pivots(frame, scales=scales)
    direction = PatternDirection(truth.direction)
    expected_kinds = (
        (PivotKind.LOW, PivotKind.HIGH, PivotKind.LOW, PivotKind.HIGH, PivotKind.LOW)
        if direction is PatternDirection.BULLISH
        else (PivotKind.HIGH, PivotKind.LOW, PivotKind.HIGH, PivotKind.LOW, PivotKind.HIGH)
    )

    all_nodes_scales: list[int] = []
    exact_candidate_scales: list[int] = []
    expected_indices = tuple(int(value) for value in truth.node_indices)

    for scale, pivots in pivots_by_scale.items():
        nodes = {(int(pivot.index), pivot.kind) for pivot in pivots}
        if all(
            (index, kind) in nodes
            for index, kind in zip(expected_indices, expected_kinds, strict=True)
        ):
            all_nodes_scales.append(int(scale))

        for window in iter_completed_xabcd_windows(pivots):
            points = window.harmonic_points()
            indices = tuple(int(point.index) for point in points)
            if indices != expected_indices:
                continue
            exact_candidate_scales.append(int(scale))
            matches = classify_completed_xabcd(window)
            if any(
                item.pattern_id == truth.pattern_id
                and item.direction is direction
                for item in matches
            ):
                return FailureDiagnosis(
                    case_id=truth.case_id,
                    stage="accepted",
                    scales_with_all_truth_nodes=tuple(sorted(set(all_nodes_scales))),
                    scales_with_exact_candidate=tuple(sorted(set(exact_candidate_scales))),
                )

    if not all_nodes_scales:
        stage: FailureStage = "pivot_missing"
    elif not exact_candidate_scales:
        stage = "candidate_window_missing"
    else:
        stage = "rule_rejected"

    return FailureDiagnosis(
        case_id=truth.case_id,
        stage=stage,
        scales_with_all_truth_nodes=tuple(sorted(set(all_nodes_scales))),
        scales_with_exact_candidate=tuple(sorted(set(exact_candidate_scales))),
    )
