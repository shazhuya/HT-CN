from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from htcn.harmonic.recognition_benchmark import (
    diagnose_truth_pivot_path,
    hierarchical_graph_completed_predictions,
    score_predictions,
    streaming_hierarchical_graph_completed_predictions,
)
from htcn.harmonic.recognition_real_noise import (
    SyntheticRealCase,
    holdout_symbols,
    inject_pattern_into_real_background,
)
from htcn.harmonic.recognition_stress import STANDARD_XABCD
from htcn.research.snapshot_cache import load_research_snapshot

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "research" / "a-share-research-universe-v1.json"
DEFAULT_DATA_DIR = ROOT / "artifacts" / "ci-research" / "data"
REPORT_PATH = ROOT / "artifacts" / "reports" / "m9-recognition-synthetic-real-gate.json"
SCALES = (3, 5, 8)
MAX_LEG_STEP = 7
MAX_TOTAL_SKIPS = 12
HOLDOUT_COUNT = 9
CASES_PER_SYMBOL = 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    return parser.parse_args()


def _manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not payload.get("instruments"):
        raise ValueError("manifest has no instruments")
    return payload


def _case_seed(instrument_id: str, case_number: int) -> int:
    digest = hashlib.sha256(
        f"gate3:{instrument_id}:{case_number}".encode()
    ).hexdigest()
    return int(digest[:8], 16)


def _build_cases(manifest: dict[str, Any], data_dir: Path) -> tuple[list[SyntheticRealCase], list[dict[str, Any]]]:
    instruments = list(manifest["instruments"])
    ids = [str(item["instrument_id"]) for item in instruments]
    holdout = set(holdout_symbols(ids, count=HOLDOUT_COUNT))
    start = str(manifest["start_date"])
    cutoff = str(manifest["snapshot_cutoff"])
    max_bars = int(manifest["max_bars"])
    pattern_ids = tuple(STANDARD_XABCD)

    cases: list[SyntheticRealCase] = []
    failures: list[dict[str, Any]] = []
    for symbol_index, item in enumerate(instruments):
        instrument_id = str(item["instrument_id"])
        snapshot, reason = load_research_snapshot(
            data_dir,
            instrument_id=instrument_id,
            requested_start=start,
            requested_end=cutoff,
            max_bars=max_bars,
            price_mode="qfq",
        )
        if snapshot is None:
            failures.append({"instrument_id": instrument_id, "reason": reason})
            continue
        split = "holdout" if instrument_id in holdout else "development"
        for case_number in range(CASES_PER_SYMBOL):
            seed = _case_seed(instrument_id, case_number)
            pattern_id = pattern_ids[(symbol_index + case_number) % len(pattern_ids)]
            direction = "bullish" if (symbol_index + case_number) % 2 == 0 else "bearish"
            cases.append(
                inject_pattern_into_real_background(
                    snapshot.frame,
                    instrument_id=instrument_id,
                    pattern_id=pattern_id,
                    direction=direction,
                    seed=seed,
                    split=split,
                    noise_strength=0.08 if case_number == 0 else 0.12,
                )
            )
    return cases, failures


