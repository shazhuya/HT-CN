from __future__ import annotations

from .models import RatioMeasurement

RECIPROCAL_ABCD: dict[float, tuple[float, ...]] = {
    0.382: (2.24, 2.618),
    0.500: (2.0,),
    0.618: (1.618,),
    0.707: (1.414,),
    0.786: (1.272,),
    0.886: (1.13,),
}


def leg_length(start: float, end: float) -> float:
    """Absolute price length of a leg."""
    return abs(float(end) - float(start))


def ratio_of_legs(
    *,
    name: str,
    numerator_start: float,
    numerator_end: float,
    denominator_start: float,
    denominator_end: float,
) -> RatioMeasurement:
    """Measure one leg length relative to another without pattern-specific semantics.

    M2 deliberately keeps this primitive neutral. Binding a leg pair to concepts such as
    `B/XA`, `BC projection`, or `AB=CD` belongs to a schema-specific evaluator, preventing
    hidden assumptions about how a particular Carney pattern defines a measurement.
    """
    numerator = leg_length(numerator_start, numerator_end)
    denominator = leg_length(denominator_start, denominator_end)
    if denominator == 0:
        raise ValueError("cannot measure ratio against a zero-length leg")
    return RatioMeasurement(
        name=name,
        numerator=numerator,
        denominator=denominator,
        value=numerator / denominator,
    )


def reciprocal_bc_targets(c_retracement: float, *, tolerance: float = 0.002) -> tuple[float, ...]:
    """Return Carney AB=CD reciprocal BC target(s) for a known C retracement.

    Matching is intentionally tight and explicit. Callers that want a wider real-time
    tolerance must make that policy visible rather than silently rounding arbitrary values.
    """
    value = float(c_retracement)
    for retracement, targets in RECIPROCAL_ABCD.items():
        if abs(value - retracement) <= tolerance:
            return targets
    return ()
