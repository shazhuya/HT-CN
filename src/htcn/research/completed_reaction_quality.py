from __future__ import annotations

from collections import Counter
from math import ceil
from typing import Any, Callable, Iterable

import pandas as pd

from .completed_reaction_calibration import ACTIONABLE_COMPLETED_OUTCOMES


GatePredicate = Callable[[dict[str, Any], dict[str, float]], bool]


def _metric_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        outcome = row.get("outcome") or {}
        if outcome.get("sealed"):
            continue
        if outcome.get("outcome_class") not in ACTIONABLE_COMPLETED_OUTCOMES:
            continue
        out.append(row)
    return out


def _split_visible_rows(
    rows: Iterable[dict[str, Any]], calibration: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    boundaries = calibration.get("boundaries") or {}
    if not boundaries:
        return [], []

    train_end = pd.Timestamp(boundaries["train_end"]).normalize()
    validation_start = pd.Timestamp(boundaries["validation_start"]).normalize()
    validation_end = pd.Timestamp(boundaries["validation_end"]).normalize()
    holdout_start = pd.Timestamp(boundaries["holdout_start"]).normalize()

    train: list[dict[str, Any]] = []
    validation: list[dict[str, Any]] = []
    for row in _metric_rows(rows):
        signal = pd.Timestamp(row["signal_trade_date"]).normalize()
        observation_end = pd.Timestamp(row["observation_end_trade_date"]).normalize()
        if signal <= train_end:
            if observation_end < validation_start:
                train.append(row)
        elif validation_start <= signal <= validation_end:
            if observation_end < holdout_start:
                validation.append(row)
    return train, validation


def _quality_value(row: dict[str, Any], key: str) -> float | None:
    if key == "geometry_score":
        value = row.get("geometry_score")
    elif key == "confirmation_lag_bars":
        value = row.get("confirmation_lag_bars")
    else:
        value = (row.get("quality_at_signal") or {}).get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _value_or(row: dict[str, Any], key: str, fallback: float) -> float:
    value = _quality_value(row, key)
    return fallback if value is None else value


def _quantiles(rows: list[dict[str, Any]], key: str) -> tuple[float, float, float] | None:
    values = [_quality_value(row, key) for row in rows]
    numeric = [value for value in values if value is not None]
    if len(numeric) < 4:
        return None
    series = pd.Series(numeric, dtype="float64")
    return (
        float(series.quantile(0.25)),
        float(series.quantile(0.50)),
        float(series.quantile(0.75)),
    )


def learn_completed_reaction_thresholds(train: Iterable[dict[str, Any]]) -> dict[str, float]:
    """Learn numeric gate cutoffs from Train only.

    These thresholds are research metadata. They never alter harmonic identity, PRZ geometry,
    target definitions or the sealed Holdout.
    """
    rows = list(train)
    geometry = _quantiles(rows, "geometry_score")
    width = _quantiles(rows, "prz_width_ratio")
    lag = _quantiles(rows, "confirmation_lag_bars")
    if geometry is None or width is None or lag is None:
        return {}
    return {
        "geometry_q50": geometry[1],
        "geometry_q75": geometry[2],
        "prz_width_q25": width[0],
        "prz_width_q50": width[1],
        "confirmation_lag_q25": lag[0],
        "confirmation_lag_q50": lag[1],
    }


def _gate_library() -> dict[str, tuple[str, GatePredicate]]:
    return {
        "geometry_top_half": (
            "geometry_quality",
            lambda row, t: _value_or(row, "geometry_score", float("-inf"))
            >= t["geometry_q50"],
        ),
        "geometry_top_quartile": (
            "geometry_quality",
            lambda row, t: _value_or(row, "geometry_score", float("-inf"))
            >= t["geometry_q75"],
        ),
        "narrow_prz_q1": (
            "geometry_quality",
            lambda row, t: _value_or(row, "prz_width_ratio", float("inf"))
            <= t["prz_width_q25"],
        ),
        "narrow_prz_q2": (
            "geometry_quality",
            lambda row, t: _value_or(row, "prz_width_ratio", float("inf"))
            <= t["prz_width_q50"],
        ),
        "fast_confirmation_q1": (
            "observability_latency",
            lambda row, t: _value_or(row, "confirmation_lag_bars", float("inf"))
            <= t["confirmation_lag_q25"],
        ),
        "fast_confirmation_q2": (
            "observability_latency",
            lambda row, t: _value_or(row, "confirmation_lag_bars", float("inf"))
            <= t["confirmation_lag_q50"],
        ),
        "no_source_tolerance_required": (
            "source_conformity",
            lambda row, t: row.get("source_tolerance_used") is not True,
        ),
        "scale_5_plus": (
            "context_scale",
            lambda row, t: int(row.get("source_scale", 0)) >= 5,
        ),
        "scale_8_plus": (
            "context_scale",
            lambda row, t: int(row.get("source_scale", 0)) >= 8,
        ),
    }


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(rows)
    outcomes = Counter(str(row["outcome"]["outcome_class"]) for row in rows)
    t1 = int(outcomes.get("t1_only_within_horizon", 0) + outcomes.get("t2_within_horizon", 0))
    t2 = int(outcomes.get("t2_within_horizon", 0))
    return {
        "records": count,
        "t1_rate": None if not count else t1 / count,
        "t2_rate": None if not count else t2 / count,
        "symbols": len({str(row["instrument_id"]) for row in rows}),
        "families": len({str(row["pattern_family"]) for row in rows}),
        "by_family": dict(sorted(Counter(str(row["pattern_family"]) for row in rows).items())),
    }


def _lift(value: float | None, baseline: float | None) -> float | None:
    if value is None or baseline is None:
        return None
    return float(value - baseline)


def _evaluate_gate(
    *,
    name: str,
    layer: str,
    predicate: GatePredicate,
    thresholds: dict[str, float],
    train: list[dict[str, Any]],
    validation: list[dict[str, Any]],
    train_baseline: dict[str, Any],
    validation_baseline: dict[str, Any],
    minimum_train_gate: int,
    minimum_validation_gate: int,
) -> dict[str, Any]:
    train_rows = [row for row in train if predicate(row, thresholds)]
    validation_rows = [row for row in validation if predicate(row, thresholds)]
    train_summary = _summary(train_rows)
    validation_summary = _summary(validation_rows)

    train_t1_lift = _lift(train_summary["t1_rate"], train_baseline["t1_rate"])
    validation_t1_lift = _lift(validation_summary["t1_rate"], validation_baseline["t1_rate"])
    train_t2_lift = _lift(train_summary["t2_rate"], train_baseline["t2_rate"])
    validation_t2_lift = _lift(validation_summary["t2_rate"], validation_baseline["t2_rate"])

    enough = (
        train_summary["records"] >= minimum_train_gate
        and validation_summary["records"] >= minimum_validation_gate
    )
    consistent_t1 = bool(
        enough
        and train_t1_lift is not None
        and validation_t1_lift is not None
        and train_t1_lift > 0
        and validation_t1_lift > 0
    )
    t2_corroborates = bool(
        consistent_t1
        and train_t2_lift is not None
        and validation_t2_lift is not None
        and train_t2_lift >= 0
        and validation_t2_lift >= 0
    )

    return {
        "name": name,
        "layer": layer,
        "train": train_summary,
        "validation": validation_summary,
        "train_t1_lift": train_t1_lift,
        "validation_t1_lift": validation_t1_lift,
        "train_t2_lift": train_t2_lift,
        "validation_t2_lift": validation_t2_lift,
        "sample_floor_met": enough,
        "consistent_t1_evidence": consistent_t1,
        "t2_corroborates": t2_corroborates,
        "eligible_for_policy_freeze": False,
    }


def build_completed_reaction_quality_report(
    records: Iterable[dict[str, Any]],
    calibration: dict[str, Any],
    *,
    minimum_train_gate: int | None = None,
    minimum_validation_gate: int | None = None,
) -> dict[str, Any]:
    """Explore signal-time completed-pattern quality without exposing Holdout outcomes.

    Input is expected to be the already-redacted completed-reaction artifact. The function
    intentionally ignores sealed rows and evaluates a fixed gate library on Train/Validation
    only. A research candidate is not a production rule and never modifies Carney identity.
    """
    holdout = calibration.get("holdout") or {"sealed": True, "records": 0}
    base = {
        "holdout": {
            "sealed": True,
            "records": int(holdout.get("records", 0)),
            "outcomes_exposed": False,
        },
        "methodology": {
            "input_boundary": "Consumes the redacted completed-reaction artifact; sealed Holdout outcomes are unavailable by construction.",
            "threshold_learning": "Numeric thresholds are learned from Train only and reused unchanged on Validation.",
            "target": "T1/T2 are post-confirmation reaction targets, not forming-PRZ touch labels.",
            "identity": "Quality evidence cannot change harmonic identity, Pivot choice, PRZ or target prices.",
            "selection": "Candidate flags are exploratory Train/Validation evidence only; eligible_for_policy_freeze remains false.",
        },
    }

    if calibration.get("status") != "completed_reaction_calibration_holdout_sealed":
        return {
            **base,
            "status": "completed_reaction_quality_sample_insufficient_holdout_sealed",
            "reason": calibration.get("reason") or "completed_reaction_calibration_not_ready",
            "thresholds": {},
            "baseline": {"train": _summary([]), "validation": _summary([])},
            "gates": [],
            "consistent_t1_candidates": [],
            "t2_corroborated_candidates": [],
        }

    train, validation = _split_visible_rows(records, calibration)
    thresholds = learn_completed_reaction_thresholds(train)
    if not thresholds:
        return {
            **base,
            "status": "completed_reaction_quality_sample_insufficient_holdout_sealed",
            "reason": "insufficient_train_feature_coverage",
            "thresholds": {},
            "baseline": {"train": _summary(train), "validation": _summary(validation)},
            "gates": [],
            "consistent_t1_candidates": [],
            "t2_corroborated_candidates": [],
        }

    train_baseline = _summary(train)
    validation_baseline = _summary(validation)
    min_train = (
        max(8, ceil(train_baseline["records"] * 0.20))
        if minimum_train_gate is None
        else int(minimum_train_gate)
    )
    min_validation = (
        max(3, ceil(validation_baseline["records"] * 0.20))
        if minimum_validation_gate is None
        else int(minimum_validation_gate)
    )

    gates = [
        _evaluate_gate(
            name=name,
            layer=layer,
            predicate=predicate,
            thresholds=thresholds,
            train=train,
            validation=validation,
            train_baseline=train_baseline,
            validation_baseline=validation_baseline,
            minimum_train_gate=min_train,
            minimum_validation_gate=min_validation,
        )
        for name, (layer, predicate) in _gate_library().items()
    ]
    consistent = [row["name"] for row in gates if row["consistent_t1_evidence"]]
    corroborated = [row["name"] for row in gates if row["t2_corroborates"]]

    return {
        **base,
        "status": "completed_reaction_quality_evidence_holdout_sealed",
        "thresholds": thresholds,
        "sample_floor": {"train_gate": min_train, "validation_gate": min_validation},
        "baseline": {"train": train_baseline, "validation": validation_baseline},
        "gates": gates,
        "consistent_t1_candidates": consistent,
        "t2_corroborated_candidates": corroborated,
    }
