from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import pandas as pd

from .indicators import wilder_rsi
from .models import HarmonicPoint, PatternDirection
from .prz import PotentialReversalZone


@dataclass(frozen=True, slots=True)
class ReactionAudit:
    """Deterministic retrospective post-completion price/confirmation audit.

    Pattern identity is frozen before this module runs. This audit cannot create, delete,
    or mutate harmonic geometry.

    Source-fidelity boundaries:
    - a secondary overlap is only a retest observation;
    - a Type-II candidate requires an explicitly frozen source PRZ and a full retest of
      its terminal side;
    - that full retest is recorded as the retrospective Type-II Terminal Price Bar;
    - PRICE and indicator evidence are assessed only after that full retest;
    - the Wilder RSI evidence here is a lightweight confirmation layer, NOT RSI BAMM.

    The source-aligned no-lookahead execution clock remains the Terminal Price Bar pipeline
    in ``htcn.research.terminal_bar``. This completed-pattern audit is retrospective and must
    not be presented as proof that the D Pivot was observable in real time.
    """

    d_index: int
    bars_observed: int
    target_382: float
    target_618: float
    bars_to_382: int | None
    bars_to_618: int | None
    first_prz_exit_bar: int | None
    secondary_prz_retest_bar: int | None
    source_prz_available: bool
    full_prz_retest_bar: int | None
    type_ii_terminal_bar: int | None
    reversal_exit_after_retest_bar: int | None
    bars_to_reversal_exit_after_retest: int | None
    third_prz_test_bar: int | None
    no_prz_retest_first_3_bars: bool | None
    no_prz_retest_first_5_bars: bool | None
    max_favorable_price: float | None
    max_favorable_retracement: float | None
    type_ii_candidate: bool
    rsi_period: int
    rsi_at_d: float | None
    rsi_extreme_bar: int | None
    rsi_extreme_value: float | None
    rsi_trigger_bar: int | None
    rsi_trigger_value: float | None
    rsi_confirmation: bool
    indicator_evidence_kind: str
    indicator_evidence_is_rsi_bamm: bool
    type_ii_evidence_state: str

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


def _target_prices(
    *,
    a_price: float,
    d_price: float,
    direction: PatternDirection,
) -> tuple[float, float]:
    span = abs(a_price - d_price)
    if span <= 0:
        raise ValueError("A and D must define a positive reaction span")
    sign = 1.0 if direction is PatternDirection.BULLISH else -1.0
    return (
        d_price + sign * 0.382 * span,
        d_price + sign * 0.618 * span,
    )


def _observation_bounds(prz: PotentialReversalZone) -> tuple[float, float]:
    """Bounds used only to notice a secondary re-entry.

    When source PRZ bounds are frozen they take precedence. Otherwise we retain the legacy
    ideal-core overlap solely as a descriptive observation; it can never promote Type-II.
    """
    if prz.has_source_prz:
        assert prz.source_prz_low is not None and prz.source_prz_high is not None
        return float(prz.source_prz_low), float(prz.source_prz_high)
    return float(prz.ideal_core_low), float(prz.ideal_core_high)


def _bar_overlaps_prz(low: float, high: float, prz: PotentialReversalZone) -> bool:
    zone_low, zone_high = _observation_bounds(prz)
    return high >= zone_low and low <= zone_high


def _tests_full_source_prz(
    low: float,
    high: float,
    direction: PatternDirection,
    prz: PotentialReversalZone,
) -> bool:
    """Whether a retest reaches the far/terminal side of an explicit source PRZ.

    Missing source bounds deliberately fail closed. Neither the ideal core nor the broad
    component envelope is allowed to substitute for a source-frozen Raw PRZ.
    """
    if not prz.has_source_prz:
        return False
    assert prz.source_prz_low is not None and prz.source_prz_high is not None
    if direction is PatternDirection.BULLISH:
        return low <= float(prz.source_prz_low)
    return high >= float(prz.source_prz_high)


def _exited_in_reversal_direction(
    low: float,
    high: float,
    direction: PatternDirection,
    prz: PotentialReversalZone,
) -> bool:
    zone_low, zone_high = _observation_bounds(prz)
    if direction is PatternDirection.BULLISH:
        return low > zone_high
    return high < zone_low


def _finite_or_none(value: float) -> float | None:
    return float(value) if math.isfinite(float(value)) else None


