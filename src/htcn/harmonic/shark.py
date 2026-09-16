from __future__ import annotations

from dataclasses import dataclass

from .models import HarmonicPoint, PatternDirection, PatternState, Pivot, RatioMeasurement
from .prz import PRZComponent, PotentialReversalZone
from .ratios import leg_length


@dataclass(frozen=True, slots=True)
class SharkMetrics:
    a_0x: RatioMeasurement
    b_xa: RatioMeasurement
    c_ab: RatioMeasurement
    c_0b: RatioMeasurement


@dataclass(frozen=True, slots=True)
class SharkEvaluation:
    pattern_id: str
    direction: PatternDirection
    state: PatternState
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint]
    metrics: SharkMetrics
    prz: PotentialReversalZone
    geometry_score: float
    target_50: float
    target_618: float
    reciprocal_abcd_target: float
    reasons: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.state is PatternState.COMPLETED


@dataclass(frozen=True, slots=True)
class SharkProjection:
    pattern_id: str
    direction: PatternDirection
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint]
    a_0x: float
    b_xa: float
    prz: PotentialReversalZone


@dataclass(frozen=True, slots=True)
class SharkMatch:
    pattern_id: str
    direction: PatternDirection
    state: PatternState
    scale: int
    points: tuple[HarmonicPoint, ...]
    evaluation: SharkEvaluation
    geometry_score: float
    conflict_key: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class SharkFormingMatch:
    pattern_id: str
    direction: PatternDirection
    state: PatternState
    scale: int
    points: tuple[HarmonicPoint, ...]
    projection: SharkProjection
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
    zero, x = points[0], points[1]
    if x.price == zero.price:
        raise ValueError("0 and X cannot have the same price")
    return PatternDirection.BULLISH if x.price > zero.price else PatternDirection.BEARISH


def _project_from_b(
    *,
    b_price: float,
    length: float,
    ratio: float,
    direction: PatternDirection,
) -> float:
    return b_price - ratio * length if direction is PatternDirection.BULLISH else b_price + ratio * length


def _component_range(
    *,
    name: str,
    b_price: float,
    length: float,
    low_ratio: float,
    high_ratio: float,
    direction: PatternDirection,
) -> PRZComponent:
    p1 = _project_from_b(b_price=b_price, length=length, ratio=low_ratio, direction=direction)
    p2 = _project_from_b(b_price=b_price, length=length, ratio=high_ratio, direction=direction)
    low, high = sorted((p1, p2))
    if low <= 0:
        raise ValueError(f"{name} projects outside the positive-price domain")
    return PRZComponent(
        name=name,
        price_low=low,
        price_high=high,
        ratio_low=low_ratio,
        ratio_high=high_ratio,
    )


def _build_prz(
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
) -> PotentialReversalZone:
    zero, x, a, b = points
    direction = _direction(points)
    ab = leg_length(a.price, b.price)
    ob = leg_length(zero.price, b.price)
    if ab <= 0 or ob <= 0:
        raise ValueError("Shark AB and 0B spans must be positive")

    return PotentialReversalZone(
        pattern_id="shark",
        direction=direction,
        components=(
            _component_range(
                name="0B completion",
                b_price=b.price,
                length=ob,
                low_ratio=0.886,
                high_ratio=1.13,
                direction=direction,
            ),
            _component_range(
                name="AB impulse completion",
                b_price=b.price,
                length=ab,
                low_ratio=1.618,
                high_ratio=2.24,
                direction=direction,
            ),
        ),
    )


def _ranges_overlap(prz: PotentialReversalZone) -> bool:
    if len(prz.components) < 2:
        return False
    low = max(component.price_low for component in prz.components)
    high = min(component.price_high for component in prz.components)
    return low <= high


def measure_shark(
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
) -> SharkMetrics:
    if tuple(point.label for point in points) != ("0", "X", "A", "B", "C"):
        raise ValueError("points must be labelled 0, X, A, B, C")
    if any(left.index >= right.index for left, right in zip(points, points[1:])):
        raise ValueError("0/X/A/B/C indices must be strictly increasing")

    zero, x, a, b, c = points
    ox = leg_length(zero.price, x.price)
    xa = leg_length(x.price, a.price)
    ab = leg_length(a.price, b.price)
    bc = leg_length(b.price, c.price)
    ob = leg_length(zero.price, b.price)
    if min(ox, xa, ab, ob) <= 0:
        raise ValueError("Shark source legs must be positive")
    return SharkMetrics(
        a_0x=_ratio("a_0x", xa, ox),
        b_xa=_ratio("b_xa", ab, xa),
        c_ab=_ratio("c_ab", bc, ab),
        c_0b=_ratio("c_0b", bc, ob),
    )


def _turning_geometry_ok(points: tuple[HarmonicPoint, ...], direction: PatternDirection) -> bool:
    zero, x, a, b, c = points
    if direction is PatternDirection.BULLISH:
        return zero.price < a.price < x.price < b.price and c.price < b.price
    return zero.price > a.price > x.price > b.price and c.price > b.price


def _in_band(value: float, low: float, high: float) -> bool:
    eps = 1e-12 * max(1.0, abs(value), abs(low), abs(high))
    return low - eps <= value <= high + eps


