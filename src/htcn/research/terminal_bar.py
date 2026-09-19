from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from copy import deepcopy
from typing import Any

import pandas as pd

from .quality_layers import pattern_family
from .time_split import assign_purged_split, derive_boundaries

DEFAULT_TERMINAL_REACTION_HORIZON = 20
DEFAULT_TERMINAL_SAMPLE_FLOOR = 60


def _touches_prz(row: pd.Series, *, low: float, high: float) -> bool:
    return float(row["low"]) <= float(high) and float(row["high"]) >= float(low)


def _tests_prz_extreme(
    row: pd.Series,
    *,
    direction: str,
    low: float,
    high: float,
) -> bool:
    if direction == "bullish":
        return float(row["low"]) <= float(low)
    if direction == "bearish":
        return float(row["high"]) >= float(high)
    raise ValueError(f"unsupported direction: {direction}")


def _exits_prz_in_reversal_direction(
    row: pd.Series,
    *,
    direction: str,
    low: float,
    high: float,
) -> bool:
    if direction == "bullish":
        return float(row["low"]) > float(high)
    if direction == "bearish":
        return float(row["high"]) < float(low)
    raise ValueError(f"unsupported direction: {direction}")


def _first_bar(
    frame: pd.DataFrame,
    *,
    start: int,
    end: int,
    predicate,
) -> int | None:
    if start > end or start >= len(frame):
        return None
    lo = max(0, int(start))
    hi = min(int(end), len(frame) - 1)
    for index in range(lo, hi + 1):
        if predicate(frame.iloc[index]):
            return index
    return None


def _target_hit(row: pd.Series, *, target: float, direction: str) -> bool:
    if direction == "bullish":
        return float(row["high"]) >= float(target)
    if direction == "bearish":
        return float(row["low"]) <= float(target)
    raise ValueError(f"unsupported direction: {direction}")


def _reaction_targets(
    record: dict[str, Any],
    *,
    terminal_price: float,
) -> tuple[str, float, str, float]:
    points = {str(point["label"]): point for point in record.get("prefix_points") or []}
    direction = str(record["direction"])
    sign = 1.0 if direction == "bullish" else -1.0
    schema = str(record["schema"])

    if schema == "0XABC":
        if "B" not in points:
            raise ValueError("Shark forming projection is missing B")
        span = abs(float(points["B"]["price"]) - float(terminal_price))
        if span <= 0:
            raise ValueError("Shark B/C reaction span must be positive")
        return (
            "50%",
            float(terminal_price) + sign * 0.50 * span,
            "61.8%",
            float(terminal_price) + sign * 0.618 * span,
        )

    if "A" not in points:
        raise ValueError(f"{schema} forming projection is missing A")
    span = abs(float(points["A"]["price"]) - float(terminal_price))
    if span <= 0:
        raise ValueError("A/terminal reaction span must be positive")
    return (
        "38.2%",
        float(terminal_price) + sign * 0.382 * span,
        "61.8%",
        float(terminal_price) + sign * 0.618 * span,
    )


