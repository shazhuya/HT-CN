from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from math import floor
from statistics import median
from typing import Any, Iterable

import pandas as pd


@dataclass(frozen=True, slots=True)
class SplitBoundaries:
    train_end: str
    validation_start: str
    validation_end: str
    holdout_start: str


@dataclass(frozen=True, slots=True)
class NumericThresholds:
    prz_width_ratio: tuple[float, float, float]
    distance_to_prz_ratio: tuple[float, float, float]
    confirmation_lag_bars: tuple[float, float, float]


def _date(value: Any) -> pd.Timestamp:
    return pd.Timestamp(value).normalize()


def mature_forward_records(records: Iterable[dict[str, Any]], *, horizon: int = 60) -> list[dict[str, Any]]:
    """Return only forward-eligible records with a complete outcome window."""
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    out: list[dict[str, Any]] = []
    for row in records:
        outcome = row.get("outcome") or {}
        if outcome.get("pre_signal_prz_touch_bar") is not None:
            continue
        if int(outcome.get("available_future_bars", 0)) < horizon:
            continue
        if not row.get("observation_end_trade_date"):
            raise ValueError("mature record missing observation_end_trade_date")
        out.append(row)
    return out


def derive_boundaries(
    records: Iterable[dict[str, Any]],
    *,
    train_fraction: float = 0.60,
    validation_fraction: float = 0.20,
) -> SplitBoundaries:
    """Derive one global chronological train/validation/holdout split.

    The split depends only on signal timestamps, never on later outcomes. Purging is handled
    separately using each record's observation-end timestamp.
    """
    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be between 0 and 1")
    if not 0 < validation_fraction < 1:
        raise ValueError("validation_fraction must be between 0 and 1")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("train + validation fractions must leave a holdout")

    dates = sorted({_date(row["signal_trade_date"]) for row in records})
    if len(dates) < 5:
        raise ValueError("at least five distinct signal dates are required")

    n = len(dates)
    train_end_index = min(max(floor(n * train_fraction) - 1, 0), n - 3)
    validation_end_index = min(
        max(floor(n * (train_fraction + validation_fraction)) - 1, train_end_index + 1),
        n - 2,
    )
    validation_start_index = train_end_index + 1
    holdout_start_index = validation_end_index + 1
    return SplitBoundaries(
        train_end=dates[train_end_index].date().isoformat(),
        validation_start=dates[validation_start_index].date().isoformat(),
        validation_end=dates[validation_end_index].date().isoformat(),
        holdout_start=dates[holdout_start_index].date().isoformat(),
    )


