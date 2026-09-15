from __future__ import annotations

from dataclasses import dataclass
from math import inf

from .models import HarmonicPoint, PatternDirection, PatternState, RatioMeasurement
from .prz import PotentialReversalZone, build_xabcd_prz
from .ratios import leg_length
from .rules import PatternRule


@dataclass(frozen=True, slots=True)
class ConstraintCheck:
    name: str
    value: float
    passed: bool
    canonical_passed: bool
    distance_to_canonical: float


@dataclass(frozen=True, slots=True)
class XABCDMetrics:
    b_xa: RatioMeasurement
    c_ab: RatioMeasurement
    bc_projection: RatioMeasurement
    d_xa: RatioMeasurement
    cd_ab: RatioMeasurement


@dataclass(frozen=True, slots=True)
class PatternEvaluation:
    pattern_id: str
    direction: PatternDirection
    state: PatternState
    metrics: XABCDMetrics
    checks: tuple[ConstraintCheck, ...]
    prz: PotentialReversalZone
    abcd_distance: float
    reasons: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.state is PatternState.COMPLETED


def _ratio(name: str, numerator: float, denominator: float) -> RatioMeasurement:
    if denominator <= 0:
        raise ValueError(f"{name}: denominator must be positive")
    value = numerator / denominator
    return RatioMeasurement(name=name, numerator=numerator, denominator=denominator, value=value)


def measure_xabcd(
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
) -> XABCDMetrics:
    x, a, b, c, d = points
    if tuple(point.label for point in points) != ("X", "A", "B", "C", "D"):
        raise ValueError("points must be labelled X, A, B, C, D")
    if not (x.index < a.index < b.index < c.index < d.index):
        raise ValueError("X/A/B/C/D indices must be strictly increasing")

    xa = leg_length(x, a)
    ab = leg_length(a, b)
    bc = leg_length(b, c)
    cd = leg_length(c, d)
    ad = abs(d.price - a.price)

    return XABCDMetrics(
        b_xa=_ratio("b_xa", ab, xa),
        c_ab=_ratio("c_ab", bc, ab),
        bc_projection=_ratio("bc_projection", cd, bc),
        d_xa=_ratio("d_xa", ad, xa),
        cd_ab=_ratio("cd_ab", cd, ab),
    )


def _infer_direction(x: HarmonicPoint, a: HarmonicPoint) -> PatternDirection:
    if a.price == x.price:
        raise ValueError("X and A cannot have the same price")
    return PatternDirection.BULLISH if a.price > x.price else PatternDirection.BEARISH


def _validate_turning_geometry(
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
    direction: PatternDirection,
) -> tuple[str, ...]:
    x, a, b, c, d = points
    reasons: list[str] = []
    if direction is PatternDirection.BULLISH:
        if not (a.price > x.price and b.price < a.price and c.price > b.price and d.price < c.price):
            reasons.append("bullish XABCD must alternate up/down/up/down from X to D")
    else:
        if not (a.price < x.price and b.price > a.price and c.price < b.price and d.price > c.price):
            reasons.append("bearish XABCD must alternate down/up/down/up from X to D")
    return tuple(reasons)


def _distance_to_band(value: float, minimum: float, maximum: float) -> float:
    if minimum <= value <= maximum:
        return 0.0
    return min(abs(value - minimum), abs(value - maximum))


def evaluate_xabcd(
    rule: PatternRule,
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
    *,
    include_source_tolerance: bool = True,
    abcd_relative_tolerance: float = 0.03,
) -> PatternEvaluation:
    """Evaluate one completed XABCD candidate against one Carney rule.

    `abcd_relative_tolerance` is an engine matching tolerance, not a Carney B-point
    tolerance.  It is deliberately an explicit argument so research can calibrate it
    without mutating the source rule registry.
    """

    if rule.schema != "XABCD":
        raise ValueError(f"rule {rule.pattern_id!r} is not XABCD")
    if not rule.executable_identity:
        raise ValueError(f"rule {rule.pattern_id!r} is not executable yet")
    if abcd_relative_tolerance < 0:
        raise ValueError("abcd_relative_tolerance must be non-negative")

    x, a, b, c, _ = points
    direction = _infer_direction(x, a)
    metrics = measure_xabcd(points)
    reasons = list(_validate_turning_geometry(points, direction))
    checks: list[ConstraintCheck] = []

    metric_by_name = {
        "b_xa": metrics.b_xa.value,
        "bc_projection": metrics.bc_projection.value,
        "d_xa": metrics.d_xa.value,
        "c_ab": metrics.c_ab.value,
    }

    for name, constraint in rule.constraints.items():
        if name not in metric_by_name:
            continue
        value = metric_by_name[name]
        canonical = constraint.contains(value, include_tolerance=False)
        passed = constraint.contains(value, include_tolerance=include_source_tolerance)
        checks.append(
            ConstraintCheck(
                name=name,
                value=value,
                passed=passed,
                canonical_passed=canonical,
                distance_to_canonical=_distance_to_band(value, constraint.minimum, constraint.maximum),
            )
        )
        if not passed:
            reasons.append(
                f"{name}={value:.6f} outside allowed {constraint.minimum:g}-{constraint.maximum:g}"
            )

    if rule.abcd_types:
        abcd_distance = min(abs(metrics.cd_ab.value - target) / target for target in rule.abcd_types)
        if abcd_distance > abcd_relative_tolerance:
            reasons.append(
                f"CD/AB={metrics.cd_ab.value:.6f} does not match allowed AB=CD types "
                f"{rule.abcd_types} within relative tolerance {abcd_relative_tolerance:.3f}"
            )
    else:
        abcd_distance = inf

    prz = build_xabcd_prz(rule, (x, a, b, c))
    state = PatternState.COMPLETED if not reasons else PatternState.REJECTED
    return PatternEvaluation(
        pattern_id=rule.pattern_id,
        direction=direction,
        state=state,
        metrics=metrics,
        checks=tuple(checks),
        prz=prz,
        abcd_distance=abcd_distance,
        reasons=tuple(reasons),
    )