def _reaction_targets(
    points: tuple[HarmonicPoint, ...], direction: PatternDirection
) -> tuple[float, float, float]:
    _, _, a, b, c = points
    bc = leg_length(b.price, c.price)
    ab = leg_length(a.price, b.price)
    sign = 1.0 if direction is PatternDirection.BULLISH else -1.0
    return (
        c.price + sign * 0.50 * bc,
        c.price + sign * 0.618 * bc,
        c.price + sign * ab,
    )


def evaluate_shark(
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
) -> SharkEvaluation:
    direction = _direction(points)
    metrics = measure_shark(points)
    reasons: list[str] = []

    if not _turning_geometry_ok(points, direction):
        reasons.append("Shark points do not match the required 0-X-A-B-C turning geometry")
    if not _in_band(metrics.a_0x.value, 0.382, 0.618):
        reasons.append(f"A/0X={metrics.a_0x.value:.6f} outside 0.382-0.618")
    if not _in_band(metrics.b_xa.value, 1.13, 1.618):
        reasons.append(f"B/XA={metrics.b_xa.value:.6f} outside 1.13-1.618")
    if not _in_band(metrics.c_ab.value, 1.618, 2.24):
        reasons.append(f"C/AB={metrics.c_ab.value:.6f} outside 1.618-2.24")
    if not _in_band(metrics.c_0b.value, 0.886, 1.13):
        reasons.append(f"C/0B={metrics.c_0b.value:.6f} outside 0.886-1.13")

    prz = _build_prz(points[:4])
    if not _ranges_overlap(prz):
        reasons.append("Shark 0B and AB completion ranges do not converge")

    c = points[4]
    anchor = (prz.price_low + prz.price_high) / 2.0
    ob = leg_length(points[0].price, points[3].price)
    convergence_error = abs(float(c.price) - anchor) / max(ob, 1e-12)
    geometry_score = round(max(0.0, 100.0 * (1.0 - min(1.0, 4.0 * convergence_error))), 2)
    target_50, target_618, reciprocal_target = _reaction_targets(points, direction)

    return SharkEvaluation(
        pattern_id="shark",
        direction=direction,
        state=PatternState.COMPLETED if not reasons else PatternState.REJECTED,
        points=points,
        metrics=metrics,
        prz=prz,
        geometry_score=geometry_score,
        target_50=target_50,
        target_618=target_618,
        reciprocal_abcd_target=reciprocal_target,
        reasons=tuple(reasons),
    )


def project_forming_shark(
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
) -> SharkProjection | None:
    if tuple(point.label for point in points) != ("0", "X", "A", "B"):
        raise ValueError("forming Shark points must be labelled 0, X, A, B")
    if any(left.index >= right.index for left, right in zip(points, points[1:])):
        raise ValueError("0/X/A/B indices must be strictly increasing")

    zero, x, a, b = points
    direction = _direction(points)
    ox = leg_length(zero.price, x.price)
    xa = leg_length(x.price, a.price)
    ab = leg_length(a.price, b.price)
    if min(ox, xa) <= 0:
        return None
    a_0x = xa / ox
    b_xa = ab / xa
    if not _in_band(a_0x, 0.382, 0.618) or not _in_band(b_xa, 1.13, 1.618):
        return None
    if direction is PatternDirection.BULLISH and not (zero.price < a.price < x.price < b.price):
        return None
    if direction is PatternDirection.BEARISH and not (zero.price > a.price > x.price > b.price):
        return None

    prz = _build_prz(points)
    if not _ranges_overlap(prz):
        return None
    return SharkProjection(
        pattern_id="shark",
        direction=direction,
        points=points,
        a_0x=a_0x,
        b_xa=b_xa,
        prz=prz,
    )


def _points_from_pivots(pivots: tuple[Pivot, ...], labels: tuple[str, ...]) -> tuple[HarmonicPoint, ...]:
    return tuple(
        HarmonicPoint(label=label, index=pivot.index, price=pivot.price)
        for label, pivot in zip(labels, pivots)
    )


def scan_shark_pivots(
    pivots_by_scale: dict[int, tuple[Pivot, ...] | list[Pivot]],
    *,
    max_completed: int = 100,
    max_forming: int = 20,
) -> tuple[tuple[SharkMatch, ...], tuple[SharkFormingMatch, ...]]:
    completed: list[SharkMatch] = []
    forming: list[SharkFormingMatch] = []

    for scale, raw in pivots_by_scale.items():
        pivots = tuple(raw)
        for start in range(0, len(pivots) - 4):
            chunk = pivots[start : start + 5]
            if any(left.kind == right.kind for left, right in zip(chunk, chunk[1:])):
                continue
            points = _points_from_pivots(chunk, ("0", "X", "A", "B", "C"))
            try:
                evaluation = evaluate_shark(points)  # type: ignore[arg-type]
            except ValueError:
                continue
            if evaluation.passed:
                completed.append(
                    SharkMatch(
                        pattern_id="shark",
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
                points = _points_from_pivots(chunk, ("0", "X", "A", "B"))
                try:
                    projection = project_forming_shark(points)  # type: ignore[arg-type]
                except ValueError:
                    projection = None
                if projection is not None:
                    width_basis = max(leg_length(points[0].price, points[3].price), 1e-12)
                    width_penalty = min(1.0, projection.prz.width / width_basis)
                    forming.append(
                        SharkFormingMatch(
                            pattern_id="shark",
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
