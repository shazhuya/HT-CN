from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from itertools import combinations, pairwise
from pathlib import Path
from typing import Any

import pandas as pd

from htcn.harmonic.discovery import discover_frame
from htcn.harmonic.pine_r34 import scan_pine_r34
from htcn.harmonic.recognition_benchmark import (
    RecognitionPrediction,
    RecognitionTruth,
    authoritative_predictions,
    diagnose_authoritative_truth,
    graph_completed_predictions,
    score_predictions,
)

REPORT_PATH = Path("artifacts/reports/m9-recognition-correctness-baseline.json")
CORPUS_ID = "recognition-correctness-gate0-v3"
SCALES = (3,)

STANDARD_XABCD = {
    "gartley": (100.0, 200.0, 138.2, 183.2, 121.4),
    "bat": (100.0, 200.0, 150.0, 188.6, 111.4),
    "butterfly": (100.0, 200.0, 121.4, 169.8, 73.0),
    "crab": (100.0, 200.0, 150.0, 194.3, 38.2),
    "deep_crab": (100.0, 200.0, 111.4, 156.6410383189, 38.2),
}


def _mirror(prices: tuple[float, ...], *, axis: float = 300.0) -> tuple[float, ...]:
    return tuple(axis - value for value in prices)


def _render_path(
    anchors: list[tuple[int, float]],
    *,
    rows: int,
) -> pd.DataFrame:
    closes = [0.0] * rows
    for (left_i, left_p), (right_i, right_p) in pairwise(anchors):
        if right_i <= left_i:
            raise ValueError("anchor indices must increase")
        for index in range(left_i, right_i + 1):
            fraction = (index - left_i) / (right_i - left_i)
            closes[index] = left_p + (right_p - left_p) * fraction
    return pd.DataFrame(
        {
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1000.0] * rows,
        }
    )


def _render_clean_xabcd(
    prices: tuple[float, ...],
) -> tuple[pd.DataFrame, tuple[int, ...]]:
    node_indices = (10, 30, 50, 70, 90)
    first_leg = prices[1] - prices[0]
    last_leg = prices[-1] - prices[-2]
    first_guard = prices[0] + (1.0 if first_leg > 0 else -1.0) * abs(first_leg) * 0.2
    last_guard = prices[-1] - (1.0 if last_leg > 0 else -1.0) * abs(last_leg) * 0.2
    anchors = [
        (0, first_guard),
        *zip(node_indices, prices, strict=True),
        (110, last_guard),
    ]
    return _render_path(list(anchors), rows=111), node_indices


def _render_minor_swing_xabcd(
    prices: tuple[float, ...],
) -> tuple[pd.DataFrame, tuple[int, ...]]:
    """Insert one complete minor low/high pair inside the major A->B leg.

    The major harmonic geometry is unchanged. At scale 3 the minor pair is deliberately
    confirmed as two extra pivots, so a consecutive-five-pivot detector should lose the
    major X/A/B/C/D path while a bounded graph detector may recover it.
    """

    node_indices = (10, 30, 70, 90, 110)
    x, a, b, c, d = prices
    direction_ab = 1.0 if b > a else -1.0
    span = abs(b - a)
    minor_1 = a + direction_ab * span * 0.45
    minor_2 = a + direction_ab * span * 0.28
    first_guard = x + (1.0 if a > x else -1.0) * abs(a - x) * 0.2
    last_guard = d - (1.0 if d > c else -1.0) * abs(d - c) * 0.2
    anchors = [
        (0, first_guard),
        (10, x),
        (30, a),
        (44, minor_1),
        (54, minor_2),
        (70, b),
        (90, c),
        (110, d),
        (130, last_guard),
    ]
    return _render_path(anchors, rows=131), node_indices


