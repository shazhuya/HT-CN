from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from htcn.harmonic.recognition_benchmark import graph_completed_predictions
from htcn.harmonic.recognition_oracle import oracle_pattern_ids
from htcn.harmonic.recognition_stress import (
    negative_stress_cases,
    positive_stress_cases,
)

REPORT_PATH = Path("artifacts/reports/m9-recognition-oracle-gate.json")
SCALES = (3, 5, 8)
MAX_TOTAL_SKIPS = 6


def _prices_for_prediction(frame, prediction) -> tuple[float, float, float, float, float]:
    values = tuple(
        float(frame.iloc[index]["close"])
        for index in prediction.node_indices
    )
    if len(values) != 5:
        raise ValueError("standard XABCD oracle expects five prediction nodes")
    return values


def build_report() -> dict[str, Any]:
    positives = positive_stress_cases(seeds_per_depth=4)
    negatives = negative_stress_cases(copies_per_kind=10)

    production_predictions = 0
    oracle_valid_predictions = 0
    disagreements = []
    nested_or_multi_valid = 0

    for case in positives:
        predictions = graph_completed_predictions(
            case.frame,
            scales=SCALES,
            max_total_skips=MAX_TOTAL_SKIPS,
        )
        production_predictions += len(predictions)
        valid_in_case = 0
        for prediction in predictions:
            prices = _prices_for_prediction(case.frame, prediction)
            oracle_ids = oracle_pattern_ids(prices)
            valid = prediction.pattern_id in oracle_ids
            oracle_valid_predictions += int(valid)
            valid_in_case += int(valid)
            if not valid:
                disagreements.append(
                    {
                        "case_id": case.truth.case_id,
                        "prediction_id": prediction.prediction_id,
                        "pattern_id": prediction.pattern_id,
                        "node_indices": list(prediction.node_indices),
                        "oracle_pattern_ids": list(oracle_ids),
                        "prices": list(prices),
                    }
                )
        nested_or_multi_valid += int(valid_in_case > 1)

    negative_predictions = 0
    negative_oracle_valid = 0
    negative_rows = []
    for case in negatives:
        predictions = graph_completed_predictions(
            case.frame,
            scales=SCALES,
            max_total_skips=MAX_TOTAL_SKIPS,
        )
        negative_predictions += len(predictions)
        valid_count = 0
        for prediction in predictions:
            prices = _prices_for_prediction(case.frame, prediction)
            valid_count += int(prediction.pattern_id in oracle_pattern_ids(prices))
        negative_oracle_valid += valid_count
        negative_rows.append(
            {
                "case_id": case.case_id,
                "production_predictions": len(predictions),
                "oracle_valid_predictions": valid_count,
            }
        )

    return {
        "schema": 1,
        "gate_id": "recognition-rule-oracle-gate2-v1",
        "scope": {
            "positive_cases": len(positives),
            "negative_cases": len(negatives),
            "scales": list(SCALES),
            "max_total_skips": MAX_TOTAL_SKIPS,
            "oracle_independence": (
                "recognition_oracle.py imports no production rules/evaluator/scanner/discovery/engine"
            ),
            "precision_claim_allowed": False,
            "note": (
                "This gate independently validates standard-XABCD identity of every production "
                "graph prediction. It resolves rule-semantic disagreements and nested valid "
                "geometries; it does not by itself label every plausible raw-market path."
            ),
        },
        "positive_production_predictions": production_predictions,
        "positive_oracle_valid_predictions": oracle_valid_predictions,
        "positive_oracle_agreement_rate": (
            oracle_valid_predictions / production_predictions
            if production_predictions
            else 1.0
        ),
        "positive_cases_with_multiple_oracle_valid_predictions": nested_or_multi_valid,
        "identity_disagreement_count": len(disagreements),
        "identity_disagreements": disagreements,
        "negative_production_predictions": negative_predictions,
        "negative_oracle_valid_predictions": negative_oracle_valid,
        "negative_cases": negative_rows,
        "gate_pass": (
            len(disagreements) == 0
            and negative_predictions == 0
            and negative_oracle_valid == 0
        ),
    }


def main() -> int:
    report = build_report()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"[HT-CN recognition oracle] report={REPORT_PATH}")
    return 0 if report["gate_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