def _rsi_confirmation_evidence(
    frame: pd.DataFrame,
    *,
    d_index: int,
    type_ii_terminal_bar: int | None,
    direction: PatternDirection,
    period: int,
) -> tuple[float | None, int | None, float | None, int | None, float | None, bool]:
    """Audit a simple Wilder RSI 30/70 reversal around the Type-II full retest.

    This is deliberately NOT an RSI BAMM implementation. Volume Two RSI BAMM requires a
    multi-step complex RSI structure, trigger bar, reaction, divergence, 1.13/1.618
    confirmation and coordinated pattern completion. The lightweight evidence below only
    records an extreme-zone reading and subsequent exit from that zone.
    """

    if "close" not in frame.columns:
        return None, None, None, None, None, False

    rsi = wilder_rsi(frame["close"], period=period)
    rsi_at_d = _finite_or_none(float(rsi.iloc[d_index])) if 0 <= d_index < len(rsi) else None
    if type_ii_terminal_bar is None:
        return rsi_at_d, None, None, None, None, False

    retest_index = d_index + type_ii_terminal_bar
    if retest_index >= len(rsi):
        return rsi_at_d, None, None, None, None, False

    extreme_positions: list[int] = []
    for absolute in range(d_index, retest_index + 1):
        value = float(rsi.iloc[absolute])
        if not math.isfinite(value):
            continue
        if direction is PatternDirection.BULLISH and value <= 30.0 or direction is PatternDirection.BEARISH and value >= 70.0:
            extreme_positions.append(absolute)

    if not extreme_positions:
        return rsi_at_d, None, None, None, None, False

    extreme_index = extreme_positions[-1]
    extreme_value = float(rsi.iloc[extreme_index])
    trigger_index: int | None = None
    trigger_value: float | None = None
    for absolute in range(extreme_index + 1, len(rsi)):
        value = float(rsi.iloc[absolute])
        if not math.isfinite(value):
            continue
        if direction is PatternDirection.BULLISH and value > 30.0:
            trigger_index = absolute
            trigger_value = value
            break
        if direction is PatternDirection.BEARISH and value < 70.0:
            trigger_index = absolute
            trigger_value = value
            break

    return (
        rsi_at_d,
        extreme_index - d_index,
        extreme_value,
        None if trigger_index is None else trigger_index - d_index,
        trigger_value,
        trigger_index is not None,
    )


def _reaction_anchors(
    points: tuple[HarmonicPoint, ...],
) -> tuple[HarmonicPoint, HarmonicPoint]:
    labels = tuple(point.label for point in points)
    if labels == ("X", "A", "B", "C", "D"):
        return points[1], points[4]
    if labels == ("A", "B", "C", "D"):
        return points[0], points[3]
    raise ValueError("reaction audit requires X/A/B/C/D or A/B/C/D points")