def _render_contaminated_xabcd(
    prices: tuple[float, ...],
    *,
    contaminated_legs: tuple[str, ...],
) -> tuple[pd.DataFrame, tuple[int, ...]]:
    """Render the same major XABCD with bounded minor pairs on selected legs."""

    labels = ("X", "A", "B", "C", "D")
    node_indices = (20, 80, 140, 200, 260)
    leg_names = ("XA", "AB", "BC", "CD")
    points = dict(zip(labels, prices, strict=True))
    indices = dict(zip(labels, node_indices, strict=True))
    anchors: list[tuple[int, float]] = []

    x, a, _, c, d = prices
    first_guard = x + (1.0 if a > x else -1.0) * abs(a - x) * 0.2
    last_guard = d - (1.0 if d > c else -1.0) * abs(d - c) * 0.2
    anchors.append((0, first_guard))
    anchors.append((node_indices[0], x))

    for leg_name, left_label, right_label in zip(
        leg_names,
        labels[:-1],
        labels[1:],
        strict=True,
    ):
        left_i = indices[left_label]
        right_i = indices[right_label]
        left_p = points[left_label]
        right_p = points[right_label]
        if leg_name in contaminated_legs:
            direction = 1.0 if right_p > left_p else -1.0
            span = abs(right_p - left_p)
            anchors.extend(
                [
                    (left_i + 20, left_p + direction * span * 0.45),
                    (left_i + 40, left_p + direction * span * 0.28),
                ]
            )
        anchors.append((right_i, right_p))

    anchors.append((300, last_guard))
    return _render_path(anchors, rows=301), node_indices


def _minor_swing_matrix_cases():
    leg_names = ("XA", "AB", "BC", "CD")
    contamination_sets = [
        (leg,)
        for leg in leg_names
    ] + list(combinations(leg_names, 2))
    for pattern_id, prices in STANDARD_XABCD.items():
        for direction, oriented in (
            ("bullish", prices),
            ("bearish", _mirror(prices)),
        ):
            for contaminated_legs in contamination_sets:
                frame, indices = _render_contaminated_xabcd(
                    oriented,
                    contaminated_legs=tuple(contaminated_legs),
                )
                leg_key = "+".join(contaminated_legs)
                yield (
                    _truth(
                        case_id=(
                            f"minor_matrix:{leg_key}:{pattern_id}:{direction}"
                        ),
                        pattern_id=pattern_id,
                        direction=direction,
                        indices=indices,
                    ),
                    frame,
                )


def _render_hard_negative(
    prices: tuple[float, ...],
) -> pd.DataFrame:
    x, a, b, c, _ = prices
    direction = 1.0 if a > x else -1.0
    xa = abs(a - x)
    # 0.70 XA is intentionally away from every supported standard completion family
    # for the source-shaped B values used in this corpus.
    invalid_d = a - direction * xa * 0.70
    return _render_clean_xabcd((x, a, b, c, invalid_d))[0]


def _truth(
    *,
    case_id: str,
    pattern_id: str,
    direction: str,
    indices: tuple[int, ...],
) -> RecognitionTruth:
    return RecognitionTruth(
        case_id=case_id,
        pattern_id=pattern_id,
        direction=direction,
        labels=("X", "A", "B", "C", "D"),
        node_indices=indices,
    )


def _positive_cases(kind: str):
    renderer = (
        _render_clean_xabcd
        if kind == "clean"
        else _render_minor_swing_xabcd
    )
    for pattern_id, prices in STANDARD_XABCD.items():
        for direction, oriented in (
            ("bullish", prices),
            ("bearish", _mirror(prices)),
        ):
            frame, indices = renderer(oriented)
            yield (
                _truth(
                    case_id=f"{kind}:{pattern_id}:{direction}",
                    pattern_id=pattern_id,
                    direction=direction,
                    indices=indices,
                ),
                frame,
            )


def _hard_negative_cases():
    for pattern_id, prices in STANDARD_XABCD.items():
        for direction, oriented in (
            ("bullish", prices),
            ("bearish", _mirror(prices)),
        ):
            yield (
                f"hard_negative:{pattern_id}:{direction}",
                _render_hard_negative(oriented),
            )


def _pine_prefix_predictions(frame: pd.DataFrame) -> tuple[RecognitionPrediction, ...]:
    scan = scan_pine_r34(frame, scales=SCALES)
    return tuple(
        RecognitionPrediction(
            prediction_id=(
                f"pine_r34:{item.pattern_id}:{item.direction}:"
                + "-".join(str(node.index) for node in item.source_nodes)
            ),
            pattern_id=item.pattern_id,
            direction="bullish" if item.direction == 1 else "bearish",
            labels=tuple(item.source_labels),
            node_indices=tuple(int(node.index) for node in item.source_nodes),
        )
        for item in scan.candidates
        if not item.research_only and item.schema == "XABCD"
    )


