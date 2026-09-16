from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict
from typing import Any, Iterable

import pandas as pd

from .quality_gate import GateSpec, build_gate_library, evaluate_gate_library, gate_matches, outcome_metrics
from .time_split import assign_purged_split, derive_boundaries, learn_numeric_thresholds, mature_forward_records


def _delta(gated: dict[str, Any], baseline: dict[str, Any], key: str) -> float | None:
    left = gated.get(key)
    right = baseline.get(key)
    if left is None or right is None:
        return None
    return float(left) - float(right)


def _metrics_with_delta(base_rows: list[dict[str, Any]], gate_rows: list[dict[str, Any]], horizon: int) -> dict[str, Any]:
    baseline = outcome_metrics(base_rows, horizon=horizon)
    gated = outcome_metrics(gate_rows, horizon=horizon)
    return {
        "baseline": baseline,
        "gated": gated,
        "touch_delta": _delta(gated, baseline, "touch_rate"),
        "retirement_delta": _delta(gated, baseline, "retirement_rate"),
        "completion_delta": _delta(gated, baseline, "completion_rate"),
    }


def _direction_ok(row: dict[str, Any]) -> bool:
    touch = row.get("touch_delta")
    retire = row.get("retirement_delta")
    return bool(touch is not None and retire is not None and touch > 0 and retire < 0)


def _top_share(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    if not rows:
        return {"top_value": None, "top_records": 0, "top_share": None, "distribution": {}}
    counts = Counter(str(row.get(key)) for row in rows)
    top_value, top_records = counts.most_common(1)[0]
    return {
        "top_value": top_value,
        "top_records": int(top_records),
        "top_share": float(top_records / len(rows)),
        "distribution": dict(sorted(counts.items())),
    }


def _symbol_diagnostics(
    rows: list[dict[str, Any]],
    spec: GateSpec,
    *,
    horizon: int,
    min_baseline: int = 20,
    min_gated: int = 5,
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["instrument_id"])].append(row)
    details: list[dict[str, Any]] = []
    eligible: list[dict[str, Any]] = []
    for symbol, members in sorted(grouped.items()):
        gated = [row for row in members if gate_matches(row, spec)]
        metrics = _metrics_with_delta(members, gated, horizon)
        item = {
            "instrument_id": symbol,
            "baseline_records": len(members),
            "gated_records": len(gated),
            **metrics,
        }
        item["eligible"] = len(members) >= min_baseline and len(gated) >= min_gated
        item["direction_ok"] = bool(item["eligible"] and _direction_ok(item))
        details.append(item)
        if item["eligible"]:
            eligible.append(item)
    joint = sum(bool(item["direction_ok"]) for item in eligible)
    return {
        "eligible_symbols": len(eligible),
        "direction_ok_symbols": joint,
        "direction_ok_ratio": None if not eligible else joint / len(eligible),
        "details": details,
    }


def _leave_one_symbol_out(rows: list[dict[str, Any]], spec: GateSpec, *, horizon: int) -> dict[str, Any]:
    symbols = sorted({str(row["instrument_id"]) for row in rows})
    details: list[dict[str, Any]] = []
    for symbol in symbols:
        subset = [row for row in rows if str(row["instrument_id"]) != symbol]
        gated = [row for row in subset if gate_matches(row, spec)]
        metrics = _metrics_with_delta(subset, gated, horizon)
        details.append({"removed_symbol": symbol, **metrics, "direction_ok": _direction_ok(metrics)})
    ok = sum(bool(item["direction_ok"]) for item in details)
    return {
        "removals": len(details),
        "direction_ok_removals": ok,
        "all_direction_ok": bool(details and ok == len(details)),
        "direction_ok_ratio": None if not details else ok / len(details),
        "details": details,
    }


def _time_segments(
    rows: list[dict[str, Any]],
    spec: GateSpec,
    *,
    horizon: int,
    segments: int,
    min_baseline: int = 30,
    min_gated: int = 10,
) -> dict[str, Any]:
    if not rows or segments < 1:
        return {"segments": [], "eligible_segments": 0, "direction_ok_segments": 0, "direction_ok_ratio": None}
    ordered_dates = sorted({pd.Timestamp(row["signal_trade_date"]).normalize() for row in rows})
    date_groups = [group.tolist() for group in __import__("numpy").array_split(ordered_dates, min(segments, len(ordered_dates)))]
    details: list[dict[str, Any]] = []
    eligible: list[dict[str, Any]] = []
    for position, dates in enumerate(date_groups, start=1):
        date_set = set(dates)
        members = [row for row in rows if pd.Timestamp(row["signal_trade_date"]).normalize() in date_set]
        gated = [row for row in members if gate_matches(row, spec)]
        metrics = _metrics_with_delta(members, gated, horizon)
        item = {
            "segment": position,
            "first_signal_date": None if not dates else min(dates).date().isoformat(),
            "last_signal_date": None if not dates else max(dates).date().isoformat(),
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
        "eligible_segments": len(eligible),
        "direction_ok_segments": ok,
        "direction_ok_ratio": None if not eligible else ok / len(eligible),
        "details": details,
    }


def _gate_concentration(rows: list[dict[str, Any]], spec: GateSpec) -> dict[str, Any]:
    gated = [row for row in rows if gate_matches(row, spec)]
    return {
        "records": len(gated),
        "by_symbol": _top_share(gated, "instrument_id"),
        "by_pattern": _top_share(gated, "pattern_id"),
        "by_scale": _top_share(gated, "source_scale"),
    }


