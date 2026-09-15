from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from .models import HarmonicPoint, PatternDirection
from .prz import PotentialReversalZone


@dataclass(frozen=True, slots=True)
class ReactionAudit:
    """Deterministic post-completion price-path audit.

    This module deliberately does not turn the observed path into a trade recommendation.
    It records the source-backed Type-I minimum objectives (38.2% / 61.8%), whether price
    exited and later retested the original PRZ, and the timing of those events.

    A secondary PRZ retest is only labelled a *Type-II candidate*. Volume Three requires
    additional price/indicator confirmation for a valid Type-II reversal; this audit does
    not invent that confirmation.
    """

    d_index: int
    bars_observed: int
    target_382: float
    target_618: float
    bars_to_382: int | None
    bars_to_618: int | None
    first_prz_exit_bar: int | None
    secondary_prz_retest_bar: int | None
    no_prz_retest_first_3_bars: bool | None
    no_prz_retest_first_5_bars: bool | None
    max_favorable_price: float | None
    max_favorable_retracement: float | None
    type_ii_candidate: bool

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


def _bar_overlaps_prz(low: float, high: float, prz: PotentialReversalZone) -> bool:
    return high >= prz.price_low and low <= prz.price_high


def _exited_in_reversal_direction(
    low: float,
    high: float,
    direction: PatternDirection,
    prz: PotentialReversalZone,
) -> bool:
    if direction is PatternDirection.BULLISH:
        return low > prz.price_high
    return high < prz.price_low


def audit_completed_reaction(
    frame: pd.DataFrame,
    *,
    points: tuple[HarmonicPoint, ...],
    direction: PatternDirection,
    prz: PotentialReversalZone,
) -> ReactionAudit:
    """Audit the observable path after D without future-data leakage into identity.

    ``frame`` must be the same indexed price window used to identify the pattern. Only bars
    strictly after D are examined. Targets are measured from D back toward A using the
    38.2% and 61.8% reaction objectives described in Harmonic Trading Volume Three.
    """

    if tuple(point.label for point in points) != ("X", "A", "B", "C", "D"):
        raise ValueError("reaction audit requires X/A/B/C/D points")
    required = {"high", "low"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"reaction audit missing columns: {sorted(missing)}")

    a = points[1]
    d = points[4]
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

        if first_exit is None and _exited_in_reversal_direction(low, high, direction, prz):
            first_exit = offset
        elif first_exit is not None and secondary_retest is None and _bar_overlaps_prz(low, high, prz):
            secondary_retest = offset

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

    return ReactionAudit(
        d_index=int(d.index),
        bars_observed=bars_observed,
        target_382=float(target_382),
        target_618=float(target_618),
        bars_to_382=bars_to_382,
        bars_to_618=bars_to_618,
        first_prz_exit_bar=first_exit,
        secondary_prz_retest_bar=secondary_retest,
        no_prz_retest_first_3_bars=no_retest_within(3),
        no_prz_retest_first_5_bars=no_retest_within(5),
        max_favorable_price=max_favorable_price,
        max_favorable_retracement=max_favorable_retracement,
        type_ii_candidate=bool(first_exit is not None and secondary_retest is not None),
    )
