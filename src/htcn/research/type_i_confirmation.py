from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from .quality_layers import pattern_family
from .time_split import SplitBoundaries, assign_purged_split

DEFAULT_TYPE_I_LANDMARK_BAR = 5


CohortPredicate = Callable[[dict[str, Any]], bool]


def _terminal_events(
    records: Iterable[dict[str, Any]],
    *,
    reaction_horizon: int,
) -> list[dict[str, Any]]:
    """Reconstruct the mature M2.17 Terminal-Bar population without opening Holdout labels."""
    out: list[dict[str, Any]] = []
    for row in records:
        audit = row.get("terminal_bar_audit") or {}
        if audit.get("status") != "terminal_price_bar_observed":
            continue
        if int(audit.get("available_future_bars_after_terminal", 0)) < reaction_horizon:
            continue
        out.append(
            {
                "instrument_id": row.get("instrument_id"),
                "pattern_id": row.get("pattern_id"),
                "pattern_family": pattern_family(row.get("pattern_id")),
                "schema": row.get("schema"),
                "direction": row.get("direction"),
                "source_scale": int(row.get("source_scale") or 0),
                "signal_bar": int(audit["terminal_bar"]),
                "signal_trade_date": str(audit["terminal_trade_date"]),
                "observation_end_trade_date": str(audit["reaction_observation_end_trade_date"]),
                "terminal_bar_audit": audit,
            }
        )
    out.sort(
        key=lambda row: (
            str(row["signal_trade_date"]),
            str(row.get("instrument_id")),
            str(row.get("pattern_id")),
            int(row.get("source_scale") or 0),
        )
    )
    return out


def _boundaries(calibration: dict[str, Any]) -> SplitBoundaries | None:
    payload = calibration.get("boundaries") or {}
    required = {"train_end", "validation_start", "validation_end", "holdout_start"}
    if not required.issubset(payload):
        return None
    return SplitBoundaries(
        train_end=str(payload["train_end"]),
        validation_start=str(payload["validation_start"]),
        validation_end=str(payload["validation_end"]),
        holdout_start=str(payload["holdout_start"]),
    )


def _bar_value(audit: dict[str, Any], key: str) -> int | None:
    value = audit.get(key)
    return None if value is None else int(value)


def _progression_summary(
    rows: Iterable[dict[str, Any]],
    *,
    landmark_bar: int,
    reaction_horizon: int,
) -> dict[str, Any]:
    values = list(rows)
    early_t1 = 0
    early_t2 = 0
    t1_pending = 0
    t2_pending = 0
    t1_after_landmark = 0
    t2_after_landmark = 0
    exit3 = 0
    exit5 = 0
    clean3 = 0
    clean5 = 0

    for row in values:
        audit = row["terminal_bar_audit"]
        t1 = _bar_value(audit, "bars_from_terminal_to_t1")
        t2 = _bar_value(audit, "bars_from_terminal_to_t2")
        exit_bar = _bar_value(audit, "bars_from_terminal_to_full_prz_exit")

        if t1 is not None and 1 <= t1 <= landmark_bar:
            early_t1 += 1
        if t2 is not None and 1 <= t2 <= landmark_bar:
            early_t2 += 1

        if t1 is None or t1 > landmark_bar:
            t1_pending += 1
            if t1 is not None and landmark_bar < t1 <= reaction_horizon:
                t1_after_landmark += 1
        if t2 is None or t2 > landmark_bar:
            t2_pending += 1
            if t2 is not None and landmark_bar < t2 <= reaction_horizon:
                t2_after_landmark += 1

        if exit_bar is not None and exit_bar <= 3:
            exit3 += 1
        if exit_bar is not None and exit_bar <= 5:
            exit5 += 1
        if not bool(audit.get("prz_overlap_within_t_plus_3")):
            clean3 += 1
        if not bool(audit.get("prz_overlap_within_t_plus_5")):
            clean5 += 1

    count = len(values)
    return {
        "records": count,
        "early_t1_by_landmark": early_t1,
        "early_t2_by_landmark": early_t2,
        "early_t1_rate": None if not count else early_t1 / count,
        "early_t2_rate": None if not count else early_t2 / count,
        "t1_pending_at_landmark": t1_pending,
        "t2_pending_at_landmark": t2_pending,
        "t1_first_hit_after_landmark_within_horizon": t1_after_landmark,
        "t2_first_hit_after_landmark_within_horizon": t2_after_landmark,
        "t1_after_landmark_rate_among_pending": (
            None if not t1_pending else t1_after_landmark / t1_pending
        ),
        "t2_after_landmark_rate_among_pending": (
            None if not t2_pending else t2_after_landmark / t2_pending
        ),
        "full_prz_exit_within_3_rate": None if not count else exit3 / count,
        "full_prz_exit_within_5_rate": None if not count else exit5 / count,
        "no_prz_overlap_within_3_rate": None if not count else clean3 / count,
        "no_prz_overlap_within_5_rate": None if not count else clean5 / count,
    }