def build_quality_robustness_report(
    records: Iterable[dict[str, Any]],
    *,
    horizon: int = 60,
    min_mature_records: int = 100,
) -> dict[str, Any]:
    """Stress-test predeclared quality gates without ever opening Holdout outcomes.

    This layer does not search for new gates. It reuses the frozen Train-only threshold gate
    library and asks whether each already-strong gate survives symbol concentration, leave-one-
    symbol-out, cross-sectional direction and coarse chronological segmentation.
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
    train = splits["train"]
    validation = splits["validation"]
    if not train or not validation or not splits["holdout"]:
        return {
            "status": "insufficient_split_coverage",
            "mature_records": len(mature),
            "policy_frozen": False,
            "holdout_opened": False,
        }

    thresholds = learn_numeric_thresholds(train)
    threshold_payload = {
        "prz_width_ratio": list(thresholds.prz_width_ratio),
        "distance_to_prz_ratio": list(thresholds.distance_to_prz_ratio),
        "confirmation_lag_bars": list(thresholds.confirmation_lag_bars),
    }
    # evaluate_gate_library expects the flattened signal-time quality fields used by M2.8.
    from .autonomous_calibration import gate_rows

    flat_train = gate_rows(train)
    flat_validation = gate_rows(validation)
    evidence = evaluate_gate_library(
        flat_train,
        flat_validation,
        thresholds=threshold_payload,
        horizon=horizon,
    )
    strong_names = set(evidence["strong_candidates"])
    spec_by_name = {spec.name: spec for spec in build_gate_library(threshold_payload)}

    gates: list[dict[str, Any]] = []
    robust_names: list[str] = []
    for name in sorted(strong_names):
        spec = spec_by_name[name]
        tr_conc = _gate_concentration(flat_train, spec)
        va_conc = _gate_concentration(flat_validation, spec)
        tr_symbols = _symbol_diagnostics(flat_train, spec, horizon=horizon)
        va_symbols = _symbol_diagnostics(flat_validation, spec, horizon=horizon)
        tr_loso = _leave_one_symbol_out(flat_train, spec, horizon=horizon)
        va_loso = _leave_one_symbol_out(flat_validation, spec, horizon=horizon)
        tr_time = _time_segments(flat_train, spec, horizon=horizon, segments=3)
        va_time = _time_segments(flat_validation, spec, horizon=horizon, segments=2)

        symbol_concentration_ok = bool(
            (tr_conc["by_symbol"]["top_share"] or 1.0) <= 0.30
            and (va_conc["by_symbol"]["top_share"] or 1.0) <= 0.30
        )
        cross_section_ok = bool(
            tr_symbols["eligible_symbols"] >= 5
            and va_symbols["eligible_symbols"] >= 5
            and (tr_symbols["direction_ok_ratio"] or 0.0) >= 0.60
            and (va_symbols["direction_ok_ratio"] or 0.0) >= 0.50
        )
        loso_ok = bool(tr_loso["all_direction_ok"] and va_loso["all_direction_ok"])
        temporal_ok = bool(
            tr_time["eligible_segments"] >= 3
            and va_time["eligible_segments"] >= 2
            and (tr_time["direction_ok_ratio"] or 0.0) >= (2 / 3)
            and (va_time["direction_ok_ratio"] or 0.0) >= 0.50
        )
        robust = bool(symbol_concentration_ok and cross_section_ok and loso_ok and temporal_ok)
        if robust:
            robust_names.append(name)
        gates.append(
            {
                "name": name,
                "description": spec.description,
                "clauses": [asdict(clause) for clause in spec.clauses],
                "symbol_concentration_ok": symbol_concentration_ok,
                "cross_section_ok": cross_section_ok,
                "leave_one_symbol_out_ok": loso_ok,
                "temporal_stability_ok": temporal_ok,
                "robust_research_candidate": robust,
                "train": {
                    "concentration": tr_conc,
                    "symbol_diagnostics": tr_symbols,
                    "leave_one_symbol_out": tr_loso,
                    "time_segments": tr_time,
                },
                "validation": {
                    "concentration": va_conc,
                    "symbol_diagnostics": va_symbols,
                    "leave_one_symbol_out": va_loso,
                    "time_segments": va_time,
                },
            }
        )

    return {
        "status": "research_robustness_holdout_sealed",
        "mature_records": len(mature),
        "purged_boundary_records": len(purged),
        "train_records": len(train),
        "validation_records": len(validation),
        "holdout_records_sealed": len(splits["holdout"]),
        "train_learned_thresholds": threshold_payload,
        "strong_candidates_in": sorted(strong_names),
        "robust_research_candidates": robust_names,
        "gates": gates,
        "policy_frozen": False,
        "holdout_opened": False,
        "methodology": {
            "new_gate_search": False,
            "symbol_concentration": "No single symbol may exceed 30% of gated records in Train or Validation.",
            "cross_section": "Requires >=5 eligible symbols in each split and joint touch-up/retirement-down direction in >=60% Train and >=50% Validation symbols.",
            "leave_one_symbol_out": "Aggregate direction must remain favorable after removing every individual symbol in Train and Validation.",
            "temporal": "Frozen gate must remain directionally favorable in >=2/3 Train thirds and >=1/2 Validation halves.",
            "holdout": "Holdout outcomes are not read by this module.",
        },
    }
