from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

import numpy as np
import pandas as pd

from .completed_reaction_quality import _gate_library, _split_visible_rows


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(rows)
    t1 = sum(
        (row.get("outcome") or {}).get("outcome_class")
        in {"t1_only_within_horizon", "t2_within_horizon"}
        for row in rows
    )
    t2 = sum((row.get("outcome") or {}).get("outcome_class") == "t2_within_horizon" for row in rows)
    return {
        "records": count,
        "t1_rate": None if not count else t1 / count,
        "t2_rate": None if not count else t2 / count,
    }


def _delta(gated: dict[str, Any], baseline: dict[str, Any], key: str) -> float | None:
    left = gated.get(key)
    right = baseline.get(key)
    if left is None or right is None:
        return None
    return float(left) - float(right)


def _metrics(base_rows: list[dict[str, Any]], gated_rows: list[dict[str, Any]]) -> dict[str, Any]:
    baseline = _summary(base_rows)
    gated = _summary(gated_rows)
    return {
        "baseline": baseline,
        "gated": gated,
        "t1_lift": _delta(gated, baseline, "t1_rate"),
        "t2_lift": _delta(gated, baseline, "t2_rate"),
    }


def _top_share(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    if not rows:
        return {"top_value": None, "top_records": 0, "top_share": None, "distribution": {}}
    counts = Counter(str(row.get(key)) for row in rows)
    value, records = counts.most_common(1)[0]
    return {
        "top_value": value,
        "top_records": int(records),
        "top_share": records / len(rows),
        "distribution": dict(sorted(counts.items())),
    }


def _gate_rows(
    rows: list[dict[str, Any]],
    *,
    predicate: Any,
    thresholds: dict[str, float],
) -> list[dict[str, Any]]:
    return [row for row in rows if predicate(row, thresholds)]


def _concentration(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "records": len(rows),
        "by_symbol": _top_share(rows, "instrument_id"),
        "by_family": _top_share(rows, "pattern_family"),
        "by_scale": _top_share(rows, "source_scale"),
    }


def _leave_one_symbol_out(
    rows: list[dict[str, Any]],
    *,
    predicate: Any,
    thresholds: dict[str, float],
) -> dict[str, Any]:
    details: list[dict[str, Any]] = []
    for symbol in sorted({str(row["instrument_id"]) for row in rows}):
        subset = [row for row in rows if str(row["instrument_id"]) != symbol]
        gated = _gate_rows(subset, predicate=predicate, thresholds=thresholds)
        metrics = _metrics(subset, gated)
        direction_ok = bool(
            gated and metrics["t1_lift"] is not None and metrics["t1_lift"] > 0
        )
        details.append(
            {
                "removed_symbol": symbol,
                "direction_ok": direction_ok,
                **metrics,
            }
        )
    ok = sum(bool(row["direction_ok"]) for row in details)
    return {
        "removals": len(details),
        "direction_ok_removals": ok,
        "direction_ok_ratio": None if not details else ok / len(details),
        "all_direction_ok": bool(details and ok == len(details)),
        "details": details,
    }


def _family_stability(
    train: list[dict[str, Any]],
    validation: list[dict[str, Any]],
    *,
    predicate: Any,
    thresholds: dict[str, float],
    min_train_baseline: int = 8,
    min_train_gated: int = 3,
    min_validation_baseline: int = 4,
    min_validation_gated: int = 2,
) -> dict[str, Any]:
    families = sorted(
        {str(row["pattern_family"]) for row in train}
        | {str(row["pattern_family"]) for row in validation}
    )
    details: list[dict[str, Any]] = []
    jointly_eligible: list[dict[str, Any]] = []
    for family in families:
        train_base = [row for row in train if str(row["pattern_family"]) == family]
        validation_base = [row for row in validation if str(row["pattern_family"]) == family]
        train_gated = _gate_rows(train_base, predicate=predicate, thresholds=thresholds)
        validation_gated = _gate_rows(validation_base, predicate=predicate, thresholds=thresholds)
        train_metrics = _metrics(train_base, train_gated)
        validation_metrics = _metrics(validation_base, validation_gated)
        eligible = bool(
            len(train_base) >= min_train_baseline
            and len(train_gated) >= min_train_gated
            and len(validation_base) >= min_validation_baseline
            and len(validation_gated) >= min_validation_gated
        )
        direction_ok = bool(
            eligible
            and train_metrics["t1_lift"] is not None
            and validation_metrics["t1_lift"] is not None
            and train_metrics["t1_lift"] > 0
            and validation_metrics["t1_lift"] > 0
        )
        item = {
            "family": family,
            "eligible": eligible,
            "direction_ok": direction_ok,
            "train": train_metrics,
            "validation": validation_metrics,
        }
        details.append(item)
        if eligible:
            jointly_eligible.append(item)
    ok = sum(bool(row["direction_ok"]) for row in jointly_eligible)
    return {
        "jointly_eligible_families": len(jointly_eligible),
        "direction_ok_families": ok,
        "direction_ok_ratio": None if not jointly_eligible else ok / len(jointly_eligible),
        "generalizes_across_families": bool(
            len(jointly_eligible) >= 2 and ok == len(jointly_eligible)
        ),
        "details": details,
    }


def _time_segments(
    rows: list[dict[str, Any]],
    *,
    predicate: Any,
    thresholds: dict[str, float],
    segments: int,
    min_baseline: int,
    min_gated: int,
) -> dict[str, Any]:
    dates = sorted({pd.Timestamp(row["signal_trade_date"]).normalize() for row in rows})
    if not dates:
        return {
            "eligible_segments": 0,
            "direction_ok_segments": 0,
            "direction_ok_ratio": None,
            "details": [],
        }
    groups = np.array_split(np.array(dates, dtype=object), min(segments, len(dates)))
    details: list[dict[str, Any]] = []
    eligible: list[dict[str, Any]] = []
    for position, group in enumerate(groups, start=1):
        group_dates = list(group)
        date_set = set(group_dates)
        base_rows = [
            row
            for row in rows
            if pd.Timestamp(row["signal_trade_date"]).normalize() in date_set
        ]
        gated_rows = _gate_rows(base_rows, predicate=predicate, thresholds=thresholds)
        metrics = _metrics(base_rows, gated_rows)
        is_eligible = bool(
            len(base_rows) >= min_baseline and len(gated_rows) >= min_gated
        )
        direction_ok = bool(
            is_eligible and metrics["t1_lift"] is not None and metrics["t1_lift"] > 0
        )
        item = {
            "segment": position,
            "first_signal_date": min(group_dates).date().isoformat(),
            "last_signal_date": max(group_dates).date().isoformat(),
            "eligible": is_eligible,
            "direction_ok": direction_ok,
            **metrics,
        }
        details.append(item)
        if is_eligible:
            eligible.append(item)
    ok = sum(bool(row["direction_ok"]) for row in eligible)
    return {
        "eligible_segments": len(eligible),
        "direction_ok_segments": ok,
        "direction_ok_ratio": None if not eligible else ok / len(eligible),
        "details": details,
    }


def _lag_scale_alias(rows: list[dict[str, Any]]) -> dict[str, Any]:
    comparable = [
        row
        for row in rows
        if row.get("confirmation_lag_bars") is not None and row.get("source_scale") is not None
    ]
    exact = sum(
        int(row["confirmation_lag_bars"]) == int(row["source_scale"])
        for row in comparable
    )
    return {
        "records": len(comparable),
        "exact_matches": exact,
        "exact_match_rate": None if not comparable else exact / len(comparable),
    }


def _semantic_alias(
    name: str,
    layer: str,
    train: list[dict[str, Any]],
    validation: list[dict[str, Any]],
    *,
    predicate: Any,
    thresholds: dict[str, float],
) -> dict[str, Any]:
    train_lag = _lag_scale_alias(train)
    validation_lag = _lag_scale_alias(validation)
    is_latency_gate = layer == "observability_latency" or name.startswith("fast_confirmation_")
    limit = None
    if name == "fast_confirmation_q1":
        limit = thresholds.get("confirmation_lag_q25")
    elif name == "fast_confirmation_q2":
        limit = thresholds.get("confirmation_lag_q50")

    def _agreement(rows: list[dict[str, Any]]) -> float | None:
        if limit is None or not rows:
            return None
        same = sum(
            bool(predicate(row, thresholds)) == (int(row.get("source_scale", 0)) <= float(limit))
            for row in rows
        )
        return same / len(rows)

    train_agreement = _agreement(train)
    validation_agreement = _agreement(validation)
    alias = bool(
        is_latency_gate
        and train_lag["exact_match_rate"] == 1.0
        and validation_lag["exact_match_rate"] == 1.0
        and train_agreement == 1.0
        and validation_agreement == 1.0
    )
    return {
        "confirmation_lag_vs_source_scale": {
            "train": train_lag,
            "validation": validation_lag,
        },
        "candidate_mask_vs_scale_rule": {
            "scale_rule": None if limit is None else f"source_scale <= {float(limit):g}",
            "train_agreement": train_agreement,
            "validation_agreement": validation_agreement,
        },
        "is_scale_alias": alias,
        "independent_quality_signal": not alias,
    }


def _scale_diversity(train_rows: list[dict[str, Any]], validation_rows: list[dict[str, Any]]) -> dict[str, Any]:
    train = _top_share(train_rows, "source_scale")
    validation = _top_share(validation_rows, "source_scale")
    train_scales = len(train["distribution"])
    validation_scales = len(validation["distribution"])
    okay = bool(
        train_scales >= 2
        and validation_scales >= 2
        and (train["top_share"] or 1.0) <= 0.80
        and (validation["top_share"] or 1.0) <= 0.80
    )
    return {
        "train": train,
        "validation": validation,
        "train_scales": train_scales,
        "validation_scales": validation_scales,
        "diverse": okay,
    }


def build_completed_reaction_robustness_report(
    records: Iterable[dict[str, Any]],
    calibration: dict[str, Any],
    quality_report: dict[str, Any],
) -> dict[str, Any]:
    """Stress-test M2.15 candidates without reading sealed Holdout outcomes.

    This stage searches for no new gates. It reuses M2.15 Train-learned thresholds and only
    challenges already-declared candidates for concentration, symbol dependence, family/time
    stability, scale diversity and semantic aliasing. No result can freeze a production policy.
    """
    holdout_records = int((calibration.get("holdout") or {}).get("records", 0))
    base = {
        "holdout": {"sealed": True, "records": holdout_records, "outcomes_exposed": False},
        "policy_frozen": False,
        "holdout_opened": False,
        "methodology": {
            "new_gate_search": False,
            "candidate_source": "Only M2.15 consistent_t1_candidates are stress-tested.",
            "holdout": "Input outcomes at/after Holdout are sealed before this module is called.",
            "symbol_concentration": "No single symbol may exceed 25% of gated Train or Validation rows.",
            "leave_one_symbol_out": "Aggregate T1 lift must remain positive after removing every symbol in each visible split.",
            "family": "A general candidate needs at least two jointly eligible pattern families and positive within-family T1 lift in both Train and Validation.",
            "temporal": "Train uses thirds and Validation halves. Validation requires two eligible halves; positive T1 lift must hold in >=2/3 Train segments and all eligible Validation halves.",
            "scale": "A non-context candidate needs at least two source scales in Train and Validation and no single scale above 80% of gated rows.",
            "semantic_alias": "A latency gate that is exactly equivalent to source_scale is treated as scale context, not independent quality evidence.",
            "identity": "Robustness never changes Carney identity, Pivot selection, PRZ or reaction targets.",
        },
    }
    if quality_report.get("status") != "completed_reaction_quality_evidence_holdout_sealed":
        return {
            **base,
            "status": "completed_reaction_robustness_not_ready_holdout_sealed",
            "reason": "completed_reaction_quality_not_ready",
            "candidates_in": [],
            "robust_candidates": [],
            "gates": [],
        }

    train, validation = _split_visible_rows(list(records), calibration)
    thresholds = {str(k): float(v) for k, v in (quality_report.get("thresholds") or {}).items()}
    library = _gate_library()
    candidates = [
        str(name)
        for name in quality_report.get("consistent_t1_candidates", [])
        if str(name) in library
    ]

    gates: list[dict[str, Any]] = []
    robust: list[str] = []
    for name in candidates:
        layer, predicate = library[name]
        train_gated = _gate_rows(train, predicate=predicate, thresholds=thresholds)
        validation_gated = _gate_rows(validation, predicate=predicate, thresholds=thresholds)
        concentration_train = _concentration(train_gated)
        concentration_validation = _concentration(validation_gated)
        concentration_ok = bool(
            (concentration_train["by_symbol"]["top_share"] or 1.0) <= 0.25
            and (concentration_validation["by_symbol"]["top_share"] or 1.0) <= 0.25
        )
        loso_train = _leave_one_symbol_out(train, predicate=predicate, thresholds=thresholds)
        loso_validation = _leave_one_symbol_out(validation, predicate=predicate, thresholds=thresholds)
        loso_ok = bool(loso_train["all_direction_ok"] and loso_validation["all_direction_ok"])
        family = _family_stability(
            train,
            validation,
            predicate=predicate,
            thresholds=thresholds,
        )
        train_time = _time_segments(
            train,
            predicate=predicate,
            thresholds=thresholds,
            segments=3,
            min_baseline=10,
            min_gated=3,
        )
        validation_time = _time_segments(
            validation,
            predicate=predicate,
            thresholds=thresholds,
            segments=2,
            min_baseline=6,
            min_gated=2,
        )
        temporal_ok = bool(
            train_time["eligible_segments"] >= 3
            and (train_time["direction_ok_ratio"] or 0.0) >= (2 / 3)
            and validation_time["eligible_segments"] >= 2
            and validation_time["direction_ok_segments"] == validation_time["eligible_segments"]
        )
        scale = _scale_diversity(train_gated, validation_gated)
        alias = _semantic_alias(
            name,
            layer,
            train,
            validation,
            predicate=predicate,
            thresholds=thresholds,
        )
        semantic_independence_ok = bool(alias["independent_quality_signal"])
        scale_ok = bool(scale["diverse"] or layer == "context_scale")
        blockers: list[str] = []
        if not concentration_ok:
            blockers.append("symbol_concentration")
        if not loso_ok:
            blockers.append("leave_one_symbol_out")
        if not family["generalizes_across_families"]:
            blockers.append("family_generalization")
        if not temporal_ok:
            blockers.append("temporal_stability")
        if not scale_ok:
            blockers.append("scale_diversity")
        if not semantic_independence_ok:
            blockers.append("confirmation_lag_is_scale_alias")

        candidate_robust = not blockers
        if candidate_robust:
            robust.append(name)
        gates.append(
            {
                "name": name,
                "m2_15_layer": layer,
                "effective_layer": "context_scale_alias" if alias["is_scale_alias"] else layer,
                "train": _metrics(train, train_gated),
                "validation": _metrics(validation, validation_gated),
                "concentration": {
                    "ok": concentration_ok,
                    "train": concentration_train,
                    "validation": concentration_validation,
                },
                "leave_one_symbol_out": {
                    "ok": loso_ok,
                    "train": loso_train,
                    "validation": loso_validation,
                },
                "family_stability": family,
                "temporal_stability": {
                    "ok": temporal_ok,
                    "train": train_time,
                    "validation": validation_time,
                },
                "scale_diversity": scale,
                "semantic_alias": alias,
                "blockers": blockers,
                "robust_research_candidate": candidate_robust,
                "eligible_for_policy_freeze": False,
            }
        )

    return {
        **base,
        "status": "completed_reaction_robustness_holdout_sealed",
        "visible_records": {"train": len(train), "validation": len(validation)},
        "thresholds_reused": thresholds,
        "candidates_in": candidates,
        "robust_candidates": robust,
        "gates": gates,
    }
