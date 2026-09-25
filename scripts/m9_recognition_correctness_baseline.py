from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from itertools import pairwise
from pathlib import Path

import pandas as pd

from htcn.harmonic.pine_r34 import scan_pine_r34
from htcn.harmonic.recognition_benchmark import (
    RecognitionPrediction,
    RecognitionTruth,
    authoritative_predictions,
    diagnose_authoritative_truth,
    score_predictions,
)

REPORT_PATH = Path("artifacts/reports/m9-recognition-correctness-baseline.json")
CORPUS_ID = "recognition-correctness-smoke-v1"
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


def _render_xabcd(prices: tuple[float, ...]) -> tuple[pd.DataFrame, tuple[int, ...]]:
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

    closes = [0.0] * 111
    for (left_i, left_p), (right_i, right_p) in pairwise(anchors):
        for index in range(left_i, right_i + 1):
            fraction = (index - left_i) / (right_i - left_i)
            closes[index] = left_p + (right_p - left_p) * fraction

    frame = pd.DataFrame(
        {
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1000.0] * len(closes),
        }
    )
    return frame, node_indices


def _positive_cases():
    for pattern_id, prices in STANDARD_XABCD.items():
        for direction, oriented in (
            ("bullish", prices),
            ("bearish", _mirror(prices)),
        ):
            frame, indices = _render_xabcd(oriented)
            yield (
                RecognitionTruth(
                    case_id=f"{pattern_id}:{direction}",
                    pattern_id=pattern_id,
                    direction=direction,
                    labels=("X", "A", "B", "C", "D"),
                    node_indices=indices,
                ),
                frame,
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


def _corpus_fingerprint(cases) -> str:
    payload = [
        {
            "truth": asdict(truth),
            "ohlc": frame[["open", "high", "low", "close"]].round(10).values.tolist(),
        }
        for truth, frame in cases
    ]
    material = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def build_report() -> dict:
    cases = list(_positive_cases())
    authoritative_truths = [truth for truth, _ in cases]
    authoritative_predictions_all: list[RecognitionPrediction] = []
    diagnoses = []

    # Each generated case is a separate market path. Prediction ids are case-prefixed so
    # one-to-one matching cannot accidentally cross-credit identical node coordinates.
    scoped_truths: list[RecognitionTruth] = []
    for truth, frame in cases:
        scoped_truth = RecognitionTruth(
            case_id=truth.case_id,
            pattern_id=truth.pattern_id,
            direction=truth.direction,
            labels=truth.labels,
            node_indices=truth.node_indices,
        )
        scoped_truths.append(scoped_truth)
        for prediction in authoritative_predictions(frame, scales=SCALES):
            authoritative_predictions_all.append(
                RecognitionPrediction(
                    prediction_id=f"{truth.case_id}|{prediction.prediction_id}",
                    pattern_id=prediction.pattern_id,
                    direction=prediction.direction,
                    labels=prediction.labels,
                    node_indices=prediction.node_indices,
                )
            )
        diagnoses.append(asdict(diagnose_authoritative_truth(frame, truth, scales=SCALES)))

    # Score case-by-case to prevent a prediction from one independent path matching a truth
    # from another path that happens to share the same synthetic bar coordinates.
    per_case_authoritative = []
    for truth, frame in cases:
        metrics = score_predictions(
            [truth],
            authoritative_predictions(frame, scales=SCALES),
            tolerance_bars=1,
        )
        per_case_authoritative.append((truth.case_id, metrics))

    total_tp = sum(item.true_positive for _, item in per_case_authoritative)
    total_fp = sum(item.false_positive for _, item in per_case_authoritative)
    total_fn = sum(item.false_negative for _, item in per_case_authoritative)
    precision = total_tp / (total_tp + total_fp) if total_tp + total_fp else 1.0
    recall = total_tp / (total_tp + total_fn) if total_tp + total_fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    exact = sum(item.exact_match_count for _, item in per_case_authoritative)
    matched_node_errors = [
        error
        for _, item in per_case_authoritative
        for match in item.matches
        for error in map(abs, match.node_offsets)
    ]

    pine_case_rows = []
    pine_tp = pine_fp = pine_fn = pine_exact = 0
    pine_errors: list[int] = []
    for truth, frame in cases:
        prefix_truth = RecognitionTruth(
            case_id=truth.case_id,
            pattern_id=truth.pattern_id,
            direction=truth.direction,
            labels=("X", "A", "B", "C"),
            node_indices=truth.node_indices[:4],
        )
        metrics = score_predictions(
            [prefix_truth],
            _pine_prefix_predictions(frame),
            tolerance_bars=1,
        )
        pine_case_rows.append({"case_id": truth.case_id, **_metric_payload(metrics)})
        pine_tp += metrics.true_positive
        pine_fp += metrics.false_positive
        pine_fn += metrics.false_negative
        pine_exact += metrics.exact_match_count
        pine_errors.extend(
            abs(error)
            for match in metrics.matches
            for error in match.node_offsets
        )

    stage_counts: dict[str, int] = {}
    for row in diagnoses:
        stage = str(row["stage"])
        stage_counts[stage] = stage_counts.get(stage, 0) + 1

    return {
        "schema": 1,
        "benchmark_id": CORPUS_ID,
        "corpus_sha256": _corpus_fingerprint(cases),
        "scope": {
            "positive_cases": len(cases),
            "standard_patterns": sorted(STANDARD_XABCD),
            "directions": ["bullish", "bearish"],
            "pivot_scales": list(SCALES),
            "real_market_accuracy_claim_allowed": False,
            "hard_negative_gate_complete": False,
            "note": (
                "Gate 0 smoke baseline only. This measures controlled known-node recovery; "
                "it does not establish real-market semantic accuracy."
            ),
        },
        "authoritative_completed_xabcd": {
            "truth_count": len(cases),
            "prediction_count": total_tp + total_fp,
            "true_positive": total_tp,
            "false_positive": total_fp,
            "false_negative": total_fn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "exact_match_count": exact,
            "exact_match_rate": exact / len(cases),
            "node_mae_bars": (
                sum(matched_node_errors) / len(matched_node_errors)
                if matched_node_errors
                else None
            ),
            "failure_stage_counts": stage_counts,
            "diagnoses": diagnoses,
            "cases": [
                {"case_id": case_id, **_metric_payload(metrics)}
                for case_id, metrics in per_case_authoritative
            ],
        },
        "pine_r34_projected_xabc": {
            "truth_count": len(cases),
            "prediction_count": pine_tp + pine_fp,
            "true_positive": pine_tp,
            "false_positive": pine_fp,
            "false_negative": pine_fn,
            "precision": pine_tp / (pine_tp + pine_fp) if pine_tp + pine_fp else 1.0,
            "recall": pine_tp / (pine_tp + pine_fn) if pine_tp + pine_fn else 1.0,
            "f1": (
                2
                * (pine_tp / (pine_tp + pine_fp))
                * (pine_tp / (pine_tp + pine_fn))
                / (
                    (pine_tp / (pine_tp + pine_fp))
                    + (pine_tp / (pine_tp + pine_fn))
                )
                if pine_tp and (pine_tp + pine_fp) and (pine_tp + pine_fn)
                else 0.0
            ),
            "exact_match_count": pine_exact,
            "exact_match_rate": pine_exact / len(cases),
            "node_mae_bars": (
                sum(pine_errors) / len(pine_errors)
                if pine_errors
                else None
            ),
            "cases": pine_case_rows,
        },
    }


def _metric_payload(metrics) -> dict:
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
