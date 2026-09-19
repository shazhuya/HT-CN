from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass

from .models import HarmonicPoint, Pivot


@dataclass(frozen=True, slots=True)
class SwingWindow:
    """A semantic candidate window cut from one confirmed swing sequence.

    The window knows nothing about Gartley/Bat/etc.  This isolation prevents the
    pivot detector from being tuned to whichever pattern the classifier currently
    wants to see.
    """

    scale: int
    pivots: tuple[Pivot, ...]

    def __post_init__(self) -> None:
        if len(self.pivots) not in (4, 5):
            raise ValueError("swing window must contain 4 or 5 pivots")
        if any(p.scale != self.scale for p in self.pivots):
            raise ValueError("all pivots in a window must share the same scale")
        if any(left.index >= right.index for left, right in zip(self.pivots, self.pivots[1:])):
            raise ValueError("pivot indices must be strictly increasing")
        if any(left.kind == right.kind for left, right in zip(self.pivots, self.pivots[1:])):
            raise ValueError("pivot kinds must alternate")

    @property
    def is_completed(self) -> bool:
        return len(self.pivots) == 5

    def harmonic_points(self) -> tuple[HarmonicPoint, ...]:
        labels = ("X", "A", "B", "C", "D") if self.is_completed else ("X", "A", "B", "C")
        return tuple(
            HarmonicPoint(label=label, index=pivot.index, price=pivot.price)
            for label, pivot in zip(labels, self.pivots)
        )


def _validate_sequence(pivots: Sequence[Pivot]) -> None:
    if any(left.index >= right.index for left, right in zip(pivots, pivots[1:])):
        raise ValueError("pivot sequence must be ordered by index")
    scales = {pivot.scale for pivot in pivots}
    if len(scales) > 1:
        raise ValueError("candidate generation must operate on one scale at a time")


def iter_swing_windows(pivots: Sequence[Pivot], *, size: int) -> Iterator[SwingWindow]:
    """Iterate every historical semantic window of the requested size.

    This is intentionally the historical primitive. Completed XABCD recognition uses
    all 5-pivot windows so past completed structures remain auditable.
    """
    if size not in (4, 5):
        raise ValueError("size must be 4 or 5")
    _validate_sequence(pivots)
    if not pivots:
        return
    scale = pivots[0].scale
    for start in range(len(pivots) - size + 1):
        chunk = tuple(pivots[start : start + size])
        if any(left.kind == right.kind for left, right in zip(chunk, chunk[1:])):
            continue
        yield SwingWindow(scale=scale, pivots=chunk)


def iter_forming_xabc_windows(pivots: Sequence[Pivot]) -> Iterable[SwingWindow]:
    """Return only the current frontier XABC window for one scale.

    A historical four-pivot window stops being *forming* once a later confirmed pivot
    exists. The previous implementation returned every historical XABC slice, which made
    old projections survive forever and flooded a live chart with stale "forming" items.

    Historical XABC research is still available through ``iter_swing_windows(..., size=4)``;
    this function is deliberately live/frontier semantics only.
    """
    _validate_sequence(pivots)
    if len(pivots) < 4:
        return ()
    chunk = tuple(pivots[-4:])
    if any(left.kind == right.kind for left, right in zip(chunk, chunk[1:])):
        return ()
    return (SwingWindow(scale=chunk[0].scale, pivots=chunk),)


def iter_completed_xabcd_windows(pivots: Sequence[Pivot]) -> Iterable[SwingWindow]:
    return iter_swing_windows(pivots, size=5)
