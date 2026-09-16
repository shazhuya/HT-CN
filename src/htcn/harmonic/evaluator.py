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
    target: float | None = None
    relative_error: float | None = None
    policy: str = "band"


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


@dataclass(frozen=True, slots=True)
class _IdentityEvaluation:
    """Cheap identity result before any projected PRZ objects are constructed."""

    direction: PatternDirection
    metrics: XABCDMetrics
    checks: tuple[ConstraintCheck, ...]
    abcd_distance: float
    reasons: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.reasons


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

    xa = leg_length(x.price, a.price)
    ab = leg_length(a.price, b.price)
    bc = leg_length(b.price, c.price)
    cd = leg_length(c.price, d.price)
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


def _nearest_harmonic_target(value: float, targets: tuple[float, ...]) -> tuple[float, float, float]:
    target = min(targets, key=lambda item: abs(float(value) - float(item)) / float(item))
    absolute_error = abs(float(value) - float(target))
    relative_error = absolute_error / float(target)
    return float(target), absolute_error, relative_error


def _evaluate_identity(
    rule: PatternRule,
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
    *,
    include_source_tolerance: bool,
    abcd_relative_tolerance: float,
    harmonic_family_relative_tolerance: float,
) -> _IdentityEvaluation:
    """Evaluate source-backed identity without constructing any PRZ projection.

    This function owns the identity logic used by both the public full evaluator and the
    Scanner fast path. Keeping one implementation prevents a performance optimization from
    creating a second, subtly different pattern definition.
    """
    if rule.schema != "XABCD":
        raise ValueError(f"rule {rule.pattern_id!r} is not XABCD")
    if not rule.executable_identity:
        raise ValueError(f"rule {rule.pattern_id!r} is not executable yet")
    if abcd_relative_tolerance < 0:
        raise ValueError("abcd_relative_tolerance must be non-negative")
    if harmonic_family_relative_tolerance < 0:
        raise ValueError("harmonic_family_relative_tolerance must be non-negative")

    x, a, _, _, _ = points
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
                policy="source_band",
            )
        )
        if not passed:
            reasons.append(
                f"{name}={value:.6f} outside allowed {constraint.minimum:g}-{constraint.maximum:g}"
            )

    for name, targets in rule.harmonic_targets.items():
        if name not in metric_by_name:
            continue
        value = metric_by_name[name]
        target, absolute_error, relative_error = _nearest_harmonic_target(value, targets)
        exact = absolute_error <= 1e-12 * max(1.0, abs(value), abs(target))
        passed = relative_error <= harmonic_family_relative_tolerance
        checks.append(
            ConstraintCheck(
                name=f"{name}_harmonic_family",
                value=value,
                passed=passed,
                canonical_passed=exact,
                distance_to_canonical=absolute_error,
                target=target,
                relative_error=relative_error,
                policy="operational_match_to_source_family",
            )
        )
        if not passed:
            rendered = ",".join(f"{item:g}" for item in targets)
            reasons.append(
                f"{name}={value:.6f} not within HT-CN {harmonic_family_relative_tolerance:.1%} "
                f"matching tolerance of source harmonic family [{rendered}]"
            )

    if rule.abcd_minimum is not None:
        passed = metrics.cd_ab.value + 1e-12 >= rule.abcd_minimum
        checks.append(
            ConstraintCheck(
                name="abcd_minimum",
                value=metrics.cd_ab.value,
                passed=passed,
                canonical_passed=passed,
                distance_to_canonical=max(0.0, rule.abcd_minimum - metrics.cd_ab.value),
                target=rule.abcd_minimum,
                relative_error=(
                    max(0.0, rule.abcd_minimum - metrics.cd_ab.value) / rule.abcd_minimum
                    if rule.abcd_minimum > 0
                    else None
                ),
                policy="source_minimum",
            )
        )
        if not passed:
            reasons.append(
                f"CD/AB={metrics.cd_ab.value:.6f} below source minimum {rule.abcd_minimum:g}"
            )

    if rule.abcd_types:
        abcd_distance = min(abs(metrics.cd_ab.value - target) / target for target in rule.abcd_types)
    else:
        abcd_distance = inf

    return _IdentityEvaluation(
        direction=direction,
        metrics=metrics,
        checks=tuple(checks),
        abcd_distance=abcd_distance,
        reasons=tuple(reasons),
    )


def match_xabcd(
    rule: PatternRule,
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
    *,
    include_source_tolerance: bool = True,
    abcd_relative_tolerance: float = 0.03,
    harmonic_family_relative_tolerance: float = 0.03,
) -> PatternEvaluation | None:
    """Return a full completed match, or ``None`` without building PRZ for a rejection.

    This is the Scanner/research hot-path API. It is semantically identical to asking
    ``evaluate_xabcd(...).passed`` but avoids constructing the much richer M2.26 component
    audit for the overwhelming majority of rule/candidate pairs that already fail identity.
    """
    identity = _evaluate_identity(
        rule,
        points,
        include_source_tolerance=include_source_tolerance,
        abcd_relative_tolerance=abcd_relative_tolerance,
        harmonic_family_relative_tolerance=harmonic_family_relative_tolerance,
    )
    if not identity.passed:
        return None

    x, a, b, c, _ = points
    prz = build_xabcd_prz(rule, (x, a, b, c))
    return PatternEvaluation(
        pattern_id=rule.pattern_id,
        direction=identity.direction,
        state=PatternState.COMPLETED,
        metrics=identity.metrics,
        checks=identity.checks,
        prz=prz,
        abcd_distance=identity.abcd_distance,
        reasons=(),
    )


def evaluate_xabcd(
    rule: PatternRule,
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
    *,
    include_source_tolerance: bool = True,
    abcd_relative_tolerance: float = 0.03,
    harmonic_family_relative_tolerance: float = 0.03,
) -> PatternEvaluation:
    """Evaluate one completed XABCD candidate against one Carney rule.

    The public audit evaluator preserves the historical contract and therefore still emits
    a projected PRZ even for a rejected candidate. High-volume Scanner/research code should
    use :func:`match_xabcd`, which shares the exact same identity logic but constructs PRZ
    only after that identity passes.
    """
    identity = _evaluate_identity(
        rule,
        points,
        include_source_tolerance=include_source_tolerance,
        abcd_relative_tolerance=abcd_relative_tolerance,
        harmonic_family_relative_tolerance=harmonic_family_relative_tolerance,
    )
    x, a, b, c, _ = points
    prz = build_xabcd_prz(rule, (x, a, b, c))
    return PatternEvaluation(
        pattern_id=rule.pattern_id,
        direction=identity.direction,
        state=PatternState.COMPLETED if identity.passed else PatternState.REJECTED,
        metrics=identity.metrics,
        checks=identity.checks,
        prz=prz,
        abcd_distance=identity.abcd_distance,
        reasons=identity.reasons,
    )