def audit_projected_terminal_price_bar(
    record: dict[str, Any],
    *,
    frame: pd.DataFrame,
    forming_horizon: int,
    reaction_horizon: int = DEFAULT_TERMINAL_REACTION_HORIZON,
) -> dict[str, Any]:
    """Audit the first source-aligned Terminal Price Bar from a no-lookahead projection.

    Carney Volume 3 defines the Terminal Price Bar as the bar that tests the final/extreme
    measurement of the PRZ, with execution beginning after that bar. This audit therefore does
    not wait for the terminal price extreme to become a right-confirmed Pivot. The later Pivot
    confirmation is retained only as retrospective audit evidence.
    """
    if forming_horizon < 1 or reaction_horizon < 1:
        raise ValueError("forming_horizon and reaction_horizon must be >= 1")
    required = {"trade_date", "high", "low", "close"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"terminal-bar frame missing columns: {sorted(missing)}")

    source = frame.sort_values("trade_date").reset_index(drop=True)
    if source.empty:
        return {"status": "empty_frame"}

    signal_bar = int(record["signal_bar"])
    if signal_bar < 0 or signal_bar >= len(source):
        raise ValueError("forming signal_bar is outside frame")
    direction = str(record["direction"])
    if direction not in {"bullish", "bearish"}:
        raise ValueError(f"unsupported direction: {direction}")

    prz = record.get("prz") or {}
    low = float(prz["price_low"])
    high = float(prz["price_high"])
    if low > high:
        raise ValueError("PRZ low must be <= high")

    outcome = record.get("outcome") or {}
    pre_signal_touch = outcome.get("pre_signal_prz_touch_bar")
    if pre_signal_touch is not None:
        return {
            "status": "projection_late_before_signal",
            "pre_signal_prz_touch_bar": int(pre_signal_touch),
            "source_semantics": "A projection is not execution-eligible if the PRZ was already tested before the forming signal became observable.",
        }

    end = min(signal_bar + int(forming_horizon), len(source) - 1)
    retired_at = outcome.get("frontier_retired_at_bar")
    if retired_at is not None:
        end = min(end, int(retired_at))

    first_entry = _first_bar(
        source,
        start=signal_bar + 1,
        end=end,
        predicate=lambda row: _touches_prz(row, low=low, high=high),
    )
    terminal_bar = _first_bar(
        source,
        start=signal_bar + 1,
        end=end,
        predicate=lambda row: _tests_prz_extreme(
            row,
            direction=direction,
            low=low,
            high=high,
        ),
    )
    if terminal_bar is None:
        return {
            "status": "no_terminal_price_bar_within_active_horizon",
            "first_prz_entry_bar": first_entry,
            "bars_to_first_prz_entry": None if first_entry is None else int(first_entry - signal_bar),
            "active_search_end_bar": int(end),
            "retired_at_bar": None if retired_at is None else int(retired_at),
            "source_semantics": "PRZ overlap alone is not the official Terminal Price Bar; the extreme/final PRZ measurement must be tested.",
        }

    terminal_row = source.iloc[terminal_bar]
    terminal_price = (
        float(terminal_row["low"]) if direction == "bullish" else float(terminal_row["high"])
    )
    t1_name, t1_price, t2_name, t2_price = _reaction_targets(
        record,
        terminal_price=terminal_price,
    )
    available = max(0, len(source) - 1 - terminal_bar)
    reaction_end = min(terminal_bar + int(reaction_horizon), len(source) - 1)
    t1_hit_bar = _first_bar(
        source,
        start=terminal_bar + 1,
        end=len(source) - 1,
        predicate=lambda row: _target_hit(row, target=t1_price, direction=direction),
    )
    t2_hit_bar = _first_bar(
        source,
        start=terminal_bar + 1,
        end=len(source) - 1,
        predicate=lambda row: _target_hit(row, target=t2_price, direction=direction),
    )
    bars_to_t1 = None if t1_hit_bar is None else int(t1_hit_bar - terminal_bar)
    bars_to_t2 = None if t2_hit_bar is None else int(t2_hit_bar - terminal_bar)
    t1_within = bars_to_t1 is not None and bars_to_t1 <= reaction_horizon
    t2_within = bars_to_t2 is not None and bars_to_t2 <= reaction_horizon

    first_exit = _first_bar(
        source,
        start=terminal_bar + 1,
        end=min(terminal_bar + 5, len(source) - 1),
        predicate=lambda row: _exits_prz_in_reversal_direction(
            row,
            direction=direction,
            low=low,
            high=high,
        ),
    )
    overlap_first_3 = any(
        _touches_prz(source.iloc[index], low=low, high=high)
        for index in range(terminal_bar + 1, min(terminal_bar + 3, len(source) - 1) + 1)
    )
    overlap_first_5 = any(
        _touches_prz(source.iloc[index], low=low, high=high)
        for index in range(terminal_bar + 1, min(terminal_bar + 5, len(source) - 1) + 1)
    )

    if available < reaction_horizon:
        outcome_class = "immature"
    elif t2_within:
        outcome_class = "t2_within_horizon"
    elif t1_within:
        outcome_class = "t1_only_within_horizon"
    else:
        outcome_class = "no_t1_within_horizon"

    later_terminal = outcome.get("completion_terminal_bar")
    later_confirmation = outcome.get("completion_confirmed_at_bar")
    return {
        "status": "terminal_price_bar_observed",
        "projected_pattern_id": str(record["pattern_id"]),
        "schema": str(record["schema"]),
        "direction": direction,
        "forming_signal_bar": signal_bar,
        "forming_signal_trade_date": pd.Timestamp(source.iloc[signal_bar]["trade_date"]).date().isoformat(),
        "first_prz_entry_bar": first_entry,
        "bars_to_first_prz_entry": None if first_entry is None else int(first_entry - signal_bar),
        "terminal_bar": int(terminal_bar),
        "terminal_trade_date": pd.Timestamp(terminal_row["trade_date"]).date().isoformat(),
        "bars_from_forming_signal_to_terminal_bar": int(terminal_bar - signal_bar),
        "terminal_price": terminal_price,
        "prz": {"price_low": low, "price_high": high},
        "reaction_horizon_bars": int(reaction_horizon),
        "available_future_bars_after_terminal": int(available),
        "reaction_observation_end_bar": int(reaction_end),
        "reaction_observation_end_trade_date": pd.Timestamp(
            source.iloc[reaction_end]["trade_date"]
        ).date().isoformat(),
        "t1_name": t1_name,
        "t1_price": float(t1_price),
        "t2_name": t2_name,
        "t2_price": float(t2_price),
        "bars_from_terminal_to_t1": bars_to_t1,
        "bars_from_terminal_to_t2": bars_to_t2,
        "t1_within_horizon": bool(t1_within),
        "t2_within_horizon": bool(t2_within),
        "outcome_class": outcome_class,
        "first_full_prz_exit_bar": first_exit,
        "bars_from_terminal_to_full_prz_exit": None
        if first_exit is None
        else int(first_exit - terminal_bar),
        "prz_overlap_within_t_plus_3": bool(overlap_first_3),
        "prz_overlap_within_t_plus_5": bool(overlap_first_5),
        "later_engine_completion_terminal_bar": later_terminal,
        "later_engine_completion_confirmed_at_bar": later_confirmation,
        "same_terminal_bar_as_later_confirmed_completion": bool(
            later_terminal is not None and int(later_terminal) == int(terminal_bar)
        ),
        "bars_from_terminal_to_later_pivot_confirmation": None
        if later_confirmation is None
        else int(later_confirmation) - int(terminal_bar),
        "source_semantics": {
            "official_completion_event": "Terminal Price Bar tests the final/extreme PRZ measurement; this is distinct from later right-side Pivot confirmation.",
            "type_i_timing": "3-5 bar fields are descriptive evidence only; HT-CN does not turn Carney's qualitative 'clear continuation' language into an invented hard pass/fail score.",
            "targets": "Standard projected structures use 38.2%/61.8% from the terminal extreme toward A; Shark uses 50%/61.8% of B-to-terminal span.",
        },
    }


