from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from copy import deepcopy
from typing import Any

import pandas as pd

from .time_split import assign_purged_split, derive_boundaries

ACTIONABLE_COMPLETED_OUTCOMES = {
    "t2_within_horizon",
    "t1_only_within_horizon",
    "no_t1_within_horizon",
}


def attach_completed_reaction_observation_windows(
    records: Iterable[dict[str, Any]],
    *,
    trade_dates: Sequence[Any],
    horizon: int,
) -> list[dict[str, Any]]:
    """Attach the exact forward-label end date used by completed-reaction calibration.

    ``signal_bar`` is already the first observable terminal-Pivot confirmation bar. The
    observation window therefore starts there and ends ``horizon`` trading bars later, or at
    the available dataset end for immature rows. This timestamp is metadata for purging only;
    it cannot change pattern identity or outcome labels.
    """
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    dates = [pd.Timestamp(value).date().isoformat() for value in trade_dates]
    if not dates:
        return []

    out: list[dict[str, Any]] = []
    for source in records:
        row = dict(source)
        signal_bar = int(row["signal_bar"])
        if signal_bar < 0 or signal_bar >= len(dates):
            raise ValueError("completed reaction signal_bar is outside trade_dates")
        observation_end_bar = min(signal_bar + int(horizon), len(dates) - 1)
        outcome = row.get("outcome") or {}
        row["confirmation_lag_bars"] = int(outcome.get("confirmation_lag_bars", 0))
        row["observation_end_bar"] = int(observation_end_bar)
        row["observation_end_trade_date"] = dates[observation_end_bar]
        out.append(row)
    return out


def actionable_completed_reaction_records(
    records: Iterable[dict[str, Any]],
    *,
    horizon: int,
) -> list[dict[str, Any]]:
    """Return completed reactions that were observable and fully mature after confirmation."""
    if horizon < 1:
        raise ValueError("horizon must be >= 1")

    out: list[dict[str, Any]] = []
    for row in records:
        outcome = row.get("outcome") or {}
        if outcome.get("outcome_class") not in ACTIONABLE_COMPLETED_OUTCOMES:
            continue
        if outcome.get("late_completion_signal"):
            continue
        if int(outcome.get("available_future_bars_after_confirmation", 0)) < horizon:
            continue
        if not row.get("signal_trade_date") or not row.get("observation_end_trade_date"):
            raise ValueError("mature completed reaction is missing split timestamps")
        out.append(row)

    out.sort(
        key=lambda row: (
            str(row["signal_trade_date"]),
            str(row["instrument_id"]),
            int(row["signal_bar"]),
            str(row["pattern_id"]),
        )
    )
    return out