def _evaluate(cases: list[SyntheticRealCase], *, reveal_cases: bool) -> dict[str, Any]:
    totals = {"tp": 0, "fp": 0, "fn": 0, "exact": 0, "predictions": 0}
    by_pattern: dict[str, dict[str, int]] = defaultdict(
        lambda: {"cases": 0, "tp": 0, "fn": 0, "predictions": 0}
    )
    rows = []
    for case in cases:
        predictions = hierarchical_graph_completed_predictions(
            case.frame,
            scales=SCALES,
            recent_pivots=20,
            max_leg_step=MAX_LEG_STEP,
            max_total_skips=MAX_TOTAL_SKIPS,
        )
        metrics = score_predictions([case.truth], predictions, tolerance_bars=1)
        totals["tp"] += metrics.true_positive
        totals["fp"] += metrics.false_positive
        totals["fn"] += metrics.false_negative
        totals["exact"] += metrics.exact_match_count
        totals["predictions"] += len(predictions)
        bucket = by_pattern[case.pattern_id]
        bucket["cases"] += 1
        bucket["tp"] += metrics.true_positive
        bucket["fn"] += metrics.false_negative
        bucket["predictions"] += len(predictions)
        if reveal_cases:
            rows.append(
                {
                    "case_id": case.truth.case_id,
                    "instrument_id": case.instrument_id,
                    "pattern_id": case.pattern_id,
                    "direction": case.direction,
                    "source_start": case.source_start,
                    "source_end": case.source_end,
                    "prediction_count": len(predictions),
                    "tp": metrics.true_positive,
                    "fn": metrics.false_negative,
                    "exact": metrics.exact_match_count,
                }
            )
    denominator = len(cases)
    recall = totals["tp"] / (totals["tp"] + totals["fn"]) if denominator else 1.0
    return {
        "case_count": denominator,
        "true_positive": totals["tp"],
        "false_negative": totals["fn"],
        "raw_unmatched_prediction_count": totals["fp"],
        "injected_truth_recall": recall,
        "exact_node_rate": totals["exact"] / denominator if denominator else 1.0,
        "predictions_per_case": totals["predictions"] / denominator if denominator else 0.0,
        "raw_unmatched_predictions_are_not_precision_claim": True,
        "by_pattern": {
            pattern: {
                **bucket,
                "recall": bucket["tp"] / (bucket["tp"] + bucket["fn"])
                if bucket["tp"] + bucket["fn"]
                else 1.0,
                "predictions_per_case": bucket["predictions"] / bucket["cases"],
            }
            for pattern, bucket in sorted(by_pattern.items())
        },
        "cases": rows if reveal_cases else "sealed_holdout_case_details",
    }


