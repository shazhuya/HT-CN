from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from htcn.harmonic.recognition_benchmark import (
    graph_completed_predictions,
    score_predictions,
    streaming_graph_completed_predictions,
)
from htcn.harmonic.recognition_stress import (
    append_future_replacement_tail,
    corpus_fingerprint,
    negative_stress_cases,
    positive_stress_cases,
)

REPORT_PATH = Path("artifacts/reports/m9-recognition-adversarial-gate.json")
CORPUS_ID = "recognition-adversarial-gate1-v1"
SINGLE_SCALE = (3,)
MULTI_SCALE = (3, 5, 8)


def _positive_metrics(
    cases,
    *,
    scales: tuple[int, ...],
    max_total_skips: int = 4,
) -> dict[str, Any]:
    total_tp = total_fp = total_fn = exact = 0
    prediction_total = 0
    node_errors: list[int] = []
    by_depth: dict[int, dict[str, int]] = defaultdict(
        lambda: {"cases": 0, "tp": 0, "fp": 0, "fn": 0, "predictions": 0}
    )
    rows = []

    for case in cases:
        predictions = graph_completed_predictions(
            case.frame,
            scales=scales,
            max_total_skips=max_total_skips,
        )
        metrics = score_predictions([case.truth], predictions, tolerance_bars=1)
        total_tp += metrics.true_positive
        total_fp += metrics.false_positive
        total_fn += metrics.false_negative
        exact += metrics.exact_match_count
        prediction_total += len(predictions)
        node_errors.extend(
            abs(offset)
            for match in metrics.matches
            for offset in match.node_offsets
        )
        bucket = by_depth[case.minor_pairs]
        bucket["cases"] += 1
        bucket["tp"] += metrics.true_positive
        bucket["fp"] += metrics.false_positive
        bucket["fn"] += metrics.false_negative
        bucket["predictions"] += len(predictions)
        rows.append(
            {
                "case_id": case.truth.case_id,
                "minor_pairs": case.minor_pairs,
                "contaminated_legs": list(case.contaminated_legs),
                "predictions": len(predictions),
                "tp": metrics.true_positive,
                "fp": metrics.false_positive,
                "fn": metrics.false_negative,
                "exact": metrics.exact_match_count,
                "prediction_details": [
                    {
                        "pattern_id": item.pattern_id,
                        "direction": item.direction,
                        "node_indices": list(item.node_indices),
                    }
                    for item in predictions
                ],
            }
        )

    precision = total_tp / (total_tp + total_fp) if total_tp + total_fp else 1.0
    recall = total_tp / (total_tp + total_fn) if total_tp + total_fn else 1.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    depth_rows = {}
    for depth, bucket in sorted(by_depth.items()):
        depth_recall = (
            bucket["tp"] / (bucket["tp"] + bucket["fn"])
            if bucket["tp"] + bucket["fn"]
            else 1.0
        )
        depth_precision = (
            bucket["tp"] / (bucket["tp"] + bucket["fp"])
            if bucket["tp"] + bucket["fp"]
            else 1.0
        )
        depth_rows[str(depth)] = {
            **bucket,
            "precision": depth_precision,
            "recall": depth_recall,
            "predictions_per_case": bucket["predictions"] / bucket["cases"],
        }

    return {
        "case_count": len(cases),
        "prediction_count": prediction_total,
        "true_positive": total_tp,
        "false_positive": total_fp,
        "false_negative": total_fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "exact_match_rate": exact / len(cases) if cases else 1.0,
        "node_mae_bars": sum(node_errors) / len(node_errors) if node_errors else None,
        "predictions_per_case": prediction_total / len(cases) if cases else 0.0,
        "by_minor_pair_depth": depth_rows,
        "cases": rows,
    }


def _negative_metrics(
    cases,
    *,
    scales: tuple[int, ...],
    max_total_skips: int = 4,
) -> dict[str, Any]:
    total_predictions = 0
    by_kind: dict[str, dict[str, int]] = defaultdict(
        lambda: {"cases": 0, "predictions": 0, "clean": 0}
    )
    rows = []
    for case in cases:
        predictions = graph_completed_predictions(
            case.frame,
            scales=scales,
            max_total_skips=max_total_skips,
        )
        count = len(predictions)
        total_predictions += count
        bucket = by_kind[case.kind]
        bucket["cases"] += 1
        bucket["predictions"] += count
        bucket["clean"] += int(count == 0)
        rows.append(
            {
                "case_id": case.case_id,
                "kind": case.kind,
                "prediction_count": count,
                "patterns": sorted({item.pattern_id for item in predictions}),
            }
        )
    return {
        "case_count": len(cases),
        "false_positive_predictions": total_predictions,
        "clean_rejection_rate": (
            sum(row["prediction_count"] == 0 for row in rows) / len(rows)
            if rows
            else 1.0
        ),
        "by_kind": {
            kind: {
                **bucket,
                "clean_rejection_rate": bucket["clean"] / bucket["cases"],
            }
            for kind, bucket in sorted(by_kind.items())
        },
        "cases": rows,
    }


