from __future__ import annotations

from dataclasses import dataclass

from .models import HarmonicPoint, PatternDirection, PatternState, Pivot, RatioMeasurement
from .prz import PRZComponent, PotentialReversalZone
from .ratios import leg_length


@dataclass(frozen=True, slots=True)
class FiveZeroMetrics:
    b_xa: RatioMeasurement
    c_ab: RatioMeasurement
    d_bc: RatioMeasurement
    cd_ab: RatioMeasurement


@dataclass(frozen=True, slots=True)
class FiveZeroEvaluation:
    pattern_id: str
    direction: PatternDirection
    state: PatternState
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint]
    metrics: FiveZeroMetrics
    prz: PotentialReversalZone
    geometry_score: float
    reciprocal_abcd_price: float
    reciprocal_inside_execution_band: bool
    execution_price: float
    execution_basis: str
    volume3_make_or_break_price: float
    completion_class: str
    reasons: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.state is PatternState.COMPLETED


@dataclass(frozen=True, slots=True)
class FiveZeroProjection:
    pattern_id: str
    direction: PatternDirection
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint]
    b_xa: float
    c_ab: float
    prz: PotentialReversalZone
    reciprocal_abcd_price: float
    reciprocal_inside_execution_band: bool
    execution_price: float
    execution_basis: str
    volume3_make_or_break_price: float


@dataclass(frozen=True, slots=True)
class FiveZeroMatch:
    pattern_id: str
    direction: PatternDirection
    state: PatternState
    scale: int
    points: tuple[HarmonicPoint, ...]
    evaluation: FiveZeroEvaluation
    geometry_score: float
    conflict_key: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class FiveZeroFormingMatch:
    pattern_id: str
    direction: PatternDirection
    state: PatternState
    scale: int
    points: tuple[HarmonicPoint, ...]
    projection: FiveZeroProjection
    geometry_score: float
    conflict_key: tuple[int, ...]


def _ratio(name: str, numerator: float, denominator: float) -> RatioMeasurement:
    if denominator <= 0:
        raise ValueError(f"{name}: denominator must be positive")
    return RatioMeasurement(
        name=name,
        numerator=float(numerator),
        denominator=float(denominator),
        value=float(numerator) / float(denominator),
    )


def _direction(points: tuple[HarmonicPoint, ...]) -> PatternDirection:
    x, a = points[0], points[1]
    if a.price == x.price:
        raise ValueError("X and A cannot have the same price")
    return PatternDirection.BULLISH if a.price > x.price else PatternDirection.BEARISH


def _project_from_c(
    *,
    c_price: float,
    length: float,
    ratio: float,
    direction: PatternDirection,
) -> float:
    return c_price - ratio * length if direction is PatternDirection.BULLISH else c_price + ratio * length


def _point_component(name: str, price: float, ratio: float) -> PRZComponent:
    if price <= 0:
        raise ValueError(f"{name} projects outside the positive-price domain")
    return PRZComponent(
        name=name,
        price_low=float(price),
        price_high=float(price),
        ratio_low=float(ratio),
        ratio_high=float(ratio),
    )


def _build_prz(
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
) -> tuple[PotentialReversalZone, float, bool, float, str, float]:
    """Build the structural Raw PRZ and the separate Volume Three execution refinement.

    Volume Two defines the structural 5-0 PRZ with exactly two measurements: the 50% BC
    retracement and the Reciprocal AB=CD.  Volume Three does not replace that identity with
    a generic 50%-61.8% band.  Instead, 61.8% becomes a conditional execution and
    make-or-break level depending on where the Reciprocal AB=CD completes.
    """

    x, a, b, c = points
    direction = _direction(points)
    bc = leg_length(b.price, c.price)
    ab = leg_length(a.price, b.price)
    if bc <= 0 or ab <= 0:
        raise ValueError("5-0 AB and BC spans must be positive")

    price_50 = _project_from_c(c_price=c.price, length=bc, ratio=0.50, direction=direction)
    price_618 = _project_from_c(c_price=c.price, length=bc, ratio=0.618, direction=direction)
    reciprocal = _project_from_c(c_price=c.price, length=ab, ratio=1.0, direction=direction)

    band_low, band_high = sorted((price_50, price_618))
    reciprocal_inside = band_low <= reciprocal <= band_high

    distance_50 = abs(float(price_50) - float(c.price))
    distance_reciprocal = abs(float(reciprocal) - float(c.price))
    eps = 1e-12 * max(1.0, distance_50, distance_reciprocal)
    if distance_reciprocal < distance_50 - eps:
        execution_price = reciprocal
        execution_basis = "reciprocal_before_50"
    elif abs(distance_reciprocal - distance_50) <= eps:
        execution_price = price_50
        execution_basis = "volume2_50_and_reciprocal"
    else:
        execution_price = price_618
        execution_basis = "volume3_618_after_50"

    prz = PotentialReversalZone(
        pattern_id="five_zero",
        direction=direction,
        components=(
            _point_component("BC 50% completion", price_50, 0.50),
            _point_component("BC 61.8% make-or-break", price_618, 0.618),
            _point_component("Reciprocal AB=CD x1", reciprocal, 1.0),
        ),
    )
    return (
        prz,
        reciprocal,
        reciprocal_inside,
        float(execution_price),
        execution_basis,
        float(price_618),
    )