def audit_completed_reaction(
    frame: pd.DataFrame,
    *,
    points: tuple[HarmonicPoint, ...],
    direction: PatternDirection,
    prz: PotentialReversalZone,
    rsi_period: int = 14,
) -> ReactionAudit:
    """Retrospectively audit the path after a completed D point.

    This function intentionally does not claim source-aligned real-time observability.
    ``frame`` must be the same indexed price window used to identify the pattern. Only bars
    strictly after D are examined for outcomes. Targets are measured from D back toward A
    using the 38.2% and 61.8% reaction objectives. Source-aligned live execution timing is
    owned by the no-lookahead Terminal Price Bar pipeline.
    """

    required = {"high", "low"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"reaction audit missing columns: {sorted(missing)}")
    if rsi_period < 2:
        raise ValueError("rsi_period must be >= 2")

    a, d = _reaction_anchors(points)
    if d.index < 0 or d.index >= len(frame):
        raise ValueError("D index is outside the supplied frame")

    target_382, target_618 = _target_prices(
        a_price=float(a.price),
        d_price=float(d.price),
        direction=direction,
    )
    future = frame.iloc[d.index + 1 :].copy()
    bars_observed = len(future)

    bars_to_382: int | None = None
    bars_to_618: int | None = None
    first_exit: int | None = None
    secondary_retest: int | None = None
    full_retest: int | None = None
    reversal_exit_after_retest: int | None = None
    third_test: int | None = None
    exited_after_secondary = False
    max_favorable_price: float | None = None

    for offset, (_, row) in enumerate(future.iterrows(), start=1):
        high = float(row["high"])
        low = float(row["low"])

        if direction is PatternDirection.BULLISH:
            if bars_to_382 is None and high >= target_382:
                bars_to_382 = offset
            if bars_to_618 is None and high >= target_618:
                bars_to_618 = offset
            max_favorable_price = high if max_favorable_price is None else max(max_favorable_price, high)
        else:
            if bars_to_382 is None and low <= target_382:
                bars_to_382 = offset
            if bars_to_618 is None and low <= target_618:
                bars_to_618 = offset
            max_favorable_price = low if max_favorable_price is None else min(max_favorable_price, low)

        overlap = _bar_overlaps_prz(low, high, prz)
        reversal_exit = _exited_in_reversal_direction(low, high, direction, prz)

        if first_exit is None and reversal_exit:
            first_exit = offset
            continue

        if first_exit is not None and secondary_retest is None and overlap:
            secondary_retest = offset
            if _tests_full_source_prz(low, high, direction, prz):
                full_retest = offset
            continue

        if secondary_retest is not None:
            if full_retest is None and overlap and _tests_full_source_prz(low, high, direction, prz):
                full_retest = offset
                continue

            if full_retest is not None and not exited_after_secondary and reversal_exit:
                exited_after_secondary = True
                reversal_exit_after_retest = offset
                continue
            if full_retest is not None and exited_after_secondary and third_test is None and overlap:
                third_test = offset

    def no_retest_within(limit: int) -> bool | None:
        if bars_observed < limit:
            return None
        sample = future.iloc[:limit]
        return not any(
            _bar_overlaps_prz(float(row["low"]), float(row["high"]), prz)
            for _, row in sample.iterrows()
        )

    reaction_span = abs(float(a.price) - float(d.price))
    if max_favorable_price is None:
        max_favorable_retracement = None
    elif direction is PatternDirection.BULLISH:
        max_favorable_retracement = max(0.0, (max_favorable_price - float(d.price)) / reaction_span)
    else:
        max_favorable_retracement = max(0.0, (float(d.price) - max_favorable_price) / reaction_span)

    (
        rsi_at_d,
        rsi_extreme_bar,
        rsi_extreme_value,
        rsi_trigger_bar,
        rsi_trigger_value,
        rsi_confirmation,
    ) = _rsi_confirmation_evidence(
        frame,
        d_index=int(d.index),
        type_ii_terminal_bar=full_retest,
        direction=direction,
        period=rsi_period,
    )

    type_ii_candidate = bool(first_exit is not None and prz.has_source_prz and full_retest is not None)
    if secondary_retest is None:
        evidence_state = "not_candidate"
    elif not prz.has_source_prz:
        evidence_state = "source_prz_unresolved"
    elif full_retest is None:
        evidence_state = "partial_retest_only"
    elif reversal_exit_after_retest is None:
        evidence_state = "full_retest_waiting_price"
    elif rsi_confirmation:
        evidence_state = "price_and_rsi_confirmed"
    else:
        evidence_state = "price_confirmed_no_rsi"

    bars_to_reversal_exit_after_retest = (
        None
        if full_retest is None or reversal_exit_after_retest is None
        else reversal_exit_after_retest - full_retest
    )

    return ReactionAudit(
        d_index=int(d.index),
        bars_observed=bars_observed,
        target_382=float(target_382),
        target_618=float(target_618),
        bars_to_382=bars_to_382,
        bars_to_618=bars_to_618,
        first_prz_exit_bar=first_exit,
        secondary_prz_retest_bar=secondary_retest,
        source_prz_available=prz.has_source_prz,
        full_prz_retest_bar=full_retest,
        type_ii_terminal_bar=full_retest,
        reversal_exit_after_retest_bar=reversal_exit_after_retest,
        bars_to_reversal_exit_after_retest=bars_to_reversal_exit_after_retest,
        third_prz_test_bar=third_test,
        no_prz_retest_first_3_bars=no_retest_within(3),
        no_prz_retest_first_5_bars=no_retest_within(5),
        max_favorable_price=max_favorable_price,
        max_favorable_retracement=max_favorable_retracement,
        type_ii_candidate=type_ii_candidate,
        rsi_period=rsi_period,
        rsi_at_d=rsi_at_d,
        rsi_extreme_bar=rsi_extreme_bar,
        rsi_extreme_value=rsi_extreme_value,
        rsi_trigger_bar=rsi_trigger_bar,
        rsi_trigger_value=rsi_trigger_value,
        rsi_confirmation=rsi_confirmation,
        indicator_evidence_kind="wilder_rsi_extreme_reversal",
        indicator_evidence_is_rsi_bamm=False,
        type_ii_evidence_state=evidence_state,
    )