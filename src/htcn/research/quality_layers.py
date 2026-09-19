from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from typing import Any

from .quality_gate import (
    GateSpec,
    build_gate_library,
    evaluate_gate_library,
    gate_matches,
    outcome_metrics,
)
from .time_split import (
    assign_purged_split,
    derive_boundaries,
    learn_numeric_thresholds,
    mature_forward_records,
)

QUALITY_FEATURES = frozenset(
    {
        "source_tolerance_used",
        "scale_support_count",
        "prz_width_ratio",
    }
)
READINESS_FEATURES = frozenset(
    {
        "distance_to_prz_ratio",
        "confirmation_lag_bars",
    }
)
CONTEXT_FEATURES = frozenset(
    {
        "source_scale",
    }
)

PATTERN_FAMILIES = {
    "abcd": "ABCD",
    "gartley": "XABCD",
    "bat": "XABCD",
    "alternate_bat": "XABCD",
    "butterfly": "XABCD",
    "crab": "XABCD",
    "deep_crab": "XABCD",
    "shark": "SHARK",
    "five_zero": "FIVE_ZERO",
}


def pattern_family(pattern_id: Any) -> str:
    return PATTERN_FAMILIES.get(str(pattern_id), "OTHER")


def feature_layer(feature: str) -> str:
    if feature in QUALITY_FEATURES:
        return "quality"
    if feature in READINESS_FEATURES:
        return "readiness"
    if feature in CONTEXT_FEATURES:
        return "context"
    return "unknown"


def classify_gate_layer(spec: GateSpec) -> str:
    layers = {feature_layer(clause.feature) for clause in spec.clauses}
    layers.discard("unknown")
    if not layers:
        return "unknown"
    if len(layers) == 1:
        return next(iter(layers))
    return "mixed"


def _delta(gated: dict[str, Any], baseline: dict[str, Any], key: str) -> float | None:
    left = gated.get(key)
    right = baseline.get(key)
    if left is None or right is None:
        return None
    return float(left) - float(right)


def _metrics_with_delta(
    base_rows: list[dict[str, Any]],
    gate_rows: list[dict[str, Any]],
    *,
    horizon: int,
) -> dict[str, Any]:
    baseline = outcome_metrics(base_rows, horizon=horizon)
    gated = outcome_metrics(gate_rows, horizon=horizon)
    return {
        "baseline": baseline,
        "gated": gated,
        "touch_delta": _delta(gated, baseline, "touch_rate"),
        "retirement_delta": _delta(gated, baseline, "retirement_rate"),
        "completion_delta": _delta(gated, baseline, "completion_rate"),
    }


def _direction_ok(metrics: dict[str, Any]) -> bool:
    touch = metrics.get("touch_delta")
    retirement = metrics.get("retirement_delta")
    return bool(
        touch is not None
        and retirement is not None
        and float(touch) > 0
        and float(retirement) < 0
    )


def _top_share(values: list[str]) -> dict[str, Any]:
    if not values:
        return {
            "top_value": None,
            "top_records": 0,
            "top_share": None,
            "distribution": {},
        }
    counts = Counter(values)
    top_value, top_records = counts.most_common(1)[0]
    return {
        "top_value": top_value,
        "top_records": int(top_records),
        "top_share": float(top_records / len(values)),
        "distribution": dict(sorted(counts.items())),
    }


def _group_key(row: dict[str, Any], dimension: str) -> str:
    if dimension == "pattern_family":
        return pattern_family(row.get("pattern_id"))
    return str(row.get(dimension))


