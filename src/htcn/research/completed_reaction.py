from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

import pandas as pd

from htcn.harmonic.abcd import ABCDMatch
from htcn.harmonic.engine import CompletedMatch, HarmonicScan, scan_frame
from htcn.harmonic.five_zero import FiveZeroMatch
from htcn.harmonic.models import HarmonicPoint, PatternDirection, Pivot
from htcn.harmonic.shark import SharkMatch

from .quality_layers import pattern_family


DEFAULT_COMPLETED_REACTION_HORIZON = 20
DEFAULT_COMPLETED_REACTION_SCALES = (3, 5, 8, 13, 21)


def _trade_date(frame: pd.DataFrame, index: int) -> str:
    return pd.Timestamp(frame.iloc[index]["trade_date"]).date().isoformat()


def _point_payload(frame: pd.DataFrame, point: HarmonicPoint) -> dict[str, Any]:
    return {
        "label": point.label,
        "index": int(point.index),
        "price": float(point.price),
        "trade_date": _trade_date(frame, int(point.index)),
    }


def _terminal_pivot(scan: HarmonicScan, *, scale: int, terminal_index: int) -> Pivot:
    for pivot in scan.pivots_by_scale.get(int(scale), ()):
        if int(pivot.index) == int(terminal_index):
            return pivot
    raise ValueError(f"terminal pivot not found for scale={scale}, index={terminal_index}")


def _reference_span(schema: str, points: tuple[HarmonicPoint, ...]) -> tuple[str, float]:
    by_label = {point.label: point for point in points}
    if schema == "ABCD":
        left, right, label = "A", "B", "AB"
    elif schema == "0XABC":
        left, right, label = "0", "B", "0B"
    elif schema == "FIVE_ZERO":
        left, right, label = "B", "C", "BC"
    else:
        left, right, label = "X", "A", "XA"
    if left not in by_label or right not in by_label:
        return label, 0.0
    return label, abs(float(by_label[right].price) - float(by_label[left].price))


def _standard_targets(
    points: tuple[HarmonicPoint, ...], direction: PatternDirection
) -> tuple[str, float, str, float]:
    by_label = {point.label: point for point in points}
    a = by_label.get("A")
    d = by_label.get("D")
    if a is None or d is None:
        raise ValueError("standard completed reaction requires A and D")
    span = abs(float(a.price) - float(d.price))
    if span <= 0:
        raise ValueError("A/D reaction span must be positive")
    sign = 1.0 if direction is PatternDirection.BULLISH else -1.0
    return (
        "38.2%",
        float(d.price) + sign * 0.382 * span,
        "61.8%",
        float(d.price) + sign * 0.618 * span,
    )


def _target_hit(row: pd.Series, *, target: float, direction: PatternDirection) -> bool:
    if direction is PatternDirection.BULLISH:
        return float(row["high"]) >= target
    return float(row["low"]) <= target


def _first_target_hit(
    frame: pd.DataFrame,
    *,
    start_bar: int,
    target: float,
    direction: PatternDirection,
    stop_bar: int | None = None,
) -> int | None:
    end = len(frame) - 1 if stop_bar is None else min(int(stop_bar), len(frame) - 1)
    for absolute in range(int(start_bar) + 1, end + 1):
        if _target_hit(frame.iloc[absolute], target=target, direction=direction):
            return absolute - int(start_bar)
    return None


