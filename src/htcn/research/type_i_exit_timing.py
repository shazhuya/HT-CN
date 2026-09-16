from __future__ import annotations

from typing import Any, Iterable

from .time_split import assign_purged_split
from .type_i_confirmation import DEFAULT_TYPE_I_LANDMARK_BAR, _bar_value, _boundaries, _terminal_events


DEFAULT_MIN_EXCLUSIVE_TRAIN = 60
DEFAULT_MIN_EXCLUSIVE_VALIDATION = 20


def _t2_pending(row: dict[str, Any], *, landmark_bar: int) -> bool:
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


def _exit_bucket(row: dict[str, Any]) -> str:
    exit_bar = _bar_value(row["terminal_bar_audit"], "bars_from_terminal_to_full_prz_exit")
    if exit_bar is not None and 1 <= exit_bar <= 3:
        return "exit_by_t3"
    if exit_bar is not None and 4 <= exit_bar <= 5:
        return "exit_on_t4_t5"
    return "no_full_exit_by_t5"


def _summary(
    rows: Iterable[dict[str, Any]],
    *,
    landmark_bar: int,
    reaction_horizon: int,
) -> dict[str, Any]:
    values = [row for row in rows if _t2_pending(row, landmark_bar=landmark_bar)]
    hits = sum(
        _later_t2_hit(row, landmark_bar=landmark_bar, reaction_horizon=reaction_horizon)
        for row in values
    )
    return {
        "pending_records": len(values),
        "later_t2_hits": int(hits),
        "later_t2_rate": None if not values else hits / len(values),
    }


def _rate_diff(left: dict[str, Any], right: dict[str, Any]) -> float | None:
    left_rate = left.get("later_t2_rate")
    right_rate = right.get("later_t2_rate")
    if left_rate is None or right_rate is None:
        return None
    return float(left_rate) - float(right_rate)


def _visible_split_report(
    rows: list[dict[str, Any]],
    *,
    landmark_bar: int,
    reaction_horizon: int,
) -> dict[str, Any]:
    pending = [row for row in rows if _t2_pending(row, landmark_bar=landmark_bar)]
    groups = {
        name: [row for row in pending if _exit_bucket(row) == name]
        for name in ("exit_by_t3", "exit_on_t4_t5", "no_full_exit_by_t5")
    }
    summaries = {
        name: _summary(
            values,
            landmark_bar=landmark_bar,
            reaction_horizon=reaction_horizon,
        )
        for name, values in groups.items()
    }
    any_exit = groups["exit_by_t3"] + groups["exit_on_t4_t5"]
    any_exit_summary = _summary(
        any_exit,
        landmark_bar=landmark_bar,
        reaction_horizon=reaction_horizon,
    )
    return {
        "baseline": _summary(
            pending,
            landmark_bar=landmark_bar,
            reaction_horizon=reaction_horizon,
        ),
        "groups": summaries,
        "any_exit_by_t5": any_exit_summary,
        "comparisons": {
            "fast_minus_late": _rate_diff(
                summaries["exit_by_t3"], summaries["exit_on_t4_t5"]
            ),
            "late_minus_no_exit": _rate_diff(
                summaries["exit_on_t4_t5"], summaries["no_full_exit_by_t5"]
            ),
            "fast_minus_no_exit": _rate_diff(
                summaries["exit_by_t3"], summaries["no_full_exit_by_t5"]
            ),
            "any_exit_by_t5_minus_no_exit": _rate_diff(
                any_exit_summary, summaries["no_full_exit_by_t5"]
            ),
        },
    }


def _positive(value: Any) -> bool:
    return value is not None and float(value) > 0.0


