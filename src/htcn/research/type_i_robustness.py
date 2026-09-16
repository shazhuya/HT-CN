from __future__ import annotations

from collections import Counter
from typing import Any, Callable, Iterable

import numpy as np
import pandas as pd

from .time_split import assign_purged_split
from .type_i_confirmation import (
    DEFAULT_TYPE_I_LANDMARK_BAR,
    _bar_value,
    _boundaries,
    _cohort_library,
    _terminal_events,
)


DEFAULT_MIN_TRAIN_PENDING = 60
DEFAULT_MIN_VALIDATION_PENDING = 20
DEFAULT_MAX_SYMBOL_SHARE = 0.25


Predicate = Callable[[dict[str, Any]], bool]


def _is_t2_pending(row: dict[str, Any], *, landmark_bar: int) -> bool:
    t2 = _bar_value(row["terminal_bar_audit"], "bars_from_terminal_to_t2")
    return t2 is None or t2 > landmark_bar


def _later_t2_hit(
    row: dict[str, Any],
    *,
    landmark_bar: int,
    reaction_horizon: int,
) -> bool:
    t2 = _bar_value(row["terminal_bar_audit"], "bars_from_terminal_to_t2")
    return bool(t2 is not None and landmark_bar < t2 <= reaction_horizon)


def _pending_rows(rows: Iterable[dict[str, Any]], *, landmark_bar: int) -> list[dict[str, Any]]:
    return [row for row in rows if _is_t2_pending(row, landmark_bar=landmark_bar)]


def _progression_summary(
    rows: Iterable[dict[str, Any]],
    *,
    landmark_bar: int,
    reaction_horizon: int,
) -> dict[str, Any]:
    pending = _pending_rows(rows, landmark_bar=landmark_bar)
    hits = sum(
        _later_t2_hit(
            row,
            landmark_bar=landmark_bar,
            reaction_horizon=reaction_horizon,
        )
        for row in pending
    )
    return {
        "pending_records": len(pending),
        "later_t2_hits": int(hits),
        "later_t2_rate": None if not pending else hits / len(pending),
    }


def _metrics(
    base_rows: list[dict[str, Any]],
    gated_rows: list[dict[str, Any]],
    *,
    landmark_bar: int,
    reaction_horizon: int,
) -> dict[str, Any]:
    baseline = _progression_summary(
        base_rows,
        landmark_bar=landmark_bar,
        reaction_horizon=reaction_horizon,
    )
    gated = _progression_summary(
        gated_rows,
        landmark_bar=landmark_bar,
        reaction_horizon=reaction_horizon,
    )
    left = gated["later_t2_rate"]
    right = baseline["later_t2_rate"]
    lift = None if left is None or right is None else float(left) - float(right)
    return {
        "baseline": baseline,
        "gated": gated,
        "later_t2_lift": lift,
    }


def _gate_rows(rows: list[dict[str, Any]], predicate: Predicate) -> list[dict[str, Any]]:
    return [row for row in rows if predicate(row)]


