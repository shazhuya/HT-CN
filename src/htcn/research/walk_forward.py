from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

import pandas as pd

from htcn.harmonic.abcd import evaluate_abcd, project_forming_abcd
from htcn.harmonic.candidates import SwingWindow
from htcn.harmonic.five_zero import evaluate_five_zero, project_forming_five_zero
from htcn.harmonic.models import HarmonicPoint, Pivot
from htcn.harmonic.pivots import collapse_same_kind_pivots, detect_pivot_events
from htcn.harmonic.scanner import classify_completed_xabcd, project_forming_xabcd
from htcn.harmonic.shark import evaluate_shark, project_forming_shark
import itertools

DEFAULT_FORWARD_HORIZON = 60
DEFAULT_WALK_FORWARD_SCALES = (3, 5, 8, 13, 21)


def _harmonic_points(pivots: Iterable[Pivot], labels: tuple[str, ...]) -> tuple[HarmonicPoint, ...]:
    chunk = tuple(pivots)
    return tuple(
        HarmonicPoint(label=label, index=int(pivot.index), price=float(pivot.price))
        for label, pivot in zip(labels, chunk)
    )


def _projection_key(candidate: dict[str, Any]) -> tuple[Any, ...]:
    return (
        str(candidate["pattern_id"]),
        str(candidate["schema"]),
        str(candidate["direction"]),
        tuple(int(point.index) for point in candidate["points"]),
    )


def _reference_span(schema: str, points: tuple[HarmonicPoint, ...]) -> tuple[str, float]:
    by_label = {point.label: point for point in points}
    if schema == "ABCD":
        pair, name = ("A", "B"), "AB"
    elif schema == "0XABC":
        pair, name = ("0", "B"), "0B"
    elif schema == "FIVE_ZERO":
        pair, name = ("B", "C"), "BC"
    else:
        pair, name = ("X", "A"), "XA"
    left, right = by_label.get(pair[0]), by_label.get(pair[1])
    if left is None or right is None:
        return name, 0.0
    return name, abs(float(right.price) - float(left.price))


def _projection_quality(
    *,
    schema: str,
    points: tuple[HarmonicPoint, ...],
    prz,
    source_tolerance_used: bool = False,
) -> dict[str, Any]:
    span_name, span = _reference_span(schema, points)
    width = float(prz.width)
    width_ratio = None if span <= 0 else width / span
    return {
        "reference_span_name": span_name,
        "reference_span": span,
        "prz_width": width,
        "prz_width_ratio": width_ratio,
        "source_tolerance_used": bool(source_tolerance_used),
    }


def _candidate_rank(candidate: dict[str, Any]) -> tuple[int, float, int]:
    quality = candidate["quality"]
    width_ratio = quality.get("prz_width_ratio")
    width_penalty = float("inf") if width_ratio is None else float(width_ratio)
    return (
        1 if not quality.get("source_tolerance_used") else 0,
        -width_penalty,
        int(candidate["scale"]),
    )


def _frontier_candidates(scale: int, pivots: list[Pivot]) -> list[dict[str, Any]]:
    """Project only the *current* frontier for one visible swing sequence."""

    out: list[dict[str, Any]] = []
    if len(pivots) >= 4:
        latest4 = tuple(pivots[-4:])
        if not any(left.kind == right.kind for left, right in itertools.pairwise(latest4)):
            window = SwingWindow(scale=scale, pivots=latest4)
            points = window.harmonic_points()
            for projection in project_forming_xabcd(window):
                out.append(
                    {
                        "pattern_id": projection.pattern_id,
                        "schema": "XABCD",
                        "direction": projection.direction.value,
                        "scale": scale,
                        "points": points,
                        "prz": projection.prz,
                        "quality": _projection_quality(
                            schema="XABCD",
                            points=points,
                            prz=projection.prz,
                            source_tolerance_used=projection.source_tolerance_used,
                        ),
                    }
                )

            shark_points = _harmonic_points(latest4, ("0", "X", "A", "B"))
            try:
                shark = project_forming_shark(shark_points)  # type: ignore[arg-type]
            except ValueError:
                shark = None
            if shark is not None:
                out.append(
                    {
                        "pattern_id": "shark",
                        "schema": "0XABC",
                        "direction": shark.direction.value,
                        "scale": scale,
                        "points": shark.points,
                        "prz": shark.prz,
                        "quality": _projection_quality(
                            schema="0XABC", points=shark.points, prz=shark.prz
                        ),
                    }
                )

            five_points = _harmonic_points(latest4, ("X", "A", "B", "C"))
            try:
                five = project_forming_five_zero(five_points)  # type: ignore[arg-type]
            except ValueError:
                five = None
            if five is not None:
                out.append(
                    {
                        "pattern_id": "five_zero",
                        "schema": "FIVE_ZERO",
                        "direction": five.direction.value,
                        "scale": scale,
                        "points": five.points,
                        "prz": five.prz,
                        "quality": _projection_quality(
                            schema="FIVE_ZERO", points=five.points, prz=five.prz
                        ),
                    }
                )

    if len(pivots) >= 3:
        latest3 = tuple(pivots[-3:])
        if not any(left.kind == right.kind for left, right in itertools.pairwise(latest3)):
            abcd_points = _harmonic_points(latest3, ("A", "B", "C"))
            try:
                abcd = project_forming_abcd(abcd_points)  # type: ignore[arg-type]
            except ValueError:
                abcd = None
            if abcd is not None:
                out.append(
                    {
                        "pattern_id": "abcd",
                        "schema": "ABCD",
                        "direction": abcd.direction.value,
                        "scale": scale,
                        "points": abcd.points,
                        "prz": abcd.prz,
                        "quality": _projection_quality(
                            schema="ABCD",
                            points=abcd.points,
                            prz=abcd.prz,
                            source_tolerance_used=abcd.source_tolerance_used,
                        ),
                    }
                )
    return out