def audit_confirmed_reaction(
    frame: pd.DataFrame,
    *,
    d_index: int,
    confirmation_bar: int,
    direction: PatternDirection,
    t1_name: str,
    t1_price: float,
    t2_name: str,
    t2_price: float,
    horizon: int = DEFAULT_COMPLETED_REACTION_HORIZON,
) -> dict[str, Any]:
    """Measure reaction only after the completed structure becomes observable.

    D is a historical price pivot; ``confirmation_bar`` is the first bar at which that pivot
    is confirmed by the configured right-side window. Any target reached between D and pivot
    confirmation is explicitly marked as pre-confirmation/late and is never credited as an
    actionable post-signal reaction.
    """
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    if d_index < 0 or confirmation_bar < d_index or confirmation_bar >= len(frame):
        raise ValueError("invalid D/confirmation bars")

    pre_t1 = _first_target_hit(
        frame,
        start_bar=d_index,
        stop_bar=confirmation_bar,
        target=t1_price,
        direction=direction,
    )
    pre_t2 = _first_target_hit(
        frame,
        start_bar=d_index,
        stop_bar=confirmation_bar,
        target=t2_price,
        direction=direction,
    )
    post_t1 = _first_target_hit(
        frame,
        start_bar=confirmation_bar,
        target=t1_price,
        direction=direction,
    )
    post_t2 = _first_target_hit(
        frame,
        start_bar=confirmation_bar,
        target=t2_price,
        direction=direction,
    )
    available = len(frame) - 1 - int(confirmation_bar)
    late = pre_t1 is not None

    t1_within = post_t1 is not None and post_t1 <= horizon
    t2_within = post_t2 is not None and post_t2 <= horizon
    if available < horizon:
        outcome_class = "immature"
    elif late:
        outcome_class = "late_completion_signal"
    elif t2_within:
        outcome_class = "t2_within_horizon"
    elif t1_within:
        outcome_class = "t1_only_within_horizon"
    else:
        outcome_class = "no_t1_within_horizon"

    return {
        "observation_horizon_bars": int(horizon),
        "d_index": int(d_index),
        "confirmation_bar": int(confirmation_bar),
        "confirmation_lag_bars": int(confirmation_bar - d_index),
        "available_future_bars_after_confirmation": int(available),
        "t1_name": t1_name,
        "t1_price": float(t1_price),
        "t2_name": t2_name,
        "t2_price": float(t2_price),
        "pre_confirmation_t1_hit": pre_t1 is not None,
        "pre_confirmation_t2_hit": pre_t2 is not None,
        "bars_from_d_to_pre_confirmation_t1": pre_t1,
        "bars_from_d_to_pre_confirmation_t2": pre_t2,
        "late_completion_signal": late,
        "bars_from_confirmation_to_t1": post_t1,
        "bars_from_confirmation_to_t2": post_t2,
        "t1_within_horizon_after_confirmation": bool(t1_within),
        "t2_within_horizon_after_confirmation": bool(t2_within),
        "outcome_class": outcome_class,
    }


def _primary_xabcd(items: tuple[CompletedMatch, ...]) -> list[CompletedMatch]:
    groups: dict[tuple[int, ...], list[CompletedMatch]] = {}
    for item in items:
        groups.setdefault(item.conflict_key, []).append(item)
    out: list[CompletedMatch] = []
    for rows in groups.values():
        out.append(
            max(
                rows,
                key=lambda item: (float(item.geometry_score), item.pattern_id, int(item.scale)),
            )
        )
    return out


def _x_source_tolerance_used(item: CompletedMatch) -> bool:
    return any(check.passed and not check.canonical_passed for check in item.evaluation.checks)


def _record(
    frame: pd.DataFrame,
    scan: HarmonicScan,
    *,
    instrument_id: str,
    pattern_id: str,
    schema: str,
    scale: int,
    direction: PatternDirection,
    points: tuple[HarmonicPoint, ...],
    geometry_score: float,
    prz: Any,
    horizon: int,
    source_tolerance_used: bool | None,
    shark_targets: tuple[float, float] | None = None,
) -> dict[str, Any]:
    terminal = points[-1]
    pivot = _terminal_pivot(scan, scale=scale, terminal_index=int(terminal.index))
    if shark_targets is None:
        t1_name, t1_price, t2_name, t2_price = _standard_targets(points, direction)
    else:
        t1_name, t2_name = "50%", "61.8%"
        t1_price, t2_price = shark_targets

    outcome = audit_confirmed_reaction(
        frame,
        d_index=int(terminal.index),
        confirmation_bar=int(pivot.confirmed_at),
        direction=direction,
        t1_name=t1_name,
        t1_price=float(t1_price),
        t2_name=t2_name,
        t2_price=float(t2_price),
        horizon=horizon,
    )
    span_name, span = _reference_span(schema, points)
    width = float(prz.width)
    return {
        "instrument_id": instrument_id,
        "pattern_id": pattern_id,
        "pattern_family": pattern_family(pattern_id),
        "schema": schema,
        "direction": direction.value,
        "source_scale": int(scale),
        "geometry_score": float(geometry_score),
        "source_tolerance_used": source_tolerance_used,
        "points": [_point_payload(frame, point) for point in points],
        "d_trade_date": _trade_date(frame, int(terminal.index)),
        "signal_bar": int(pivot.confirmed_at),
        "signal_trade_date": _trade_date(frame, int(pivot.confirmed_at)),
        "quality_at_signal": {
            "reference_span_name": span_name,
            "reference_span": float(span),
            "prz_width": width,
            "prz_width_ratio": None if span <= 0 else width / span,
            "geometry_score": float(geometry_score),
            "source_tolerance_used": source_tolerance_used,
        },
        "outcome": outcome,
        "anti_leakage": {
            "signal_uses_terminal_pivot_confirmation": True,
            "pre_confirmation_reaction_credited": False,
            "outcome_changes_identity": False,
        },
    }