def _pivot_path_diagnostics(
    cases: list[SyntheticRealCase],
    *,
    reveal_cases: bool,
) -> dict[str, Any]:
    rows = []
    any_present = 0
    any_recent = 0
    any_step13 = 0
    min_skip_values: list[int] = []
    min_max_step_values: list[int] = []

    for case in cases:
        diagnostic = diagnose_truth_pivot_path(
            case.frame,
            case.truth,
            scales=SCALES,
            recent_pivots=20,
        )
        scale_rows = diagnostic["scales"]
        present = [
            payload
            for payload in scale_rows.values()
            if payload["all_truth_nodes_present"]
        ]
        any_present += int(bool(present))
        any_recent += int(
            any(payload.get("all_truth_nodes_within_recent_frontier") for payload in present)
        )
        any_step13 += int(
            any(payload.get("current_step13_compatible") for payload in present)
        )
        if present:
            min_skip_values.append(
                min(int(payload["total_skipped_pivots"]) for payload in present)
            )
            min_max_step_values.append(
                min(int(payload["max_leg_step"]) for payload in present)
            )
        if reveal_cases:
            rows.append(
                {
                    "case_id": case.truth.case_id,
                    "scales": scale_rows,
                }
            )

    count = len(cases)
    return {
        "case_count": count,
        "truth_nodes_present_any_scale_rate": any_present / count if count else 1.0,
        "truth_within_recent20_any_scale_rate": any_recent / count if count else 1.0,
        "step13_compatible_any_scale_rate": any_step13 / count if count else 1.0,
        "minimum_total_skips": {
            "min": min(min_skip_values) if min_skip_values else None,
            "median": sorted(min_skip_values)[len(min_skip_values) // 2]
            if min_skip_values
            else None,
            "max": max(min_skip_values) if min_skip_values else None,
        },
        "minimum_max_leg_step": {
            "min": min(min_max_step_values) if min_max_step_values else None,
            "median": sorted(min_max_step_values)[len(min_max_step_values) // 2]
            if min_max_step_values
            else None,
            "max": max(min_max_step_values) if min_max_step_values else None,
        },
        "cases": rows if reveal_cases else "sealed_holdout_case_details",
    }


def _streaming(cases: list[SyntheticRealCase]) -> dict[str, Any]:
    selected = cases[: min(12, len(cases))]
    preserved = 0
    known_at_values: list[int] = []
    for case in selected:
        predictions = streaming_hierarchical_graph_completed_predictions(
            case.frame,
            scales=SCALES,
            recent_pivots=20,
            max_leg_step=MAX_LEG_STEP,
            max_total_skips=MAX_TOTAL_SKIPS,
        )
        metrics = score_predictions([case.truth], predictions, tolerance_bars=1)
        preserved += int(metrics.true_positive == 1)
        for prediction in predictions:
            if (
                prediction.pattern_id == case.truth.pattern_id
                and prediction.direction == case.truth.direction
                and prediction.node_indices == case.truth.node_indices
                and prediction.known_at is not None
            ):
                known_at_values.append(int(prediction.known_at))
    return {
        "case_count": len(selected),
        "truth_preserved": preserved,
        "preservation_rate": preserved / len(selected) if selected else 1.0,
        "known_at_min": min(known_at_values) if known_at_values else None,
        "known_at_max": max(known_at_values) if known_at_values else None,
    }


def main() -> int:
    args = parse_args()
    manifest = _manifest(args.manifest)
    cases, failures = _build_cases(manifest, args.data_dir)
    development = [case for case in cases if case.split == "development"]
    holdout = [case for case in cases if case.split == "holdout"]

    report = {
        "schema": 1,
        "gate_id": "recognition-synthetic-real-gate3-v3-hierarchical",
        "fixture_version": "real-noise-injection-v2-turning-guards",
        "snapshot_dataset_id": manifest.get("dataset_id"),
        "snapshot_cutoff": manifest.get("snapshot_cutoff"),
        "requested_symbols": len(manifest["instruments"]),
        "loaded_symbols": len({case.instrument_id for case in cases}),
        "snapshot_failures": failures,
        "holdout_policy": {
            "salt": "sha256-fixed-ranking",
            "holdout_count": HOLDOUT_COUNT,
            "case_details_revealed": False,
            "rule": "lowest fixed SHA256 ranks under recognition_real_noise.HOLDOUT_SALT",
        },
        "detector": {
            "scales": list(SCALES),
            "recent_pivots": 20,
            "graph": "hierarchical_swing_dominance",
            "max_leg_step": MAX_LEG_STEP,
            "max_total_skips": MAX_TOTAL_SKIPS,
        },
        "development": _evaluate(development, reveal_cases=True),
        "holdout": _evaluate(holdout, reveal_cases=False),
        "development_pivot_path_diagnostics": _pivot_path_diagnostics(
            development,
            reveal_cases=True,
        ),
        "holdout_pivot_path_diagnostics": _pivot_path_diagnostics(
            holdout,
            reveal_cases=False,
        ),
        "development_streaming": _streaming(development),
        "holdout_streaming": _streaming(holdout),
        "claims_boundary": (
            "This measures recovery of injected known harmonic truth under frozen real-A-share "
            "bar texture. Extra valid structures in a modified real background are not automatically "
            "labeled false positives. It is not a real-market semantic accuracy or profitability claim."
        ),
    }
    gates = {
        "snapshot_coverage": report["loaded_symbols"] >= 36,
        "development_recall": report["development"]["injected_truth_recall"] >= 0.90,
        "holdout_recall": report["holdout"]["injected_truth_recall"] >= 0.85,
        "development_exact_nodes": report["development"]["exact_node_rate"] >= 0.85,
        "holdout_exact_nodes": report["holdout"]["exact_node_rate"] >= 0.80,
        "development_candidate_pressure": report["development"]["predictions_per_case"] <= 4.0,
        "holdout_candidate_pressure": report["holdout"]["predictions_per_case"] <= 4.0,
        "development_streaming": report["development_streaming"]["preservation_rate"] == 1.0,
        "holdout_streaming": report["holdout_streaming"]["preservation_rate"] == 1.0,
    }
    report["gates"] = gates
    report["status"] = "pass" if all(gates.values()) else "fail"

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
