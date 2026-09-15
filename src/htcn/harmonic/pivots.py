from __future__ import annotations

from collections.abc import Iterable, Mapping

import pandas as pd

from .models import Pivot, PivotKind


REQUIRED_COLUMNS = {"high", "low"}


def _validate_frame(frame: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"missing pivot columns: {sorted(missing)}")
    if len(frame) == 0:
        return
    if frame[["high", "low"]].isnull().any().any():
        raise ValueError("pivot source contains null high/low values")
    if (frame["high"] < frame["low"]).any():
        raise ValueError("pivot source contains high < low")


def detect_confirmed_pivots(
    frame: pd.DataFrame,
    *,
    left: int = 3,
    right: int = 3,
    scale: int | None = None,
) -> list[Pivot]:
    """Detect non-repainting local pivots confirmed after `right` bars.

    A pivot high must equal the maximum high inside its full left/right window; a pivot low
    uses the equivalent minimum-low rule. Ties are resolved conservatively: if the same
    extreme appears more than once in the window, no pivot is emitted for that center bar.
    This prevents duplicate nodes on flat tops/bottoms.
    """
    if left < 1 or right < 1:
        raise ValueError("left and right must be >= 1")
    _validate_frame(frame)
    if len(frame) < left + right + 1:
        return []

    pivot_scale = scale if scale is not None else max(left, right)
    if pivot_scale < 1:
        raise ValueError("scale must be >= 1")

    highs = pd.to_numeric(frame["high"], errors="raise").to_numpy(dtype=float)
    lows = pd.to_numeric(frame["low"], errors="raise").to_numpy(dtype=float)
    pivots: list[Pivot] = []

    for center in range(left, len(frame) - right):
        lo = center - left
        hi = center + right + 1
        high_window = highs[lo:hi]
        low_window = lows[lo:hi]

        center_high = highs[center]
        if center_high == high_window.max() and (high_window == center_high).sum() == 1:
            pivots.append(
                Pivot(
                    index=center,
                    price=float(center_high),
                    kind=PivotKind.HIGH,
                    scale=pivot_scale,
                    confirmed_at=center + right,
                )
            )

        center_low = lows[center]
        if center_low == low_window.min() and (low_window == center_low).sum() == 1:
            pivots.append(
                Pivot(
                    index=center,
                    price=float(center_low),
                    kind=PivotKind.LOW,
                    scale=pivot_scale,
                    confirmed_at=center + right,
                )
            )

    return collapse_same_kind_pivots(pivots)


def collapse_same_kind_pivots(pivots: Iterable[Pivot]) -> list[Pivot]:
    """Return an alternating swing sequence, retaining the more extreme same-kind node."""
    ordered = sorted(pivots, key=lambda p: (p.index, p.kind.value))
    out: list[Pivot] = []
    for pivot in ordered:
        if not out:
            out.append(pivot)
            continue

        previous = out[-1]
        if pivot.index == previous.index:
            # A single bar can theoretically be both a local high and low in pathological data.
            # Keep neither ambiguity implicit; skip the second semantic interpretation.
            continue

        if pivot.kind != previous.kind:
            out.append(pivot)
            continue

        more_extreme = (
            pivot.price > previous.price
            if pivot.kind == PivotKind.HIGH
            else pivot.price < previous.price
        )
        if more_extreme:
            out[-1] = pivot
    return out


def detect_multi_scale_pivots(
    frame: pd.DataFrame,
    *,
    scales: Iterable[int] = (2, 3, 5, 8),
) -> dict[int, list[Pivot]]:
    """Build independent confirmed swing sequences for multiple scales."""
    result: dict[int, list[Pivot]] = {}
    for scale in sorted(set(int(value) for value in scales)):
        if scale < 1:
            raise ValueError("all scales must be >= 1")
        result[scale] = detect_confirmed_pivots(
            frame,
            left=scale,
            right=scale,
            scale=scale,
        )
    return result


def build_pivot_consensus(
    pivots_by_scale: Mapping[int, Iterable[Pivot]],
) -> dict[tuple[int, PivotKind], tuple[int, ...]]:
    """Return exact-node support across independent pivot scales.

    This is a diagnostic, not a pattern rule.  A swing extreme that is independently
    rediscovered at S3/S5/S8 is more structurally persistent than one that only exists at
    S3, but HT-CN deliberately does not use this fact to mutate Carney identity.  Exact
    index+kind matching avoids adding another arbitrary price/time tolerance during the
    calibration phase.
    """

    groups: dict[tuple[int, PivotKind], set[int]] = {}
    for scale, pivots in pivots_by_scale.items():
        for pivot in pivots:
            key = (int(pivot.index), pivot.kind)
            groups.setdefault(key, set()).add(int(scale))
    return {key: tuple(sorted(scales)) for key, scales in groups.items()}