def _graph_prefix_predictions(frame: pd.DataFrame) -> tuple[RecognitionPrediction, ...]:
    scan = discover_frame(
        frame,
        scales=SCALES,
        max_candidates=200,
        recent_pivots=18,
        max_total_skips=4,
    )
    return tuple(
        RecognitionPrediction(
            prediction_id=(
                f"extended_graph:{item.pattern_id}:{item.direction.value}:"
                + "-".join(str(point.index) for point in item.points)
            ),
            pattern_id=item.pattern_id,
            direction=item.direction.value,
            labels=tuple(point.label for point in item.points),
            node_indices=tuple(int(point.index) for point in item.points),
        )
        for item in scan.candidates
    )


def _prefix_recovery(
    truth: RecognitionTruth,
    predictions: tuple[RecognitionPrediction, ...],
) -> dict[str, Any]:
    expected_nodes = truth.node_indices[:4]
    expected_labels = truth.labels[:4]
    same_nodes = [
        prediction
        for prediction in predictions
        if prediction.direction == truth.direction
        and prediction.labels == expected_labels
        and prediction.node_indices == expected_nodes
    ]
    expected_family = [
        prediction
        for prediction in same_nodes
        if prediction.pattern_id == truth.pattern_id
    ]
    return {
        "node_path_recovered": bool(same_nodes),
        "expected_family_recovered": bool(expected_family),
        "family_count_on_truth_nodes": len(same_nodes),
        "families_on_truth_nodes": sorted(
            {prediction.pattern_id for prediction in same_nodes}
        ),
        "total_predictions": len(predictions),
    }


def _completed_metrics(cases, predictor=authoritative_predictions) -> dict[str, Any]:
    rows = []
    diagnoses = []
    total_tp = total_fp = total_fn = exact = 0
    node_errors: list[int] = []
    for truth, frame in cases:
        predictions = predictor(frame, scales=SCALES)
        metrics = score_predictions(
            [truth],
            predictions,
            tolerance_bars=1,
        )
        total_tp += metrics.true_positive
        total_fp += metrics.false_positive
        total_fn += metrics.false_negative
        exact += metrics.exact_match_count
        node_errors.extend(
            abs(error)
            for match in metrics.matches
            for error in match.node_offsets
        )
        rows.append({"case_id": truth.case_id, **_metric_payload(metrics)})
        diagnoses.append(
            asdict(
                diagnose_authoritative_truth(
                    frame,
                    truth,
                    scales=SCALES,
                )
            )
        )

    precision = total_tp / (total_tp + total_fp) if total_tp + total_fp else 1.0
    recall = total_tp / (total_tp + total_fn) if total_tp + total_fn else 1.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    stages: dict[str, int] = {}
    for row in diagnoses:
        stage = str(row["stage"])
        stages[stage] = stages.get(stage, 0) + 1
    return {
        "truth_count": len(cases),
        "prediction_count": total_tp + total_fp,
        "true_positive": total_tp,
        "false_positive": total_fp,
        "false_negative": total_fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "exact_match_count": exact,
        "exact_match_rate": exact / len(cases) if cases else 1.0,
        "node_mae_bars": (
            sum(node_errors) / len(node_errors)
            if node_errors
            else None
        ),
        "failure_stage_counts": stages,
        "diagnoses": diagnoses,
        "cases": rows,
    }


def _prefix_channel(cases, predictor) -> dict[str, Any]:
    rows = []
    node_hits = family_hits = ambiguous = 0
    for truth, frame in cases:
        recovery = _prefix_recovery(truth, predictor(frame))
        node_hits += int(recovery["node_path_recovered"])
        family_hits += int(recovery["expected_family_recovered"])
        ambiguous += int(recovery["family_count_on_truth_nodes"] > 1)
        rows.append({"case_id": truth.case_id, **recovery})
    count = len(cases)
    return {
        "truth_count": count,
        "node_path_recovery_rate": node_hits / count if count else 1.0,
        "expected_family_recovery_rate": family_hits / count if count else 1.0,
        "ambiguous_family_case_count": ambiguous,
        "pattern_precision_interpretable": False,
        "note": (
            "XABC is pre-completion: multiple valid completion families can share the same "
            "source nodes. Family multiplicity is reported, not mislabeled as false positive."
        ),
        "cases": rows,
    }