def _streaming_metrics(cases) -> dict[str, Any]:
    rows = []
    preserved = 0
    final_history_mutated = 0
    for case in cases:
        tailed = append_future_replacement_tail(case.frame, case.truth)
        prefix_metrics = score_predictions(
            [case.truth],
            graph_completed_predictions(case.frame, scales=SINGLE_SCALE),
            tolerance_bars=0,
        )
        final_metrics = score_predictions(
            [case.truth],
            graph_completed_predictions(tailed, scales=SINGLE_SCALE),
            tolerance_bars=0,
        )
        streaming_predictions = streaming_graph_completed_predictions(
            tailed,
            scales=SINGLE_SCALE,
        )
        streaming_metrics = score_predictions(
            [case.truth],
            streaming_predictions,
            tolerance_bars=0,
        )
        prefix_ok = prefix_metrics.true_positive == 1
        final_ok = final_metrics.true_positive == 1
        streaming_ok = streaming_metrics.true_positive == 1
        preserved += int(prefix_ok and streaming_ok)
        final_history_mutated += int(prefix_ok and not final_ok)
        known_at_values = [
            item.known_at
            for item in streaming_predictions
            if item.pattern_id == case.truth.pattern_id
            and item.direction == case.truth.direction
            and item.node_indices == case.truth.node_indices
        ]
        rows.append(
            {
                "case_id": case.truth.case_id,
                "prefix_found": prefix_ok,
                "final_history_found": final_ok,
                "streaming_found": streaming_ok,
                "known_at": min(known_at_values) if known_at_values else None,
            }
        )
    denominator = len(cases)
    return {
        "case_count": denominator,
        "streaming_preservation_rate": preserved / denominator if denominator else 1.0,
        "final_history_mutation_count": final_history_mutated,
        "confirmed_history_mutation_count": denominator - preserved,
        "cases": rows,
    }


def build_report() -> dict[str, Any]:
    positives = positive_stress_cases(seeds_per_depth=4)
    negatives = negative_stress_cases(copies_per_kind=10)
    streaming_cases = tuple(case for case in positives if case.minor_pairs <= 2)[:24]

    return {
        "schema": 1,
        "benchmark_id": CORPUS_ID,
        "corpus_sha256": corpus_fingerprint(positives, negatives),
        "scope": {
            "positive_cases": len(positives),
            "negative_cases": len(negatives),
            "streaming_cases": len(streaming_cases),
            "positive_minor_pairs": [1, 2, 3],
            "single_scale": list(SINGLE_SCALE),
            "multi_scale": list(MULTI_SCALE),
            "real_market_accuracy_claim_allowed": False,
            "note": (
                "Deterministic adversarial Gate 1. Randomized minor-swing amplitude/time placement, "
                "1/2/3-pair contamination, independent B/C/D near-miss negatives, multi-scale pressure "
                "and future-tail streaming invariance. This remains controlled ground truth."
            ),
        },
        "single_scale_graph_skip4": _positive_metrics(
            positives,
            scales=SINGLE_SCALE,
            max_total_skips=4,
        ),
        "multi_scale_graph_skip4": _positive_metrics(
            positives,
            scales=MULTI_SCALE,
            max_total_skips=4,
        ),
        "single_scale_graph_skip6": _positive_metrics(
            positives,
            scales=SINGLE_SCALE,
            max_total_skips=6,
        ),
        "multi_scale_graph_skip6": _positive_metrics(
            positives,
            scales=MULTI_SCALE,
            max_total_skips=6,
        ),
        "single_scale_negatives_skip4": _negative_metrics(
            negatives,
            scales=SINGLE_SCALE,
            max_total_skips=4,
        ),
        "multi_scale_negatives_skip4": _negative_metrics(
            negatives,
            scales=MULTI_SCALE,
            max_total_skips=4,
        ),
        "single_scale_negatives_skip6": _negative_metrics(
            negatives,
            scales=SINGLE_SCALE,
            max_total_skips=6,
        ),
        "multi_scale_negatives_skip6": _negative_metrics(
            negatives,
            scales=MULTI_SCALE,
            max_total_skips=6,
        ),
        "streaming_future_tail": _streaming_metrics(streaming_cases),
    }


def main() -> int:
    report = build_report()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"[HT-CN recognition adversarial] report={REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