def _event_rows(records: Iterable[dict[str, Any]], *, reaction_horizon: int) -> list[dict[str, Any]]:
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
                "pattern_family": pattern_family(str(row.get("pattern_id"))),
                "schema": row.get("schema"),
                "direction": row.get("direction"),
                "source_scale": row.get("source_scale"),
                "signal_bar": int(audit["terminal_bar"]),
                "signal_trade_date": str(audit["terminal_trade_date"]),
                "observation_end_trade_date": str(audit["reaction_observation_end_trade_date"]),
                "terminal_bar_audit": audit,
                "outcome": {"outcome_class": str(audit["outcome_class"])},
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


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(rows)
    classes = Counter(str(row["outcome"]["outcome_class"]) for row in rows)
    t1 = int(classes.get("t1_only_within_horizon", 0) + classes.get("t2_within_horizon", 0))
    t2 = int(classes.get("t2_within_horizon", 0))
    full_exit_3 = sum(
        (row["terminal_bar_audit"].get("bars_from_terminal_to_full_prz_exit") or 999) <= 3
        for row in rows
    )
    full_exit_5 = sum(
        (row["terminal_bar_audit"].get("bars_from_terminal_to_full_prz_exit") or 999) <= 5
        for row in rows
    )
    same_later = sum(
        bool(row["terminal_bar_audit"].get("same_terminal_bar_as_later_confirmed_completion"))
        for row in rows
    )
    return {
        "records": count,
        "t1_rate": None if not count else t1 / count,
        "t2_rate": None if not count else t2 / count,
        "full_prz_exit_within_3_rate": None if not count else full_exit_3 / count,
        "full_prz_exit_within_5_rate": None if not count else full_exit_5 / count,
        "same_terminal_bar_later_confirmed_rate": None if not count else same_later / count,
        "by_outcome": dict(sorted(classes.items())),
        "by_pattern": dict(sorted(Counter(str(row["pattern_id"]) for row in rows).items())),
        "by_family": dict(sorted(Counter(str(row["pattern_family"]) for row in rows).items())),
    }


