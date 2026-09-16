from __future__ import annotations

from dataclasses import dataclass
from math import isnan
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class GateClause:
    feature: str
    op: str
    value: Any


@dataclass(frozen=True, slots=True)
class GateSpec:
    name: str
    description: str
    clauses: tuple[GateClause, ...]


def _missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(isnan(float(value)))
    except (TypeError, ValueError):
        return False


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not _missing(value):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _compare(actual: Any, op: str, expected: Any) -> bool:
    if op == "eq":
        if isinstance(expected, bool):
            return _as_bool(actual) is expected
        return actual == expected
    if _missing(actual):
        return False
    left = float(actual)
    right = float(expected)
    if op == "ge":
        return left >= right
    if op == "le":
        return left <= right
    raise ValueError(f"unsupported gate op: {op}")


def gate_matches(row: dict[str, Any], spec: GateSpec) -> bool:
    return all(_compare(row.get(clause.feature), clause.op, clause.value) for clause in spec.clauses)


def build_gate_library(thresholds: dict[str, list[float] | tuple[float, ...]]) -> tuple[GateSpec, ...]:
    """Return a small predeclared gate library using TRAIN-learned thresholds only.

    The library is intentionally conservative. It does not search arbitrary numeric cutoffs,
    pattern-specific combinations, or outcome-derived features. Validation may confirm or
    reject a gate, but it never changes the clause definition.
    """
    width = tuple(float(v) for v in thresholds["prz_width_ratio"])
    distance = tuple(float(v) for v in thresholds["distance_to_prz_ratio"])
    lag = tuple(float(v) for v in thresholds["confirmation_lag_bars"])
    if min(len(width), len(distance), len(lag)) < 2:
        raise ValueError("quality-gate thresholds require at least Q1/Q2 values")

    c = GateClause
    specs = [
        GateSpec("canonical_only", "Do not use source tolerance.", (c("source_tolerance_used", "eq", False),)),
        GateSpec("multiscale_ge2", "At least two configured pivot scales support the signal.", (c("scale_support_count", "ge", 2),)),
        GateSpec("scale_ge5", "Source pivot scale is at least 5.", (c("source_scale", "ge", 5),)),
        GateSpec("scale_ge8", "Source pivot scale is at least 8.", (c("source_scale", "ge", 8),)),
        GateSpec("scale_ge13", "Source pivot scale is at least 13.", (c("source_scale", "ge", 13),)),
        GateSpec("narrow_prz_q1", "PRZ width ratio is inside TRAIN Q1.", (c("prz_width_ratio", "le", width[0]),)),
        GateSpec("narrow_prz_q2", "PRZ width ratio is inside TRAIN median.", (c("prz_width_ratio", "le", width[1]),)),
        GateSpec("near_prz_q1", "Signal close is within TRAIN Q1 distance from PRZ.", (c("distance_to_prz_ratio", "le", distance[0]),)),
        GateSpec("near_prz_q2", "Signal close is within TRAIN median distance from PRZ.", (c("distance_to_prz_ratio", "le", distance[1]),)),
        GateSpec("fast_confirm_q1", "Pivot confirmation lag is inside TRAIN Q1.", (c("confirmation_lag_bars", "le", lag[0]),)),
        GateSpec("fast_confirm_q2", "Pivot confirmation lag is inside TRAIN median.", (c("confirmation_lag_bars", "le", lag[1]),)),
        GateSpec(
            "canonical_narrow_q2",
            "Canonical geometry plus PRZ width no wider than TRAIN median.",
            (c("source_tolerance_used", "eq", False), c("prz_width_ratio", "le", width[1])),
        ),
        GateSpec(
            "multiscale_narrow_q2",
            "Multi-scale support plus PRZ width no wider than TRAIN median.",
            (c("scale_support_count", "ge", 2), c("prz_width_ratio", "le", width[1])),
        ),
        GateSpec(
            "scale8_narrow_q2",
            "Scale >= 8 plus PRZ width no wider than TRAIN median.",
            (c("source_scale", "ge", 8), c("prz_width_ratio", "le", width[1])),
        ),
        GateSpec(
            "near_fast_q2",
            "Close near PRZ and confirmation lag no worse than TRAIN medians.",
            (c("distance_to_prz_ratio", "le", distance[1]), c("confirmation_lag_bars", "le", lag[1])),
        ),
        GateSpec(
            "canonical_near_q2",
            "Canonical geometry and close within TRAIN median PRZ distance.",
            (c("source_tolerance_used", "eq", False), c("distance_to_prz_ratio", "le", distance[1])),
        ),
    ]
    return tuple(specs)


def _within(value: Any, horizon: int) -> bool:
    if _missing(value):
        return False
    bars = int(float(value))
    return 0 <= bars <= horizon