def _cohort_library() -> dict[str, tuple[str, CohortPredicate]]:
    """Predeclared source-aligned path descriptions; no thresholds are fitted to outcomes."""

    def exit_by(limit: int) -> CohortPredicate:
        def predicate(row: dict[str, Any]) -> bool:
            value = _bar_value(
                row["terminal_bar_audit"], "bars_from_terminal_to_full_prz_exit"
            )
            return value is not None and value <= limit

        return predicate

    def no_overlap(limit: int) -> CohortPredicate:
        key = f"prz_overlap_within_t_plus_{limit}"
        return lambda row: not bool(row["terminal_bar_audit"].get(key))

    exit3 = exit_by(3)
    exit5 = exit_by(5)
    clean3 = no_overlap(3)
    clean5 = no_overlap(5)
    return {
        "full_prz_exit_by_t3": (
            "Conservative price-action proxy: the entire bar moved beyond the PRZ in the reversal direction by T+3.",
            exit3,
        ),
        "full_prz_exit_by_t5": (
            "Conservative price-action proxy: the entire bar moved beyond the PRZ in the reversal direction by T+5.",
            exit5,
        ),
        "no_prz_overlap_through_t3": (
            "No T+1..T+3 bar overlapped the original PRZ after the Terminal Price Bar.",
            clean3,
        ),
        "no_prz_overlap_through_t5": (
            "No T+1..T+5 bar overlapped the original PRZ after the Terminal Price Bar.",
            clean5,
        ),
        "exit_by_t3_and_no_overlap_through_t3": (
            "Joint descriptive cohort combining conservative PRZ exit and no PRZ overlap through T+3.",
            lambda row: exit3(row) and clean3(row),
        ),
        "exit_by_t5_and_no_overlap_through_t5": (
            "Joint descriptive cohort combining conservative PRZ exit and no PRZ overlap through T+5.",
            lambda row: exit5(row) and clean5(row),
        ),
    }


def build_type_i_early_path_report(
    records: Iterable[dict[str, Any]],
    terminal_bar_calibration: dict[str, Any],
    *,
    reaction_horizon: int = 20,
    landmark_bar: int = DEFAULT_TYPE_I_LANDMARK_BAR,
) -> dict[str, Any]:
    """Describe source-backed Type-I early path behavior without creating a trading rule.

    Early features stop at T+5. Any "after landmark" statistic starts at T+6, which avoids
    relabeling an already-achieved early target as evidence for that same target. Holdout
    outcome fields are never summarized or exposed.
    """
    if reaction_horizon < 1:
        raise ValueError("reaction_horizon must be >= 1")
    if landmark_bar < 1 or landmark_bar >= reaction_horizon:
        raise ValueError("landmark_bar must be >= 1 and < reaction_horizon")

    boundary = _boundaries(terminal_bar_calibration)
    if (
        terminal_bar_calibration.get("status") != "terminal_bar_calibration_holdout_sealed"
        or boundary is None
    ):
        return {
            "status": "type_i_early_path_not_ready_holdout_sealed",
            "reason": "terminal_bar_calibration_not_ready",
            "landmark_bar": landmark_bar,
            "reaction_horizon_bars": reaction_horizon,
            "policy_frozen": False,
            "holdout": {"sealed": True, "outcomes_exposed": False},
        }

    events = _terminal_events(records, reaction_horizon=reaction_horizon)
    splits, purged = assign_purged_split(events, boundary)
    train = splits["train"]
    validation = splits["validation"]

    cohorts: list[dict[str, Any]] = []
    for name, (description, predicate) in _cohort_library().items():
        train_rows = [row for row in train if predicate(row)]
        validation_rows = [row for row in validation if predicate(row)]
        cohorts.append(
            {
                "name": name,
                "description": description,
                "train": _progression_summary(
                    train_rows,
                    landmark_bar=landmark_bar,
                    reaction_horizon=reaction_horizon,
                ),
                "validation": _progression_summary(
                    validation_rows,
                    landmark_bar=landmark_bar,
                    reaction_horizon=reaction_horizon,
                ),
                "eligible_for_policy_freeze": False,
            }
        )

    expected = terminal_bar_calibration.get("split_counts") or {}
    observed = {name: len(rows) for name, rows in splits.items()}
    return {
        "status": "type_i_early_path_evidence_holdout_sealed",
        "landmark_bar": landmark_bar,
        "reaction_horizon_bars": reaction_horizon,
        "terminal_events": len(events),
        "purged_records": len(purged),
        "split_counts": observed,
        "split_consistency_with_m2_17": {
            "expected": {
                "train": int(expected.get("train", 0)),
                "validation": int(expected.get("validation", 0)),
                "holdout": int(expected.get("holdout", 0)),
            },
            "matches": all(
                int(expected.get(name, -1)) == observed[name]
                for name in ("train", "validation", "holdout")
            ),
        },
        "baseline": {
            "train": _progression_summary(
                train,
                landmark_bar=landmark_bar,
                reaction_horizon=reaction_horizon,
            ),
            "validation": _progression_summary(
                validation,
                landmark_bar=landmark_bar,
                reaction_horizon=reaction_horizon,
            ),
        },
        "cohorts": cohorts,
        "holdout": {
            "sealed": True,
            "records": len(splits["holdout"]),
            "outcomes_exposed": False,
        },
        "policy_frozen": False,
        "eligible_for_policy_freeze": False,
        "methodology": {
            "source_clock": "All rows begin at the M2.17 source-aligned Terminal Price Bar.",
            "early_window": "Source-backed early-path descriptions use only T+1..T+5 behavior.",
            "three_to_five_bars": "The 3-5 bar cohorts are descriptive proxies; they do not turn Carney's qualitative clear-continuation language into an invented hard confirmation score.",
            "landmark": "Later-progression rates are measured only from T+6 onward among cases whose target remained pending at T+5.",
            "identity": "Early path evidence cannot create, delete, relabel or rescore harmonic identity.",
            "holdout": "M2.17 Holdout outcomes remain sealed; this report never summarizes them.",
        },
        "anti_leakage": {
            "carney_identity_changed": False,
            "cohort_thresholds_fitted_to_outcomes": False,
            "early_features_stop_at_t_plus_5": True,
            "later_progression_starts_at_t_plus_6": True,
            "m2_17_boundaries_reused": True,
            "holdout_outcomes_opened": False,
        },
    }