def build_terminal_bar_calibration(
    records: Iterable[dict[str, Any]],
    *,
    reaction_horizon: int = DEFAULT_TERMINAL_REACTION_HORIZON,
    minimum_actionable_records: int = DEFAULT_TERMINAL_SAMPLE_FLOOR,
    minimum_train_records: int = 30,
    minimum_validation_records: int = 10,
    minimum_holdout_records: int = 10,
) -> dict[str, Any]:
    """Build a source-aligned Terminal Price Bar calibration with a sealed Holdout."""
    all_rows = list(records)
    events = _event_rows(all_rows, reaction_horizon=reaction_horizon)
    status_counts = Counter(
        str((row.get("terminal_bar_audit") or {}).get("status", "missing")) for row in all_rows
    )
    base = {
        "reaction_horizon_bars": int(reaction_horizon),
        "forming_records": len(all_rows),
        "terminal_bar_status_counts": dict(sorted(status_counts.items())),
        "mature_terminal_events": len(events),
        "sample_floor": {
            "total": int(minimum_actionable_records),
            "train": int(minimum_train_records),
            "validation": int(minimum_validation_records),
            "holdout": int(minimum_holdout_records),
        },
        "policy_frozen": False,
        "methodology": {
            "source_clock": "The execution clock starts at the projected structure's Terminal Price Bar, not at later right-confirmed Pivot confirmation.",
            "terminal_definition": "Bullish requires testing the PRZ low/extreme; bearish requires testing the PRZ high/extreme.",
            "first_overlap": "Entering any part of the PRZ is tracked separately and is not automatically called official completion.",
            "three_to_five_bars": "PRZ exit/overlap is reported descriptively; no invented numeric substitute for Carney's qualitative clear-continuation requirement is imposed.",
            "holdout": "Terminal-bar Holdout outcome rates remain sealed during iterative research.",
        },
    }
    distinct_dates = sorted({str(row["signal_trade_date"]) for row in events})
    if len(distinct_dates) < 5:
        return {
            **base,
            "status": "terminal_bar_sample_insufficient_holdout_sealed",
            "reason": "fewer_than_five_distinct_terminal_dates",
            "boundaries": None,
            "purged_records": 0,
            "split_counts": {"train": 0, "validation": 0, "holdout": 0},
            "train": _summary([]),
            "validation": _summary([]),
            "holdout": {"sealed": True, "records": 0, "outcomes_exposed": False},
        }

    boundaries = derive_boundaries(events)
    splits, purged = assign_purged_split(events, boundaries)
    counts = {name: len(rows) for name, rows in splits.items()}
    adequate = bool(
        len(events) >= minimum_actionable_records
        and counts["train"] >= minimum_train_records
        and counts["validation"] >= minimum_validation_records
        and counts["holdout"] >= minimum_holdout_records
    )
    holdout_dates = sorted(str(row["signal_trade_date"]) for row in splits["holdout"])
    return {
        **base,
        "status": (
            "terminal_bar_calibration_holdout_sealed"
            if adequate
            else "terminal_bar_sample_insufficient_holdout_sealed"
        ),
        "reason": None if adequate else "terminal_bar_sample_below_research_floor_after_purge",
        "boundaries": {
            "train_end": boundaries.train_end,
            "validation_start": boundaries.validation_start,
            "validation_end": boundaries.validation_end,
            "holdout_start": boundaries.holdout_start,
        },
        "purged_records": len(purged),
        "split_counts": counts,
        "train": _summary(splits["train"]),
        "validation": _summary(splits["validation"]),
        "holdout": {
            "sealed": True,
            "records": counts["holdout"],
            "signal_start": holdout_dates[0] if holdout_dates else None,
            "signal_end": holdout_dates[-1] if holdout_dates else None,
            "by_pattern": dict(
                sorted(Counter(str(row["pattern_id"]) for row in splits["holdout"]).items())
            ),
            "outcomes_exposed": False,
        },
    }


def redact_terminal_bar_holdout(
    records: Iterable[dict[str, Any]],
    calibration: dict[str, Any],
) -> list[dict[str, Any]]:
    """Optional helper for any future raw Terminal-Bar artifact emission."""
    boundary = (calibration.get("boundaries") or {}).get("holdout_start")
    out: list[dict[str, Any]] = []
    for original in records:
        row = deepcopy(original)
        audit = row.get("terminal_bar_audit") or {}
        if boundary and audit.get("terminal_trade_date") and str(audit["terminal_trade_date"]) >= str(boundary):
            row["terminal_bar_audit"] = {
                "status": audit.get("status"),
                "terminal_bar": audit.get("terminal_bar"),
                "terminal_trade_date": audit.get("terminal_trade_date"),
                "holdout_outcome_sealed": True,
            }
        out.append(row)
    return out