def outcome_metrics(rows: Iterable[dict[str, Any]], *, horizon: int = 60) -> dict[str, float | int | None]:
    members = list(rows)
    n = len(members)
    touched = 0
    completed = 0
    retired = 0
    for row in members:
        is_touch = _as_bool(row.get("touch_before_retirement")) and _within(
            row.get("bars_to_first_future_prz_touch"), horizon
        )
        is_completion = _as_bool(row.get("completion_before_retirement")) and _within(
            row.get("bars_to_completion_confirmation"), horizon
        )
        is_retired = _within(row.get("bars_to_frontier_retirement"), horizon) and not is_touch
        touched += int(is_touch)
        completed += int(is_completion)
        retired += int(is_retired)
    return {
        "records": n,
        "touches": touched,
        "completions": completed,
        "retired_without_touch": retired,
        "touch_rate": None if n == 0 else touched / n,
        "completion_rate": None if n == 0 else completed / n,
        "retirement_rate": None if n == 0 else retired / n,
    }


def _delta(value: float | None, baseline: float | None) -> float | None:
    if value is None or baseline is None:
        return None
    return float(value) - float(baseline)


def evaluate_gate_library(
    train_rows: Iterable[dict[str, Any]],
    validation_rows: Iterable[dict[str, Any]],
    *,
    thresholds: dict[str, list[float] | tuple[float, ...]],
    horizon: int = 60,
    min_train_records: int = 25,
    min_validation_records: int = 10,
) -> dict[str, Any]:
    """Evaluate a frozen gate library on Train and Validation while leaving Holdout sealed."""
    train = list(train_rows)
    validation = list(validation_rows)
    train_base = outcome_metrics(train, horizon=horizon)
    val_base = outcome_metrics(validation, horizon=horizon)
    specs = build_gate_library(thresholds)
    diagnostics: list[dict[str, Any]] = []

    for spec in specs:
        train_members = [row for row in train if gate_matches(row, spec)]
        val_members = [row for row in validation if gate_matches(row, spec)]
        train_metrics = outcome_metrics(train_members, horizon=horizon)
        val_metrics = outcome_metrics(val_members, horizon=horizon)
        train_touch_delta = _delta(train_metrics["touch_rate"], train_base["touch_rate"])
        val_touch_delta = _delta(val_metrics["touch_rate"], val_base["touch_rate"])
        train_retire_delta = _delta(train_metrics["retirement_rate"], train_base["retirement_rate"])
        val_retire_delta = _delta(val_metrics["retirement_rate"], val_base["retirement_rate"])
        sample_ok = len(train_members) >= min_train_records and len(val_members) >= min_validation_records
        touch_consistent = bool(
            sample_ok
            and train_touch_delta is not None
            and val_touch_delta is not None
            and train_touch_delta > 0
            and val_touch_delta > 0
        )
        retirement_consistent = bool(
            sample_ok
            and train_retire_delta is not None
            and val_retire_delta is not None
            and train_retire_delta < 0
            and val_retire_delta < 0
        )
        strong_candidate = bool(
            sample_ok
            and touch_consistent
            and retirement_consistent
            and (
                (train_touch_delta is not None and train_touch_delta >= 0.03)
                or (train_retire_delta is not None and train_retire_delta <= -0.05)
            )
        )
        # Ranking is TRAIN-only by design. Validation confirms direction but never changes
        # the ranking objective or clause definitions.
        train_rank_score = None
        if train_touch_delta is not None and train_retire_delta is not None:
            train_rank_score = train_touch_delta - 0.5 * train_retire_delta
        diagnostics.append(
            {
                "name": spec.name,
                "description": spec.description,
                "clauses": [
                    {"feature": clause.feature, "op": clause.op, "value": clause.value}
                    for clause in spec.clauses
                ],
                "train": {
                    **train_metrics,
                    "coverage": None if not train else len(train_members) / len(train),
                    "touch_delta_vs_baseline": train_touch_delta,
                    "retirement_delta_vs_baseline": train_retire_delta,
                },
                "validation": {
                    **val_metrics,
                    "coverage": None if not validation else len(val_members) / len(validation),
                    "touch_delta_vs_baseline": val_touch_delta,
                    "retirement_delta_vs_baseline": val_retire_delta,
                },
                "sample_ok": sample_ok,
                "touch_direction_consistent": touch_consistent,
                "retirement_direction_consistent": retirement_consistent,
                "strong_candidate": strong_candidate,
                "train_rank_score": train_rank_score,
            }
        )

    diagnostics.sort(
        key=lambda row: (
            row["train_rank_score"] is None,
            -(row["train_rank_score"] or -999.0),
            row["name"],
        )
    )
    confirmed = [row for row in diagnostics if row["strong_candidate"]]
    return {
        "baseline": {"train": train_base, "validation": val_base},
        "gates": diagnostics,
        "strong_candidates": [row["name"] for row in confirmed],
        "policy_frozen": False,
        "holdout_opened": False,
        "methodology": {
            "gate_library": "Predeclared signal-time features only; no arbitrary cutoff search.",
            "thresholds": "Numeric cutoffs come from TRAIN quartiles only.",
            "validation": "Validation confirms direction; it does not redefine gates or ranking.",
            "completion": "Completion rate is reported but not optimized because completed events are sparse.",
            "holdout": "Holdout outcomes are not an input to this analysis.",
        },
    }