def _group_diagnostics(
    rows: list[dict[str, Any]],
    spec: GateSpec,
    *,
    dimension: str,
    horizon: int,
    min_baseline: int,
    min_gated: int,
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[_group_key(row, dimension)].append(row)

    details: list[dict[str, Any]] = []
    eligible: list[dict[str, Any]] = []
    gated_all = [row for row in rows if gate_matches(row, spec)]
    for value, members in sorted(grouped.items()):
        gated = [row for row in members if gate_matches(row, spec)]
        metrics = _metrics_with_delta(members, gated, horizon=horizon)
        item = {
            "value": value,
            "baseline_records": len(members),
            "gated_records": len(gated),
            **metrics,
        }
        item["eligible"] = len(members) >= min_baseline and len(gated) >= min_gated
        item["direction_ok"] = bool(item["eligible"] and _direction_ok(item))
        details.append(item)
        if item["eligible"]:
            eligible.append(item)

    ok = sum(bool(item["direction_ok"]) for item in eligible)
    return {
        "dimension": dimension,
        "eligible_groups": len(eligible),
        "direction_ok_groups": ok,
        "direction_ok_ratio": None if not eligible else ok / len(eligible),
        "concentration": _top_share([_group_key(row, dimension) for row in gated_all]),
        "details": details,
    }


def _stable_values(train: dict[str, Any], validation: dict[str, Any]) -> list[str]:
    train_map = {
        str(item["value"]): item
        for item in train["details"]
        if item.get("eligible") and item.get("direction_ok")
    }
    validation_map = {
        str(item["value"]): item
        for item in validation["details"]
        if item.get("eligible") and item.get("direction_ok")
    }
    return sorted(set(train_map) & set(validation_map))


def gate_generalization_diagnostics(
    train_rows: Iterable[dict[str, Any]],
    validation_rows: Iterable[dict[str, Any]],
    spec: GateSpec,
    *,
    robust: bool,
    horizon: int = 60,
) -> dict[str, Any]:
    train = list(train_rows)
    validation = list(validation_rows)

    train_pattern = _group_diagnostics(
        train,
        spec,
        dimension="pattern_id",
        horizon=horizon,
        min_baseline=20,
        min_gated=5,
    )
    validation_pattern = _group_diagnostics(
        validation,
        spec,
        dimension="pattern_id",
        horizon=horizon,
        min_baseline=20,
        min_gated=5,
    )
    train_family = _group_diagnostics(
        train,
        spec,
        dimension="pattern_family",
        horizon=horizon,
        min_baseline=30,
        min_gated=8,
    )
    validation_family = _group_diagnostics(
        validation,
        spec,
        dimension="pattern_family",
        horizon=horizon,
        min_baseline=30,
        min_gated=8,
    )
    train_scale = _group_diagnostics(
        train,
        spec,
        dimension="source_scale",
        horizon=horizon,
        min_baseline=30,
        min_gated=8,
    )
    validation_scale = _group_diagnostics(
        validation,
        spec,
        dimension="source_scale",
        horizon=horizon,
        min_baseline=30,
        min_gated=8,
    )

    pattern_generalization_ok = bool(
        train_pattern["eligible_groups"] >= 3
        and validation_pattern["eligible_groups"] >= 3
        and (train_pattern["direction_ok_ratio"] or 0.0) >= (2 / 3)
        and (validation_pattern["direction_ok_ratio"] or 0.0) >= (2 / 3)
        and (train_pattern["concentration"]["top_share"] or 1.0) <= 0.60
        and (validation_pattern["concentration"]["top_share"] or 1.0) <= 0.60
    )
    family_generalization_ok = bool(
        train_family["eligible_groups"] >= 2
        and validation_family["eligible_groups"] >= 2
        and (train_family["direction_ok_ratio"] or 0.0) >= 0.75
        and (validation_family["direction_ok_ratio"] or 0.0) >= 0.75
        and (train_family["concentration"]["top_share"] or 1.0) <= 0.70
        and (validation_family["concentration"]["top_share"] or 1.0) <= 0.70
    )
    scale_generalization_ok = bool(
        train_scale["eligible_groups"] >= 3
        and validation_scale["eligible_groups"] >= 3
        and (train_scale["direction_ok_ratio"] or 0.0) >= (2 / 3)
        and (validation_scale["direction_ok_ratio"] or 0.0) >= (2 / 3)
        and (train_scale["concentration"]["top_share"] or 1.0) <= 0.70
        and (validation_scale["concentration"]["top_share"] or 1.0) <= 0.70
    )

    semantic_layer = classify_gate_layer(spec)
    universal_quality_candidate = bool(
        robust
        and semantic_layer == "quality"
        and pattern_generalization_ok
        and family_generalization_ok
        and scale_generalization_ok
    )
    return {
        "name": spec.name,
        "semantic_layer": semantic_layer,
        "robust_input": robust,
        "pattern_generalization_ok": pattern_generalization_ok,
        "family_generalization_ok": family_generalization_ok,
        "scale_generalization_ok": scale_generalization_ok,
        "universal_quality_candidate": universal_quality_candidate,
        "stable_patterns": _stable_values(train_pattern, validation_pattern),
        "stable_families": _stable_values(train_family, validation_family),
        "stable_scales": _stable_values(train_scale, validation_scale),
        "train": {
            "pattern": train_pattern,
            "family": train_family,
            "scale": train_scale,
        },
        "validation": {
            "pattern": validation_pattern,
            "family": validation_family,
            "scale": validation_scale,
        },
    }


def build_layered_quality_report(
    records: Iterable[dict[str, Any]],
    *,
    robust_gate_names: Iterable[str] = (),
    horizon: int = 60,
    min_mature_records: int = 100,
) -> dict[str, Any]:
    """Separate structural quality, readiness and context while keeping Holdout sealed.

    Gate clauses are not redefined here. This stage only assigns semantics to the existing
    predeclared library and asks whether robust structural-quality evidence generalizes across
    pattern identities/families and pivot scales.
    """
    mature = mature_forward_records(list(records), horizon=horizon)
    if len(mature) < min_mature_records:
        return {
            "status": "insufficient_mature_records",
            "mature_records": len(mature),
            "policy_frozen": False,
            "holdout_opened": False,
        }

    boundaries = derive_boundaries(mature)
    splits, purged = assign_purged_split(mature, boundaries)
    if not splits["train"] or not splits["validation"] or not splits["holdout"]:
        return {
            "status": "insufficient_split_coverage",
            "mature_records": len(mature),
            "policy_frozen": False,
            "holdout_opened": False,
        }

    thresholds = learn_numeric_thresholds(splits["train"])
    threshold_payload = {
        "prz_width_ratio": list(thresholds.prz_width_ratio),
        "distance_to_prz_ratio": list(thresholds.distance_to_prz_ratio),
        "confirmation_lag_bars": list(thresholds.confirmation_lag_bars),
    }

    from .autonomous_calibration import gate_rows

    train = gate_rows(splits["train"])
    validation = gate_rows(splits["validation"])
    gate_evidence = evaluate_gate_library(
        train,
        validation,
        thresholds=threshold_payload,
        horizon=horizon,
    )
    strong_names = set(gate_evidence["strong_candidates"])
    robust_names = {str(name) for name in robust_gate_names}
    specs = build_gate_library(threshold_payload)
    by_layer: dict[str, list[str]] = {
        "quality": [],
        "readiness": [],
        "context": [],
        "mixed": [],
        "unknown": [],
    }
    robust_by_layer: dict[str, list[str]] = {key: [] for key in by_layer}
    quality_diagnostics: list[dict[str, Any]] = []

    for spec in specs:
        layer = classify_gate_layer(spec)
        if spec.name in strong_names:
            by_layer[layer].append(spec.name)
        if spec.name in robust_names:
            robust_by_layer[layer].append(spec.name)
        if spec.name in strong_names and layer == "quality":
            quality_diagnostics.append(
                gate_generalization_diagnostics(
                    train,
                    validation,
                    spec,
                    robust=spec.name in robust_names,
                    horizon=horizon,
                )
            )

    universal = sorted(
        item["name"] for item in quality_diagnostics if item["universal_quality_candidate"]
    )
    family_specific = {
        item["name"]: item["stable_families"]
        for item in quality_diagnostics
        if item["stable_families"]
    }
    pattern_specific = {
        item["name"]: item["stable_patterns"]
        for item in quality_diagnostics
        if item["stable_patterns"]
    }

    return {
        "status": "research_layers_holdout_sealed",
        "mature_records": len(mature),
        "purged_boundary_records": len(purged),
        "train_records": len(splits["train"]),
        "validation_records": len(splits["validation"]),
        "holdout_records_sealed": len(splits["holdout"]),
        "train_learned_thresholds": threshold_payload,
        "strong_candidates_by_layer": by_layer,
        "robust_candidates_by_layer": robust_by_layer,
        "quality_generalization": quality_diagnostics,
        "universal_quality_candidates": universal,
        "family_specific_quality_hypotheses": family_specific,
        "pattern_specific_quality_hypotheses": pattern_specific,
        "policy_frozen": False,
        "holdout_opened": False,
        "methodology": {
            "quality": (
                "Structural evidence available at signal time: source tolerance, multi-scale "
                "support and PRZ width. Quality must not include distance-to-PRZ."
            ),
            "readiness": (
                "Distance-to-PRZ and confirmation lag describe how close/ready a signal is; "
                "they are not treated as predictive geometry quality."
            ),
            "context": (
                "Source pivot scale is market/measurement context, not a universal quality score."
            ),
            "mixed": (
                "Cross-layer clauses remain research diagnostics and cannot become a universal "
                "quality policy without an explicit predeclared interaction study."
            ),
            "generalization": (
                "Universal quality requires robust evidence plus pattern, family and scale "
                "generalization; family/pattern-specific findings remain hypotheses only."
            ),
            "holdout": "Holdout outcomes are never read by this stage.",
        },
    }