def _top_share(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    if not rows:
        return {"top_value": None, "top_records": 0, "top_share": None, "distribution": {}}
    counts = Counter(str(row.get(key)) for row in rows)
    value, count = counts.most_common(1)[0]
    return {
        "top_value": value,
        "top_records": int(count),
        "top_share": count / len(rows),
        "distribution": dict(sorted(counts.items())),
    }


def _concentration(
    rows: list[dict[str, Any]],
    *,
    landmark_bar: int,
) -> dict[str, Any]:
    pending = _pending_rows(rows, landmark_bar=landmark_bar)
    return {
        "pending_records": len(pending),
        "by_symbol": _top_share(pending, "instrument_id"),
        "by_pattern": _top_share(pending, "pattern_id"),
        "by_family": _top_share(pending, "pattern_family"),
        "by_scale": _top_share(pending, "source_scale"),
        "by_direction": _top_share(pending, "direction"),
    }


def _positive_lift(metrics: dict[str, Any]) -> bool:
    lift = metrics.get("later_t2_lift")
    return bool(lift is not None and float(lift) > 0)


def _leave_one_symbol_out(
    rows: list[dict[str, Any]],
    *,
    predicate: Predicate,
    landmark_bar: int,
    reaction_horizon: int,
) -> dict[str, Any]:
    details: list[dict[str, Any]] = []
    for symbol in sorted({str(row.get("instrument_id")) for row in rows}):
        subset = [row for row in rows if str(row.get("instrument_id")) != symbol]
        gated = _gate_rows(subset, predicate)
        metrics = _metrics(
            subset,
            gated,
            landmark_bar=landmark_bar,
            reaction_horizon=reaction_horizon,
        )
        details.append(
            {
                "removed_symbol": symbol,
                "direction_ok": _positive_lift(metrics),
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


def _group_stability(
    train: list[dict[str, Any]],
    validation: list[dict[str, Any]],
    *,
    dimension: str,
    predicate: Predicate,
    landmark_bar: int,
    reaction_horizon: int,
    min_train_baseline_pending: int,
    min_train_gated_pending: int,
    min_validation_baseline_pending: int,
    min_validation_gated_pending: int,
    required_groups: int,
) -> dict[str, Any]:
    groups = sorted(
        {str(row.get(dimension)) for row in train}
        | {str(row.get(dimension)) for row in validation}
    )
    details: list[dict[str, Any]] = []
    eligible: list[dict[str, Any]] = []
    for value in groups:
        train_base = [row for row in train if str(row.get(dimension)) == value]
        validation_base = [row for row in validation if str(row.get(dimension)) == value]
        train_gated = _gate_rows(train_base, predicate)
        validation_gated = _gate_rows(validation_base, predicate)
        train_metrics = _metrics(
            train_base,
            train_gated,
            landmark_bar=landmark_bar,
            reaction_horizon=reaction_horizon,
        )
        validation_metrics = _metrics(
            validation_base,
            validation_gated,
            landmark_bar=landmark_bar,
            reaction_horizon=reaction_horizon,
        )
        is_eligible = bool(
            train_metrics["baseline"]["pending_records"] >= min_train_baseline_pending
            and train_metrics["gated"]["pending_records"] >= min_train_gated_pending
            and validation_metrics["baseline"]["pending_records"] >= min_validation_baseline_pending
            and validation_metrics["gated"]["pending_records"] >= min_validation_gated_pending
        )
        direction_ok = bool(
            is_eligible
            and _positive_lift(train_metrics)
            and _positive_lift(validation_metrics)
        )
        item = {
            "value": value,
            "eligible": is_eligible,
            "direction_ok": direction_ok,
            "train": train_metrics,
            "validation": validation_metrics,
        }
        details.append(item)
        if is_eligible:
            eligible.append(item)
    ok = sum(bool(row["direction_ok"]) for row in eligible)
    return {
        "dimension": dimension,
        "eligible_groups": len(eligible),
        "required_groups": required_groups,
        "direction_ok_groups": ok,
        "direction_ok_ratio": None if not eligible else ok / len(eligible),
        "generalizes": bool(len(eligible) >= required_groups and ok == len(eligible)),
        "details": details,
    }


def _time_segments(
    rows: list[dict[str, Any]],
    *,
    predicate: Predicate,
    landmark_bar: int,
    reaction_horizon: int,
    segments: int,
    min_baseline_pending: int,
    min_gated_pending: int,
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
        base = [
            row
            for row in rows
            if pd.Timestamp(row["signal_trade_date"]).normalize() in date_set
        ]
        gated = _gate_rows(base, predicate)
        metrics = _metrics(
            base,
            gated,
            landmark_bar=landmark_bar,
            reaction_horizon=reaction_horizon,
        )
        is_eligible = bool(
            metrics["baseline"]["pending_records"] >= min_baseline_pending
            and metrics["gated"]["pending_records"] >= min_gated_pending
        )
        direction_ok = bool(is_eligible and _positive_lift(metrics))
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


def _scale_diversity(
    train_rows: list[dict[str, Any]],
    validation_rows: list[dict[str, Any]],
    *,
    landmark_bar: int,
) -> dict[str, Any]:
    train = _top_share(_pending_rows(train_rows, landmark_bar=landmark_bar), "source_scale")
    validation = _top_share(
        _pending_rows(validation_rows, landmark_bar=landmark_bar), "source_scale"
    )
    train_scales = len(train["distribution"])
    validation_scales = len(validation["distribution"])
    diverse = bool(
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
        "diverse": diverse,
    }


def build_type_i_early_path_robustness_report(
    records: Iterable[dict[str, Any]],
    terminal_bar_calibration: dict[str, Any],
    early_path_report: dict[str, Any],
    *,
    reaction_horizon: int = 20,
    landmark_bar: int = DEFAULT_TYPE_I_LANDMARK_BAR,
    minimum_train_candidate_pending: int = DEFAULT_MIN_TRAIN_PENDING,
    minimum_validation_candidate_pending: int = DEFAULT_MIN_VALIDATION_PENDING,
    max_symbol_share: float = DEFAULT_MAX_SYMBOL_SHARE,
) -> dict[str, Any]:
    """Stress-test every M2.18 early-path cohort without opening Holdout outcomes.

    The target is deliberately narrow: among structures whose T2 was still pending at T+5,
    did T2 first occur from T+6 through the frozen reaction horizon? Cohort membership uses only
    T+1..T+5 path information. This module searches no new thresholds and cannot freeze policy.
    """
    holdout_records = int((early_path_report.get("holdout") or {}).get("records", 0))
    base = {
        "holdout": {"sealed": True, "records": holdout_records, "outcomes_exposed": False},
        "policy_frozen": False,
        "eligible_for_policy_freeze": False,
        "methodology": {
            "candidate_source": "All six M2.18 predeclared cohorts are stress-tested; none is selected from Validation performance.",
            "target": "Among cases with T2 still pending at T+5, first T2 hit from T+6 through the frozen reaction horizon.",
            "sample_floor": f"Candidate pending rows require at least {minimum_train_candidate_pending} Train and {minimum_validation_candidate_pending} Validation observations.",
            "symbol_concentration": f"No single symbol may exceed {max_symbol_share:.0%} of gated pending Train or Validation rows.",
            "leave_one_symbol_out": "Visible-split later-T2 lift must remain positive after removing every symbol.",
            "family": "A general candidate requires at least two jointly eligible pattern families with positive lift in both Train and Validation.",
            "direction": "Bullish and bearish groups must both be jointly eligible and retain positive lift in Train and Validation.",
            "temporal": "Train is split into thirds and Validation into halves; at least 2/3 eligible Train segments and all eligible Validation halves must retain positive lift.",
            "scale": "Gated pending rows require at least two source scales in each visible split and no scale above 80% share.",
            "holdout": "M2.17/M2.18 Holdout outcomes are never summarized or used to choose candidates.",
            "identity": "Robustness never changes Carney identity, Pivot selection, PRZ, Terminal Price Bar or reaction targets.",
        },
        "anti_leakage": {
            "new_gate_search": False,
            "cohort_thresholds_fitted_to_outcomes": False,
            "early_features_stop_at_t_plus_5": True,
            "later_progression_starts_at_t_plus_6": True,
            "m2_17_boundaries_reused": True,
            "holdout_outcomes_opened": False,
        },
    }

    boundary = _boundaries(terminal_bar_calibration)
    if (
        early_path_report.get("status") != "type_i_early_path_evidence_holdout_sealed"
        or terminal_bar_calibration.get("status") != "terminal_bar_calibration_holdout_sealed"
        or boundary is None
    ):
        return {
            **base,
            "status": "type_i_early_path_robustness_not_ready_holdout_sealed",
            "reason": "m2_17_or_m2_18_not_ready",
            "candidates_in": [],
            "robust_candidates": [],
            "cohorts": [],
        }

    events = _terminal_events(records, reaction_horizon=reaction_horizon)
    splits, purged = assign_purged_split(events, boundary)
    train = splits["train"]
    validation = splits["validation"]
    library = _cohort_library()
    m2_18_names = {str(row.get("name")) for row in early_path_report.get("cohorts") or []}
    candidates = [name for name in library if name in m2_18_names]

    cohort_reports: list[dict[str, Any]] = []
    robust: list[str] = []
    for name in candidates:
        description, predicate = library[name]
        train_gated = _gate_rows(train, predicate)
        validation_gated = _gate_rows(validation, predicate)
        train_metrics = _metrics(
            train,
            train_gated,
            landmark_bar=landmark_bar,
            reaction_horizon=reaction_horizon,
        )
        validation_metrics = _metrics(
            validation,
            validation_gated,
            landmark_bar=landmark_bar,
            reaction_horizon=reaction_horizon,
        )
        visible_direction_ok = bool(
            _positive_lift(train_metrics) and _positive_lift(validation_metrics)
        )
        sample_floor_ok = bool(
            train_metrics["gated"]["pending_records"] >= minimum_train_candidate_pending
            and validation_metrics["gated"]["pending_records"]
            >= minimum_validation_candidate_pending
        )

        concentration_train = _concentration(train_gated, landmark_bar=landmark_bar)
        concentration_validation = _concentration(
            validation_gated, landmark_bar=landmark_bar
        )
        concentration_ok = bool(
            (concentration_train["by_symbol"]["top_share"] or 1.0) <= max_symbol_share
            and (concentration_validation["by_symbol"]["top_share"] or 1.0)
            <= max_symbol_share
        )

        loso_train = _leave_one_symbol_out(
            train,
            predicate=predicate,
            landmark_bar=landmark_bar,
            reaction_horizon=reaction_horizon,
        )
        loso_validation = _leave_one_symbol_out(
            validation,
            predicate=predicate,
            landmark_bar=landmark_bar,
            reaction_horizon=reaction_horizon,
        )
        loso_ok = bool(loso_train["all_direction_ok"] and loso_validation["all_direction_ok"])

        family = _group_stability(
            train,
            validation,
            dimension="pattern_family",
            predicate=predicate,
            landmark_bar=landmark_bar,
            reaction_horizon=reaction_horizon,
            min_train_baseline_pending=15,
            min_train_gated_pending=5,
            min_validation_baseline_pending=8,
            min_validation_gated_pending=3,
            required_groups=2,
        )
        direction = _group_stability(
            train,
            validation,
            dimension="direction",
            predicate=predicate,
            landmark_bar=landmark_bar,
            reaction_horizon=reaction_horizon,
            min_train_baseline_pending=20,
            min_train_gated_pending=8,
            min_validation_baseline_pending=10,
            min_validation_gated_pending=5,
            required_groups=2,
        )

        train_time = _time_segments(
            train,
            predicate=predicate,
            landmark_bar=landmark_bar,
            reaction_horizon=reaction_horizon,
            segments=3,
            min_baseline_pending=20,
            min_gated_pending=8,
        )
        validation_time = _time_segments(
            validation,
            predicate=predicate,
            landmark_bar=landmark_bar,
            reaction_horizon=reaction_horizon,
            segments=2,
            min_baseline_pending=15,
            min_gated_pending=5,
        )
        temporal_ok = bool(
            train_time["eligible_segments"] >= 3
            and (train_time["direction_ok_ratio"] or 0.0) >= (2 / 3)
            and validation_time["eligible_segments"] >= 2
            and validation_time["direction_ok_segments"]
            == validation_time["eligible_segments"]
        )

        scale = _scale_diversity(
            train_gated,
            validation_gated,
            landmark_bar=landmark_bar,
        )

        blockers: list[str] = []
        if not visible_direction_ok:
            blockers.append("visible_split_direction")
        if not sample_floor_ok:
            blockers.append("candidate_sample_floor")
        if not concentration_ok:
            blockers.append("symbol_concentration")
        if not loso_ok:
            blockers.append("leave_one_symbol_out")
        if not family["generalizes"]:
            blockers.append("family_generalization")
        if not direction["generalizes"]:
            blockers.append("bull_bear_generalization")
        if not temporal_ok:
            blockers.append("temporal_stability")
        if not scale["diverse"]:
            blockers.append("scale_diversity")

        candidate_robust = not blockers
        if candidate_robust:
            robust.append(name)
        cohort_reports.append(
            {
                "name": name,
                "description": description,
                "train": train_metrics,
                "validation": validation_metrics,
                "sample_floor": {
                    "ok": sample_floor_ok,
                    "minimum_train_pending": minimum_train_candidate_pending,
                    "minimum_validation_pending": minimum_validation_candidate_pending,
                },
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
                "direction_stability": direction,
                "temporal_stability": {
                    "ok": temporal_ok,
                    "train": train_time,
                    "validation": validation_time,
                },
                "scale_diversity": scale,
                "blockers": blockers,
                "robust_research_candidate": candidate_robust,
                "eligible_for_policy_freeze": False,
            }
        )

    expected = early_path_report.get("split_counts") or {}
    observed = {name: len(rows) for name, rows in splits.items()}
    return {
        **base,
        "status": "type_i_early_path_robustness_holdout_sealed",
        "reaction_horizon_bars": reaction_horizon,
        "landmark_bar": landmark_bar,
        "terminal_events": len(events),
        "purged_records": len(purged),
        "visible_records": {"train": len(train), "validation": len(validation)},
        "split_consistency_with_m2_18": {
            "expected": {
                "train": int(expected.get("train", 0)),
                "validation": int(expected.get("validation", 0)),
                "holdout": int(expected.get("holdout", 0)),
            },
            "observed": observed,
            "matches": all(
                int(expected.get(name, -1)) == observed[name]
                for name in ("train", "validation", "holdout")
            ),
        },
        "candidates_in": candidates,
        "robust_candidates": robust,
        "cohorts": cohort_reports,
    }