def assign_purged_split(
    records: Iterable[dict[str, Any]], boundaries: SplitBoundaries
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    """Assign chronological splits and purge labels that cross the next split boundary."""
    train_end = _date(boundaries.train_end)
    validation_start = _date(boundaries.validation_start)
    validation_end = _date(boundaries.validation_end)
    holdout_start = _date(boundaries.holdout_start)
    splits: dict[str, list[dict[str, Any]]] = {"train": [], "validation": [], "holdout": []}
    purged: list[dict[str, Any]] = []

    for row in records:
        signal_date = _date(row["signal_trade_date"])
        observation_end = _date(row["observation_end_trade_date"])
        enriched = dict(row)
        if signal_date <= train_end:
            if observation_end >= validation_start:
                enriched["purge_reason"] = "train_label_crosses_validation_start"
                purged.append(enriched)
            else:
                splits["train"].append(enriched)
        elif signal_date <= validation_end:
            if signal_date < validation_start:
                raise AssertionError("validation timestamp fell inside an impossible boundary gap")
            if observation_end >= holdout_start:
                enriched["purge_reason"] = "validation_label_crosses_holdout_start"
                purged.append(enriched)
            else:
                splits["validation"].append(enriched)
        else:
            if signal_date < holdout_start:
                raise AssertionError("holdout timestamp fell inside an impossible boundary gap")
            splits["holdout"].append(enriched)

    for values in splits.values():
        values.sort(key=lambda row: (row["signal_trade_date"], row["instrument_id"], row["signal_bar"]))
    return splits, purged


def _quartiles(values: list[float]) -> tuple[float, float, float]:
    if not values:
        return (0.0, 0.0, 0.0)
    series = pd.Series(values, dtype="float64")
    return tuple(float(series.quantile(q)) for q in (0.25, 0.50, 0.75))  # type: ignore[return-value]


def learn_numeric_thresholds(train_records: Iterable[dict[str, Any]]) -> NumericThresholds:
    """Learn descriptive bucket cutoffs from TRAIN only."""
    width: list[float] = []
    distance: list[float] = []
    lag: list[float] = []
    for row in train_records:
        quality = row.get("quality_at_signal") or {}
        if quality.get("prz_width_ratio") is not None:
            width.append(float(quality["prz_width_ratio"]))
        if quality.get("distance_to_prz_ratio") is not None:
            distance.append(float(quality["distance_to_prz_ratio"]))
        lag.append(float(row.get("confirmation_lag_bars", 0)))
    return NumericThresholds(
        prz_width_ratio=_quartiles(width),
        distance_to_prz_ratio=_quartiles(distance),
        confirmation_lag_bars=_quartiles(lag),
    )


def _bucket(value: float | None, thresholds: tuple[float, float, float]) -> str:
    if value is None:
        return "missing"
    q1, q2, q3 = thresholds
    if value <= q1:
        return "Q1_low"
    if value <= q2:
        return "Q2"
    if value <= q3:
        return "Q3"
    return "Q4_high"


def signal_features(row: dict[str, Any], thresholds: NumericThresholds) -> dict[str, Any]:
    """Return features available at signal time only."""
    quality = row.get("quality_at_signal") or {}
    return {
        "pattern_id": str(row["pattern_id"]),
        "schema": str(row["schema"]),
        "direction": str(row["direction"]),
        "source_scale": int(row["source_scale"]),
        "scale_support_count": len(row.get("signal_scales") or []),
        "source_tolerance_used": bool(quality.get("source_tolerance_used", False)),
        "prz_width_bucket": _bucket(
            None if quality.get("prz_width_ratio") is None else float(quality["prz_width_ratio"]),
            thresholds.prz_width_ratio,
        ),
        "distance_to_prz_bucket": _bucket(
            None if quality.get("distance_to_prz_ratio") is None else float(quality["distance_to_prz_ratio"]),
            thresholds.distance_to_prz_ratio,
        ),
        "confirmation_lag_bucket": _bucket(
            float(row.get("confirmation_lag_bars", 0)), thresholds.confirmation_lag_bars
        ),
    }


def _event_flags(row: dict[str, Any], horizon: int) -> dict[str, bool]:
    outcome = row["outcome"]
    touch_bars = outcome.get("bars_to_first_future_prz_touch")
    completion_bars = outcome.get("bars_to_completion_confirmation")
    retirement_bars = outcome.get("bars_to_frontier_retirement")
    touched = bool(
        outcome.get("touch_before_retirement")
        and touch_bars is not None
        and 0 <= int(touch_bars) <= horizon
    )
    completed = bool(
        outcome.get("completion_before_retirement")
        and completion_bars is not None
        and 0 <= int(completion_bars) <= horizon
    )
    retired_without_touch = bool(
        retirement_bars is not None
        and 0 <= int(retirement_bars) <= horizon
        and not touched
    )
    return {
        "touched": touched,
        "completed": completed,
        "retired_without_touch": retired_without_touch,
    }


def outcome_summary(records: Iterable[dict[str, Any]], *, horizon: int = 60) -> dict[str, Any]:
    rows = list(records)
    n = len(rows)
    flags = [_event_flags(row, horizon) for row in rows]
    touches = sum(flag["touched"] for flag in flags)
    completions = sum(flag["completed"] for flag in flags)
    retired = sum(flag["retired_without_touch"] for flag in flags)
    touch_leads = [
        int(row["outcome"]["bars_to_first_future_prz_touch"])
        for row, flag in zip(rows, flags)
        if flag["touched"]
    ]
    return {
        "records": n,
        "touches": touches,
        "completions": completions,
        "retired_without_touch": retired,
        "touch_rate": None if n == 0 else touches / n,
        "completion_rate": None if n == 0 else completions / n,
        "retirement_rate": None if n == 0 else retired / n,
        "median_bars_to_touch": None if not touch_leads else median(touch_leads),
    }


def grouped_summary(
    records: Iterable[dict[str, Any]],
    *,
    thresholds: NumericThresholds,
    horizon: int = 60,
    min_group_size: int = 5,
) -> dict[str, list[dict[str, Any]]]:
    rows = list(records)
    dimensions = (
        "pattern_id",
        "schema",
        "source_scale",
        "scale_support_count",
        "source_tolerance_used",
        "prz_width_bucket",
        "distance_to_prz_bucket",
        "confirmation_lag_bucket",
    )
    result: dict[str, list[dict[str, Any]]] = {}
    feature_rows = [(row, signal_features(row, thresholds)) for row in rows]
    for dimension in dimensions:
        groups: dict[Any, list[dict[str, Any]]] = defaultdict(list)
        for row, features in feature_rows:
            groups[features[dimension]].append(row)
        stats: list[dict[str, Any]] = []
        for value, members in groups.items():
            if len(members) < min_group_size:
                continue
            stats.append({"value": value, **outcome_summary(members, horizon=horizon)})
        stats.sort(key=lambda item: (-int(item["records"]), str(item["value"])))
        result[dimension] = stats
    return result


def split_manifest(
    splits: dict[str, list[dict[str, Any]]],
    *,
    purged: list[dict[str, Any]],
    boundaries: SplitBoundaries,
) -> dict[str, Any]:
    def one(name: str) -> dict[str, Any]:
        rows = splits[name]
        dates = [row["signal_trade_date"] for row in rows]
        return {
            "records": len(rows),
            "first_signal_date": None if not dates else min(dates),
            "last_signal_date": None if not dates else max(dates),
            "by_pattern": dict(sorted(Counter(row["pattern_id"] for row in rows).items())),
        }

    return {
        "boundaries": {
            "train_end": boundaries.train_end,
            "validation_start": boundaries.validation_start,
            "validation_end": boundaries.validation_end,
            "holdout_start": boundaries.holdout_start,
        },
        "train": one("train"),
        "validation": one("validation"),
        "holdout": one("holdout"),
        "purged_boundary_records": len(purged),
        "purge_reasons": dict(sorted(Counter(row["purge_reason"] for row in purged).items())),
    }