def completed_reaction_inventory(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Outcome-free inventory safe to expose while the reaction Holdout is sealed."""
    rows = list(records)
    dates = sorted(str(row["signal_trade_date"]) for row in rows)
    return {
        "records": len(rows),
        "signal_start": dates[0] if dates else None,
        "signal_end": dates[-1] if dates else None,
        "by_pattern": dict(sorted(Counter(str(row["pattern_id"]) for row in rows).items())),
        "by_family": dict(sorted(Counter(str(row["pattern_family"]) for row in rows).items())),
        "outcome_metrics_exposed": False,
    }


def _reaction_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    outcomes = Counter(row["outcome"]["outcome_class"] for row in rows)
    t1 = int(outcomes.get("t1_only_within_horizon", 0) + outcomes.get("t2_within_horizon", 0))
    t2 = int(outcomes.get("t2_within_horizon", 0))
    count = len(rows)
    return {
        "records": count,
        "t1_within_horizon": t1,
        "t2_within_horizon": t2,
        "t1_rate": None if not count else t1 / count,
        "t2_rate": None if not count else t2 / count,
        "by_outcome": dict(sorted(outcomes.items())),
        "by_pattern": dict(sorted(Counter(str(row["pattern_id"]) for row in rows).items())),
        "by_family": dict(sorted(Counter(str(row["pattern_family"]) for row in rows).items())),
    }


def _sealed_holdout_manifest(rows: list[dict[str, Any]]) -> dict[str, Any]:
    dates = sorted(str(row["signal_trade_date"]) for row in rows)
    return {
        "sealed": True,
        "records": len(rows),
        "signal_start": dates[0] if dates else None,
        "signal_end": dates[-1] if dates else None,
        "by_pattern": dict(sorted(Counter(str(row["pattern_id"]) for row in rows).items())),
        "by_family": dict(sorted(Counter(str(row["pattern_family"]) for row in rows).items())),
        "outcomes_exposed": False,
    }


def build_completed_reaction_calibration(
    records: Iterable[dict[str, Any]],
    *,
    horizon: int,
    minimum_actionable_records: int = 60,
    minimum_train_records: int = 30,
    minimum_validation_records: int = 10,
    minimum_holdout_records: int = 10,
) -> dict[str, Any]:
    """Build a purged chronological calibration view while keeping Holdout outcomes sealed.

    The sample floors are HT-CN research-governance policy. They do not alter Carney identity,
    PRZ construction, Pivot selection or post-completion target definitions.
    """
    if min(
        horizon,
        minimum_actionable_records,
        minimum_train_records,
        minimum_validation_records,
        minimum_holdout_records,
    ) < 1:
        raise ValueError("horizon and sample floors must be >= 1")

    all_rows = list(records)
    actionable = actionable_completed_reaction_records(all_rows, horizon=horizon)
    distinct_dates = sorted({str(row["signal_trade_date"]) for row in actionable})

    base = {
        "observation_horizon_bars": int(horizon),
        "total_completed_records": len(all_rows),
        "actionable_mature_records": len(actionable),
        "late_or_immature_excluded": len(all_rows) - len(actionable),
        "sample_floor": {
            "actionable_total": int(minimum_actionable_records),
            "train": int(minimum_train_records),
            "validation": int(minimum_validation_records),
            "holdout": int(minimum_holdout_records),
        },
        "methodology": {
            "signal_clock": "The signal timestamp is the terminal Pivot confirmation bar, never historical D.",
            "purge": "Rows whose forward reaction window crosses the next chronological split boundary are purged.",
            "holdout": "Holdout identity metadata and counts are visible; Holdout T1/T2 outcomes remain sealed.",
            "identity": "No outcome statistic can create, delete, relabel or rescore a harmonic identity.",
            "sample_floor": "Sample floors are HT-CN research policy, not Carney rules or statistical guarantees.",
        },
    }

    if len(distinct_dates) < 5:
        return {
            **base,
            "status": "completed_reaction_sample_insufficient_holdout_sealed",
            "reason": "fewer_than_five_distinct_actionable_signal_dates",
            "boundaries": None,
            "purged_records": 0,
            "split_counts": {"train": 0, "validation": 0, "holdout": 0},
            "train": _reaction_summary([]),
            "validation": _reaction_summary([]),
            "holdout": _sealed_holdout_manifest([]),
        }

    boundaries = derive_boundaries(actionable)
    splits, purged = assign_purged_split(actionable, boundaries)
    train = splits["train"]
    validation = splits["validation"]
    holdout = splits["holdout"]
    split_counts = {
        "train": len(train),
        "validation": len(validation),
        "holdout": len(holdout),
    }

    adequate = (
        len(actionable) >= minimum_actionable_records
        and len(train) >= minimum_train_records
        and len(validation) >= minimum_validation_records
        and len(holdout) >= minimum_holdout_records
    )
    reason = None
    if not adequate:
        reason = "actionable_completed_reaction_sample_below_research_floor_after_purge"

    return {
        **base,
        "status": (
            "completed_reaction_calibration_holdout_sealed"
            if adequate
            else "completed_reaction_sample_insufficient_holdout_sealed"
        ),
        "reason": reason,
        "boundaries": {
            "train_end": boundaries.train_end,
            "validation_start": boundaries.validation_start,
            "validation_end": boundaries.validation_end,
            "holdout_start": boundaries.holdout_start,
        },
        "purged_records": len(purged),
        "purge_reasons": dict(sorted(Counter(str(row["purge_reason"]) for row in purged).items())),
        "split_counts": split_counts,
        "train": _reaction_summary(train),
        "validation": _reaction_summary(validation),
        "holdout": _sealed_holdout_manifest(holdout),
    }


def redact_completed_reaction_holdout(
    records: Iterable[dict[str, Any]],
    calibration: dict[str, Any],
) -> list[dict[str, Any]]:
    """Redact raw outcomes at/after the sealed Holdout boundary before artifact emission."""
    boundaries = calibration.get("boundaries")
    if not boundaries:
        return [deepcopy(row) for row in records]

    holdout_start = str(boundaries["holdout_start"])
    out: list[dict[str, Any]] = []
    for source in records:
        row = deepcopy(source)
        if str(row["signal_trade_date"]) >= holdout_start:
            row["outcome"] = {"sealed": True}
            row["holdout_outcome_sealed"] = True
        else:
            row["holdout_outcome_sealed"] = False
        out.append(row)
    return out