def _completed_candidates(scale: int, pivots: list[Pivot]) -> list[dict[str, Any]]:
    """Classify only structures ending at the newest currently visible pivot."""

    out: list[dict[str, Any]] = []
    if len(pivots) >= 5:
        latest5 = tuple(pivots[-5:])
        if not any(left.kind == right.kind for left, right in itertools.pairwise(latest5)):
            window = SwingWindow(scale=scale, pivots=latest5)
            standard_points = window.harmonic_points()
            for evaluation in classify_completed_xabcd(window):
                out.append(
                    {
                        "pattern_id": evaluation.pattern_id,
                        "schema": "XABCD",
                        "direction": evaluation.direction.value,
                        "scale": scale,
                        "points": standard_points,
                    }
                )

            shark_points = _harmonic_points(latest5, ("0", "X", "A", "B", "C"))
            try:
                shark = evaluate_shark(shark_points)  # type: ignore[arg-type]
            except ValueError:
                shark = None
            if shark is not None and shark.passed:
                out.append(
                    {
                        "pattern_id": "shark",
                        "schema": "0XABC",
                        "direction": shark.direction.value,
                        "scale": scale,
                        "points": shark.points,
                    }
                )

            five_points = _harmonic_points(latest5, ("X", "A", "B", "C", "D"))
            try:
                five = evaluate_five_zero(five_points)  # type: ignore[arg-type]
            except ValueError:
                five = None
            if five is not None and five.passed:
                out.append(
                    {
                        "pattern_id": "five_zero",
                        "schema": "FIVE_ZERO",
                        "direction": five.direction.value,
                        "scale": scale,
                        "points": five.points,
                    }
                )

    if len(pivots) >= 4:
        latest4 = tuple(pivots[-4:])
        if not any(left.kind == right.kind for left, right in itertools.pairwise(latest4)):
            abcd_points = _harmonic_points(latest4, ("A", "B", "C", "D"))
            try:
                abcd = evaluate_abcd(abcd_points)  # type: ignore[arg-type]
            except ValueError:
                abcd = None
            if abcd is not None and abcd.passed:
                out.append(
                    {
                        "pattern_id": "abcd",
                        "schema": "ABCD",
                        "direction": abcd.direction.value,
                        "scale": scale,
                        "points": abcd.points,
                    }
                )
    return out


def _completed_prefix_key(candidate: dict[str, Any]) -> tuple[Any, ...]:
    points = tuple(candidate["points"][:-1])
    return (
        str(candidate["pattern_id"]),
        str(candidate["schema"]),
        str(candidate["direction"]),
        tuple(int(point.index) for point in points),
    )


def _bar_touches_prz(row: pd.Series, low: float, high: float) -> bool:
    return float(row["low"]) <= float(high) and float(row["high"]) >= float(low)


def _first_touch(frame: pd.DataFrame, *, start: int, end: int, low: float, high: float) -> int | None:
    if start > end or start >= len(frame):
        return None
    lo = max(0, int(start))
    hi = min(int(end), len(frame) - 1)
    for index in range(lo, hi + 1):
        if _bar_touches_prz(frame.iloc[index], low, high):
            return index
    return None