def build_type_i_exit_timing_report(
    records: Iterable[dict[str, Any]],
    terminal_bar_calibration: dict[str, Any],
    early_path_report: dict[str, Any],
    robustness_report: dict[str, Any],
    *,
    reaction_horizon: int = 20,
    landmark_bar: int = DEFAULT_TYPE_I_LANDMARK_BAR,
    minimum_train_exclusive: int = DEFAULT_MIN_EXCLUSIVE_TRAIN,
    minimum_validation_exclusive: int = DEFAULT_MIN_EXCLUSIVE_VALIDATION,
) -> dict[str, Any]:
    """Resolve the nested T+3/T+5 exit cohorts without opening Holdout outcomes.

    M2.19 found both ``full_prz_exit_by_t3`` and ``full_prz_exit_by_t5`` robust. Because
    T+3 is a strict subset of T+5, treating them as two independent factors double-counts the
    same path information. M2.20 partitions T+5 behavior into three mutually exclusive groups:
    exit by T+3, first exit on T+4/T+5, and no full exit by T+5.

    The outcome remains the predeclared landmark target: among cases with T2 pending at T+5,
    first T2 hit from T+6 through the frozen reaction horizon. Holdout rows are assigned but
    never summarized.
    """
    holdout_records = int((early_path_report.get("holdout") or {}).get("records", 0))
    base = {
        "holdout": {"sealed": True, "records": holdout_records, "outcomes_exposed": False},
        "policy_frozen": False,
        "holdout_opened": False,
        "methodology": {
            "reason": "M2.19 T+3 and T+5 robust cohorts are nested and cannot be counted as independent evidence.",
            "exclusive_groups": "T+3 full exit vs first full exit on T+4/T+5 vs no full exit by T+5.",
            "target": "Among cases with T2 still pending at T+5, first T2 hit from T+6 through the frozen reaction horizon.",
            "selection_rule": "Prefer T+3 only if fast exit beats T+4/T+5 in both Train and Validation. Otherwise prefer T+5 only when T+4/T+5 still beats no-exit and pooled <=T+5 exit beats no-exit in both visible splits. Otherwise select none.",
            "sample_floor": f"Every exclusive exit group used to distinguish T+3 from T+5 requires >= {minimum_train_exclusive} Train and >= {minimum_validation_exclusive} Validation pending rows.",
            "holdout": "M2.17 Holdout outcomes remain sealed and are not summarized or used for selection.",
            "identity": "No Carney ratio, PRZ, Pivot, Terminal Price Bar or target definition is changed.",
        },
        "anti_leakage": {
            "new_numeric_threshold_search": False,
            "nested_groups_made_mutually_exclusive": True,
            "early_features_stop_at_t_plus_5": True,
            "later_progression_starts_at_t_plus_6": True,
            "m2_17_boundaries_reused": True,
            "holdout_outcomes_opened": False,
        },
    }

    boundary = _boundaries(terminal_bar_calibration)
    robust = set(str(name) for name in robustness_report.get("robust_candidates") or [])
    prerequisites = bool(
        terminal_bar_calibration.get("status") == "terminal_bar_calibration_holdout_sealed"
        and early_path_report.get("status") == "type_i_early_path_evidence_holdout_sealed"
        and robustness_report.get("status") == "type_i_early_path_robustness_holdout_sealed"
        and boundary is not None
        and {"full_prz_exit_by_t3", "full_prz_exit_by_t5"}.issubset(robust)
    )
    if not prerequisites:
        return {
            **base,
            "status": "type_i_exit_timing_not_ready_holdout_sealed",
            "reason": "m2_17_m2_18_or_m2_19_prerequisite_missing",
            "selected_hypothesis": None,
            "eligible_for_preregistration": False,
        }

    events = _terminal_events(records, reaction_horizon=reaction_horizon)
    splits, purged = assign_purged_split(events, boundary)
    train = _visible_split_report(
        splits["train"], landmark_bar=landmark_bar, reaction_horizon=reaction_horizon
    )
    validation = _visible_split_report(
        splits["validation"], landmark_bar=landmark_bar, reaction_horizon=reaction_horizon
    )

    train_groups = train["groups"]
    validation_groups = validation["groups"]
    exclusive_floor_ok = all(
        (
            train_groups[name]["pending_records"] >= minimum_train_exclusive
            and validation_groups[name]["pending_records"] >= minimum_validation_exclusive
        )
        for name in ("exit_by_t3", "exit_on_t4_t5")
    )
    speed_advantage = bool(
        _positive(train["comparisons"]["fast_minus_late"])
        and _positive(validation["comparisons"]["fast_minus_late"])
    )
    late_exit_adds_value = bool(
        _positive(train["comparisons"]["late_minus_no_exit"])
        and _positive(validation["comparisons"]["late_minus_no_exit"])
    )
    pooled_exit_adds_value = bool(
        _positive(train["comparisons"]["any_exit_by_t5_minus_no_exit"])
        and _positive(validation["comparisons"]["any_exit_by_t5_minus_no_exit"])
    )

    selected: str | None = None
    rationale = "visible evidence does not isolate one nested exit-timing hypothesis"
    if exclusive_floor_ok and speed_advantage and pooled_exit_adds_value:
        selected = "full_prz_exit_by_t3"
        rationale = "T+3 exit beats T+4/T+5 in both visible splits; earlier exit adds incremental information."
    elif exclusive_floor_ok and late_exit_adds_value and pooled_exit_adds_value:
        selected = "full_prz_exit_by_t5"
        rationale = "T+4/T+5 exits still outperform no-exit while T+3 does not consistently outperform T+4/T+5; the evidence supports a five-bar deadline rather than a speed gradient."

    return {
        **base,
        "status": "type_i_exit_timing_evidence_holdout_sealed",
        "landmark_bar": landmark_bar,
        "reaction_horizon_bars": reaction_horizon,
        "terminal_events": len(events),
        "purged_records": len(purged),
        "split_counts": {name: len(rows) for name, rows in splits.items()},
        "train": train,
        "validation": validation,
        "decision_checks": {
            "exclusive_sample_floor_ok": exclusive_floor_ok,
            "speed_advantage_fast_over_late_in_both_visible_splits": speed_advantage,
            "late_exit_beats_no_exit_in_both_visible_splits": late_exit_adds_value,
            "pooled_exit_by_t5_beats_no_exit_in_both_visible_splits": pooled_exit_adds_value,
        },
        "selected_hypothesis": selected,
        "selection_rationale": rationale,
        "eligible_for_preregistration": selected is not None,
        "eligible_for_policy_freeze": False,
        "holdout": {
            "sealed": True,
            "records": len(splits["holdout"]),
            "outcomes_exposed": False,
        },
    }