def _hard_negative_metrics(cases, predictor=authoritative_predictions) -> dict[str, Any]:
    rows = []
    false_positive = 0
    for case_id, frame in cases:
        predictions = predictor(frame, scales=SCALES)
        count = len(predictions)
        false_positive += count
        rows.append(
            {
                "case_id": case_id,
                "prediction_count": count,
                "predicted_patterns": sorted(
                    {prediction.pattern_id for prediction in predictions}
                ),
            }
        )
    return {
        "case_count": len(cases),
        "false_positive": false_positive,
        "clean_rejection_rate": (
            sum(row["prediction_count"] == 0 for row in rows) / len(rows)
            if rows
            else 1.0
        ),
        "cases": rows,
    }


def _corpus_fingerprint(groups) -> str:
    payload = []
    for group_name, cases in groups:
        for item in cases:
            if len(item) == 2 and isinstance(item[0], RecognitionTruth):
                truth, frame = item
                identity: Any = asdict(truth)
            else:
                case_id, frame = item
                identity = {"case_id": case_id, "expected": "no_standard_xabcd"}
            payload.append(
                {
                    "group": group_name,
                    "identity": identity,
                    "ohlc": frame[["open", "high", "low", "close"]]
                    .round(10)
                    .values.tolist(),
                }
            )
    material = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _metric_payload(metrics) -> dict[str, Any]:
    return {
        "truth_count": metrics.truth_count,
        "prediction_count": metrics.prediction_count,
        "true_positive": metrics.true_positive,
        "false_positive": metrics.false_positive,
        "false_negative": metrics.false_negative,
        "precision": metrics.precision,
        "recall": metrics.recall,
        "f1": metrics.f1,
        "exact_match_count": metrics.exact_match_count,
        "exact_match_rate": metrics.exact_match_rate,
        "tolerant_match_rate": metrics.tolerant_match_rate,
        "node_mae_bars": metrics.node_mae_bars,
        "node_mae_by_label": metrics.node_mae_by_label,
    }


def build_report() -> dict[str, Any]:
    clean = list(_positive_cases("clean"))
    minor = list(_positive_cases("minor_swing"))
    negatives = list(_hard_negative_cases())
    minor_matrix = list(_minor_swing_matrix_cases())
    groups = [
        ("clean_positive", clean),
        ("minor_swing_positive", minor),
        ("minor_swing_matrix", minor_matrix),
        ("hard_negative", negatives),
    ]
    return {
        "schema": 2,
        "benchmark_id": CORPUS_ID,
        "corpus_sha256": _corpus_fingerprint(groups),
        "scope": {
            "clean_positive_cases": len(clean),
            "minor_swing_positive_cases": len(minor),
            "hard_negative_cases": len(negatives),
            "minor_swing_matrix_cases": len(minor_matrix),
            "standard_patterns": sorted(STANDARD_XABCD),
            "directions": ["bullish", "bearish"],
            "pivot_scales": list(SCALES),
            "real_market_accuracy_claim_allowed": False,
            "hard_negative_gate_complete": True,
            "note": (
                "Gate 0 controlled benchmark. It tests exact known-node recovery, one bounded "
                "minor-swing contamination and near-pattern rejection. It is not a real-market "
                "semantic accuracy estimate."
            ),
        },
        "authoritative_clean_completed_xabcd": _completed_metrics(clean),
        "authoritative_minor_swing_completed_xabcd": _completed_metrics(minor),
        "authoritative_hard_negative": _hard_negative_metrics(negatives),
        "authoritative_minor_swing_matrix": _completed_metrics(minor_matrix),
        "graph_minor_swing_matrix": _completed_metrics(
            minor_matrix,
            graph_completed_predictions,
        ),
        "graph_clean_completed_xabcd": _completed_metrics(
            clean,
            graph_completed_predictions,
        ),
        "graph_minor_swing_completed_xabcd": _completed_metrics(
            minor,
            graph_completed_predictions,
        ),
        "graph_hard_negative": _hard_negative_metrics(
            negatives,
            graph_completed_predictions,
        ),
        "pine_r34_clean_xabc": _prefix_channel(clean, _pine_prefix_predictions),
        "pine_r34_minor_swing_xabc": _prefix_channel(minor, _pine_prefix_predictions),
        "extended_graph_clean_xabc": _prefix_channel(clean, _graph_prefix_predictions),
        "extended_graph_minor_swing_xabc": _prefix_channel(
            minor,
            _graph_prefix_predictions,
        ),
    }


def main() -> int:
    report = build_report()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"[HT-CN recognition baseline] report={REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