def measure_five_zero(
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
) -> FiveZeroMetrics:
    if tuple(point.label for point in points) != ("X", "A", "B", "C", "D"):
        raise ValueError("points must be labelled X, A, B, C, D")
    if any(left.index >= right.index for left, right in zip(points, points[1:])):
        raise ValueError("X/A/B/C/D indices must be strictly increasing")

    x, a, b, c, d = points
    xa = leg_length(x.price, a.price)
    ab = leg_length(a.price, b.price)
    bc = leg_length(b.price, c.price)
    cd = leg_length(c.price, d.price)
    if min(xa, ab, bc) <= 0:
        raise ValueError("5-0 source legs must be positive")
    return FiveZeroMetrics(
        b_xa=_ratio("b_xa", ab, xa),
        c_ab=_ratio("c_ab", bc, ab),
        d_bc=_ratio("d_bc", cd, bc),
        cd_ab=_ratio("cd_ab", cd, ab),
    )


def _turning_geometry_ok(points: tuple[HarmonicPoint, ...], direction: PatternDirection) -> bool:
    x, a, b, c, d = points
    if direction is PatternDirection.BULLISH:
        return b.price < x.price < a.price < c.price and b.price < d.price < c.price
    return b.price > x.price > a.price > c.price and b.price > d.price > c.price


def _frontier_geometry_ok(points: tuple[HarmonicPoint, ...], direction: PatternDirection) -> bool:
    x, a, b, c = points
    if direction is PatternDirection.BULLISH:
        return b.price < x.price < a.price < c.price
    return b.price > x.price > a.price > c.price


def _in_band(value: float, low: float, high: float) -> bool:
    eps = 1e-12 * max(1.0, abs(value), abs(low), abs(high))
    return low - eps <= value <= high + eps


def evaluate_five_zero(
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
    *,
    completion_relative_tolerance: float = 0.03,
) -> FiveZeroEvaluation:
    """Evaluate a completed 5-0 without collapsing structure and execution semantics.

    ``completion_relative_tolerance`` is an HT-CN operational tolerance against the BC span.
    It is not claimed as a universal Carney constant.
    """

    if completion_relative_tolerance < 0:
        raise ValueError("5-0 completion tolerance must be non-negative")

    direction = _direction(points)
    metrics = measure_five_zero(points)
    reasons: list[str] = []

    if not _turning_geometry_ok(points, direction):
        reasons.append("5-0 points do not match the required X-A-B-C-D turning geometry")
    if not _in_band(metrics.b_xa.value, 1.13, 1.618):
        reasons.append(f"B/XA={metrics.b_xa.value:.6f} outside 1.13-1.618")
    if not _in_band(metrics.c_ab.value, 1.618, 2.24):
        reasons.append(f"C/AB={metrics.c_ab.value:.6f} outside 1.618-2.24")

    (
        prz,
        reciprocal,
        reciprocal_inside,
        execution_price,
        execution_basis,
        make_or_break_price,
    ) = _build_prz(points[:4])

    d = points[4]
    bc = leg_length(points[2].price, points[3].price)
    completion_error = abs(float(d.price) - execution_price) / max(bc, 1e-12)
    if completion_error > completion_relative_tolerance:
        reasons.append(
            "D does not test the source-aligned 5-0 execution level "
            f"({execution_basis}); relative BC error={completion_error:.6f}"
        )

    price_50 = next(
        component.midpoint for component in prz.components if component.name == "BC 50% completion"
    )
    raw_spread = abs(float(reciprocal) - float(price_50)) / max(bc, 1e-12)
    penalty = min(1.0, (3.0 * completion_error) + min(raw_spread, 0.35))
    geometry_score = round(max(0.0, 100.0 * (1.0 - penalty)), 2)

    if execution_basis == "volume2_50_and_reciprocal":
        completion_class = "volume2_50"
    elif execution_basis == "reciprocal_before_50":
        completion_class = "reciprocal_before_50"
    else:
        completion_class = "volume3_618_refinement"

    return FiveZeroEvaluation(
        pattern_id="five_zero",
        direction=direction,
        state=PatternState.COMPLETED if not reasons else PatternState.REJECTED,
        points=points,
        metrics=metrics,
        prz=prz,
        geometry_score=geometry_score,
        reciprocal_abcd_price=reciprocal,
        reciprocal_inside_execution_band=reciprocal_inside,
        execution_price=execution_price,
        execution_basis=execution_basis,
        volume3_make_or_break_price=make_or_break_price,
        completion_class=completion_class,
        reasons=tuple(reasons),
    )