def _serialize_signal(
    candidate: dict[str, Any],
    *,
    signal_bar: int,
    signal_scales: list[int],
    dates: pd.Series,
    frame: pd.DataFrame,
) -> dict[str, Any]:
    points: tuple[HarmonicPoint, ...] = candidate["points"]
    prz = candidate["prz"]
    close = float(frame.iloc[signal_bar]["close"])
    if close < float(prz.price_low):
        distance = float(prz.price_low) - close
    elif close > float(prz.price_high):
        distance = close - float(prz.price_high)
    else:
        distance = 0.0
    span = float(candidate["quality"].get("reference_span") or 0.0)
    return {
        "pattern_id": str(candidate["pattern_id"]),
        "schema": str(candidate["schema"]),
        "direction": str(candidate["direction"]),
        "signal_bar": int(signal_bar),
        "signal_trade_date": pd.Timestamp(dates.iloc[signal_bar]).date().isoformat(),
        "source_scale": int(candidate["scale"]),
        "signal_scales": sorted({int(value) for value in signal_scales}),
        "prefix_points": [
            {
                "label": point.label,
                "index": int(point.index),
                "price": float(point.price),
                "trade_date": pd.Timestamp(dates.iloc[point.index]).date().isoformat(),
            }
            for point in points
        ],
        "terminal_pivot_bar": int(points[-1].index),
        "confirmation_lag_bars": int(signal_bar - points[-1].index),
        "prz": {
            "price_low": float(prz.price_low),
            "price_high": float(prz.price_high),
            "width": float(prz.width),
        },
        "quality_at_signal": {
            **candidate["quality"],
            "close": close,
            "distance_to_prz": distance,
            "distance_to_prz_ratio": None if span <= 0 else distance / span,
        },
    }


def _finalize_signal(
    signal: dict[str, Any],
    *,
    frame: pd.DataFrame,
    completion: dict[str, Any] | None,
    retired_at: int | None,
    horizon: int,
) -> dict[str, Any]:
    signal_bar = int(signal["signal_bar"])
    terminal_bar = int(signal["terminal_pivot_bar"])
    prz_low = float(signal["prz"]["price_low"])
    prz_high = float(signal["prz"]["price_high"])

    pre_signal_touch = _first_touch(
        frame,
        start=terminal_bar + 1,
        end=signal_bar,
        low=prz_low,
        high=prz_high,
    )
    future_touch = _first_touch(
        frame,
        start=signal_bar + 1,
        end=len(frame) - 1,
        low=prz_low,
        high=prz_high,
    )
    bars_to_touch = None if future_touch is None else int(future_touch - signal_bar)
    retired_lead = None if retired_at is None else int(retired_at - signal_bar)
    available_future = max(0, len(frame) - 1 - signal_bar)

    completion_confirmed_at = None
    completion_terminal_bar = None
    bars_to_completion_confirmation = None
    bars_to_completion_terminal = None
    if completion is not None:
        completion_confirmed_at = int(completion["confirmed_at"])
        completion_terminal_bar = int(completion["terminal_bar"])
        bars_to_completion_confirmation = completion_confirmed_at - signal_bar
        bars_to_completion_terminal = completion_terminal_bar - signal_bar

    touch_before_retirement = bool(
        bars_to_touch is not None
        and (retired_at is None or int(future_touch) <= int(retired_at))
    )
    completion_before_retirement = bool(
        completion_confirmed_at is not None
        and (retired_at is None or completion_confirmed_at <= int(retired_at))
    )

    if pre_signal_touch is not None:
        outcome_class = "late_signal_prz_already_touched"
    elif (
        completion_before_retirement
        and bars_to_completion_confirmation is not None
        and 0 <= bars_to_completion_confirmation <= horizon
    ):
        outcome_class = "engine_completed_within_horizon"
    elif touch_before_retirement and bars_to_touch is not None and bars_to_touch <= horizon:
        outcome_class = "prz_touched_within_horizon"
    elif retired_lead is not None and 0 <= retired_lead <= horizon:
        outcome_class = "frontier_retired_before_touch"
    elif available_future < horizon:
        outcome_class = "immature"
    else:
        outcome_class = "no_prz_touch_within_horizon"

    return {
        **signal,
        "outcome": {
            "observation_horizon_bars": int(horizon),
            "available_future_bars": int(available_future),
            "pre_signal_prz_touch_bar": pre_signal_touch,
            "first_future_prz_touch_bar": future_touch,
            "bars_to_first_future_prz_touch": bars_to_touch,
            "touch_before_retirement": touch_before_retirement,
            "frontier_retired_at_bar": retired_at,
            "bars_to_frontier_retirement": retired_lead,
            "completion_terminal_bar": completion_terminal_bar,
            "completion_confirmed_at_bar": completion_confirmed_at,
            "bars_to_completion_terminal": bars_to_completion_terminal,
            "bars_to_completion_confirmation": bars_to_completion_confirmation,
            "completion_before_retirement": completion_before_retirement,
            "outcome_class": outcome_class,
        },
        "anti_leakage": {
            "signal_uses_only_confirmed_pivots": True,
            "future_outcome_changes_signal": False,
            "later_scale_support_changes_first_signal": False,
            "full_history_used_only_to_precompute_confirmation_events": True,
        },
    }