def confirmed_completed_reaction_records(
    frame: pd.DataFrame,
    *,
    instrument_id: str,
    scales: tuple[int, ...] = DEFAULT_COMPLETED_REACTION_SCALES,
    horizon: int = DEFAULT_COMPLETED_REACTION_HORIZON,
    max_completed: int = 10000,
) -> list[dict[str, Any]]:
    """Build historical completed-pattern records at their first observable confirmation bar."""
    source = frame.sort_values("trade_date").reset_index(drop=True)
    if source.empty:
        return []
    scan = scan_frame(
        source,
        scales=scales,
        max_completed=max_completed,
        max_forming=0,
    )
    rows: list[dict[str, Any]] = []

    for item in _primary_xabcd(scan.completed):
        rows.append(
            _record(
                source,
                scan,
                instrument_id=instrument_id,
                pattern_id=item.pattern_id,
                schema="XABCD",
                scale=item.scale,
                direction=item.direction,
                points=item.points,
                geometry_score=item.geometry_score,
                prz=item.evaluation.prz,
                horizon=horizon,
                source_tolerance_used=_x_source_tolerance_used(item),
            )
        )

    for item in scan.abcd_completed:
        assert isinstance(item, ABCDMatch)
        rows.append(
            _record(
                source,
                scan,
                instrument_id=instrument_id,
                pattern_id="abcd",
                schema="ABCD",
                scale=item.scale,
                direction=item.direction,
                points=item.points,
                geometry_score=item.geometry_score,
                prz=item.evaluation.prz,
                horizon=horizon,
                source_tolerance_used=None,
            )
        )

    for item in scan.shark_completed:
        assert isinstance(item, SharkMatch)
        rows.append(
            _record(
                source,
                scan,
                instrument_id=instrument_id,
                pattern_id="shark",
                schema="0XABC",
                scale=item.scale,
                direction=item.direction,
                points=item.points,
                geometry_score=item.geometry_score,
                prz=item.evaluation.prz,
                horizon=horizon,
                source_tolerance_used=None,
                shark_targets=(item.evaluation.target_50, item.evaluation.target_618),
            )
        )

    for item in scan.five_zero_completed:
        assert isinstance(item, FiveZeroMatch)
        rows.append(
            _record(
                source,
                scan,
                instrument_id=instrument_id,
                pattern_id="five_zero",
                schema="FIVE_ZERO",
                scale=item.scale,
                direction=item.direction,
                points=item.points,
                geometry_score=item.geometry_score,
                prz=item.evaluation.prz,
                horizon=horizon,
                source_tolerance_used=None,
            )
        )

    rows.sort(
        key=lambda row: (
            row["signal_trade_date"],
            row["instrument_id"],
            row["pattern_id"],
            row["source_scale"],
        )
    )
    return rows


def completed_reaction_summary(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(records)
    classes = Counter(row["outcome"]["outcome_class"] for row in rows)
    mature_actionable = [
        row
        for row in rows
        if row["outcome"]["outcome_class"]
        in {"t2_within_horizon", "t1_only_within_horizon", "no_t1_within_horizon"}
    ]
    t1 = sum(
        row["outcome"]["outcome_class"] in {"t2_within_horizon", "t1_only_within_horizon"}
        for row in mature_actionable
    )
    t2 = sum(row["outcome"]["outcome_class"] == "t2_within_horizon" for row in mature_actionable)
    return {
        "records": len(rows),
        "mature_actionable_records": len(mature_actionable),
        "late_completion_signals": int(classes.get("late_completion_signal", 0)),
        "immature_records": int(classes.get("immature", 0)),
        "t1_within_horizon": int(t1),
        "t2_within_horizon": int(t2),
        "t1_rate_actionable": None if not mature_actionable else t1 / len(mature_actionable),
        "t2_rate_actionable": None if not mature_actionable else t2 / len(mature_actionable),
        "by_outcome": dict(sorted(classes.items())),
        "by_pattern": dict(sorted(Counter(row["pattern_id"] for row in rows).items())),
        "by_family": dict(sorted(Counter(row["pattern_family"] for row in rows).items())),
        "methodology": {
            "reaction_clock": "Starts only after terminal pivot confirmation, never at historical D itself.",
            "late_signal": "If T1 was already reached between D and confirmation, the case is late and excluded from actionable reaction rates.",
            "identity": "Completed identity is determined by the harmonic core before outcome measurement.",
        },
    }