def project_forming_five_zero(
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
) -> FiveZeroProjection | None:
    if tuple(point.label for point in points) != ("X", "A", "B", "C"):
        raise ValueError("forming 5-0 points must be labelled X, A, B, C")
    if any(left.index >= right.index for left, right in zip(points, points[1:])):
        raise ValueError("X/A/B/C indices must be strictly increasing")

    x, a, b, c = points
    direction = _direction(points)
    xa = leg_length(x.price, a.price)
    ab = leg_length(a.price, b.price)
    bc = leg_length(b.price, c.price)
    if min(xa, ab) <= 0:
        return None
    b_xa = ab / xa
    c_ab = bc / ab
    if not _frontier_geometry_ok(points, direction):
        return None
    if not _in_band(b_xa, 1.13, 1.618) or not _in_band(c_ab, 1.618, 2.24):
        return None

    (
        prz,
        reciprocal,
        reciprocal_inside,
        execution_price,
        execution_basis,
        make_or_break_price,
    ) = _build_prz(points)
    return FiveZeroProjection(
        pattern_id="five_zero",
        direction=direction,
        points=points,
        b_xa=b_xa,
        c_ab=c_ab,
        prz=prz,
        reciprocal_abcd_price=reciprocal,
        reciprocal_inside_execution_band=reciprocal_inside,
        execution_price=execution_price,
        execution_basis=execution_basis,
        volume3_make_or_break_price=make_or_break_price,
    )


def _points_from_pivots(pivots: tuple[Pivot, ...], labels: tuple[str, ...]) -> tuple[HarmonicPoint, ...]:
    return tuple(
        HarmonicPoint(label=label, index=pivot.index, price=pivot.price)
        for label, pivot in zip(labels, pivots)
    )


def scan_five_zero_pivots(
    pivots_by_scale: dict[int, tuple[Pivot, ...] | list[Pivot]],
    *,
    max_completed: int = 100,
    max_forming: int = 20,
) -> tuple[tuple[FiveZeroMatch, ...], tuple[FiveZeroFormingMatch, ...]]:
    completed: list[FiveZeroMatch] = []
    forming: list[FiveZeroFormingMatch] = []

    for scale, raw in pivots_by_scale.items():
        pivots = tuple(raw)
        for start in range(0, len(pivots) - 4):
            chunk = pivots[start : start + 5]
            if any(left.kind == right.kind for left, right in zip(chunk, chunk[1:])):
                continue
            points = _points_from_pivots(chunk, ("X", "A", "B", "C", "D"))
            try:
                evaluation = evaluate_five_zero(points)  # type: ignore[arg-type]
            except ValueError:
                continue
            if evaluation.passed:
                completed.append(
                    FiveZeroMatch(
                        pattern_id="five_zero",
                        direction=evaluation.direction,
                        state=PatternState.COMPLETED,
                        scale=int(scale),
                        points=evaluation.points,
                        evaluation=evaluation,
                        geometry_score=evaluation.geometry_score,
                        conflict_key=tuple(point.index for point in evaluation.points),
                    )
                )

        if len(pivots) >= 4:
            chunk = pivots[-4:]
            if not any(left.kind == right.kind for left, right in zip(chunk, chunk[1:])):
                points = _points_from_pivots(chunk, ("X", "A", "B", "C"))
                try:
                    projection = project_forming_five_zero(points)  # type: ignore[arg-type]
                except ValueError:
                    projection = None
                if projection is not None:
                    bc = max(leg_length(points[2].price, points[3].price), 1e-12)
                    source_width = (
                        projection.prz.source_prz_high - projection.prz.source_prz_low
                        if projection.prz.has_source_prz
                        else projection.prz.width
                    )
                    width_penalty = min(1.0, source_width / bc)
                    forming.append(
                        FiveZeroFormingMatch(
                            pattern_id="five_zero",
                            direction=projection.direction,
                            state=PatternState.FORMING,
                            scale=int(scale),
                            points=projection.points,
                            projection=projection,
                            geometry_score=round(100.0 * (1.0 - width_penalty), 2),
                            conflict_key=tuple(point.index for point in projection.points),
                        )
                    )

    completed.sort(key=lambda item: (-item.points[-1].index, -item.geometry_score, -item.scale))
    forming.sort(key=lambda item: (-item.points[-1].index, -item.geometry_score, -item.scale))

    def dedupe(items):
        out = []
        seen = set()
        for item in items:
            key = (item.direction, item.conflict_key)
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
        return out

    return tuple(dedupe(completed)[:max_completed]), tuple(dedupe(forming)[:max_forming])