def walk_forward_forming_signals(
    frame: pd.DataFrame,
    *,
    scales: tuple[int, ...] = DEFAULT_WALK_FORWARD_SCALES,
    horizon: int = DEFAULT_FORWARD_HORIZON,
) -> list[dict[str, Any]]:
    """Replay forming harmonic projections using only information known at each event time.

    The replay is event-driven rather than bar-by-bar: the harmonic frontier can only change
    when a new pivot becomes confirmed. Raw local-extreme events are precomputed for speed, but
    an event is not exposed to the replay before its own ``confirmed_at`` bar. This preserves
    live information boundaries while avoiding an O(N^2) full-history rescan on every bar.
    """

    required = {"trade_date", "high", "low", "close"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"walk-forward frame missing columns: {sorted(missing)}")
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    normalized_scales = tuple(sorted({int(scale) for scale in scales}))
    if not normalized_scales or any(scale < 1 for scale in normalized_scales):
        raise ValueError("scales must contain positive integers")
    if frame.empty:
        return []

    source = frame.sort_values("trade_date").reset_index(drop=True).copy()
    dates = pd.to_datetime(source["trade_date"])
    events_by_cutoff: dict[int, list[tuple[int, Pivot]]] = defaultdict(list)
    for scale in normalized_scales:
        for event in detect_pivot_events(source, left=scale, right=scale, scale=scale):
            events_by_cutoff[int(event.confirmed_at)].append((scale, event))

    raw_visible: dict[int, list[Pivot]] = {scale: [] for scale in normalized_scales}
    swing_visible: dict[int, list[Pivot]] = {scale: [] for scale in normalized_scales}
    active_by_scale: dict[int, set[tuple[Any, ...]]] = {scale: set() for scale in normalized_scales}
    seen_signals: dict[tuple[Any, ...], dict[str, Any]] = {}
    retirement: dict[tuple[Any, ...], int] = {}
    completions: dict[tuple[Any, ...], dict[str, Any]] = {}
    previous_active: set[tuple[Any, ...]] = set()

    for cutoff in sorted(events_by_cutoff):
        changed_scales: set[int] = set()
        for scale, event in events_by_cutoff[cutoff]:
            raw_visible[scale].append(event)
            changed_scales.add(scale)

        candidates_this_cutoff: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
        for scale in changed_scales:
            swing_visible[scale] = collapse_same_kind_pivots(raw_visible[scale])
            frontier = _frontier_candidates(scale, swing_visible[scale])
            active_by_scale[scale] = {_projection_key(candidate) for candidate in frontier}
            for candidate in frontier:
                candidates_this_cutoff[_projection_key(candidate)].append(candidate)

            for completed in _completed_candidates(scale, swing_visible[scale]):
                key = _completed_prefix_key(completed)
                current = completions.get(key)
                terminal_bar = int(completed["points"][-1].index)
                row = {
                    "confirmed_at": int(cutoff),
                    "terminal_bar": terminal_bar,
                    "scale": int(scale),
                }
                if current is None or int(cutoff) < int(current["confirmed_at"]):
                    completions[key] = row

        current_active = set().union(*active_by_scale.values()) if active_by_scale else set()
        for key in previous_active.difference(current_active):
            if key in seen_signals and key not in retirement:
                completion = completions.get(key)
                if completion is None or int(completion["confirmed_at"]) > int(cutoff):
                    retirement[key] = int(cutoff)

        for key, candidates in candidates_this_cutoff.items():
            if key in seen_signals:
                continue
            representative = max(candidates, key=_candidate_rank)
            signal_scales = [int(candidate["scale"]) for candidate in candidates]
            seen_signals[key] = _serialize_signal(
                representative,
                signal_bar=int(cutoff),
                signal_scales=signal_scales,
                dates=dates,
                frame=source,
            )
        previous_active = current_active

    records: list[dict[str, Any]] = []
    for key, signal in seen_signals.items():
        records.append(
            _finalize_signal(
                signal,
                frame=source,
                completion=completions.get(key),
                retired_at=retirement.get(key),
                horizon=horizon,
            )
        )

    records.sort(
        key=lambda row: (
            int(row["signal_bar"]),
            str(row["pattern_id"]),
            str(row["schema"]),
            tuple(point["index"] for point in row["prefix_points"]),
        )
    )
    return records
