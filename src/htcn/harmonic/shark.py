from __future__ import annotations

from dataclasses import dataclass

from .models import HarmonicPoint, PatternDirection, PatternState, Pivot, RatioMeasurement
from .prz import PotentialReversalZone
from .ratios import leg_length
from .shark_source import SharkSourceContract, build_shark_source_contract


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
    source_contract: SharkSourceContract
    geometry_score: float
    target_50: float
    target_618: float
    reciprocal_abcd_target: float
    initial_target: float
    initial_target_basis: str
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
    source_contract: SharkSourceContract


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
    """Return Shark -> 5-0 post-completion reaction measurements.

    These are management measurements only. They do not contribute to Shark identity or
    Shark Source Raw PRZ membership.
    """
    _, _, a, b, c = points
    bc = leg_length(b.price, c.price)
    ab = leg_length(a.price, b.price)
    sign = 1.0 if direction is PatternDirection.BULLISH else -1.0
    return (
        c.price + sign * 0.50 * bc,
        c.price + sign * 0.618 * bc,
        c.price + sign * ab,
    )


def _initial_shark_target(
    *,
    c_price: float,
    target_50: float,
    reciprocal_abcd_target: float,
) -> tuple[float, str]:
    """Volume Three management: first encountered of 50% BC and Reciprocal AB=CD."""
    distance_50 = abs(float(target_50) - float(c_price))
    distance_reciprocal = abs(float(reciprocal_abcd_target) - float(c_price))
    eps = 1e-12 * max(1.0, distance_50, distance_reciprocal)
    if abs(distance_50 - distance_reciprocal) <= eps:
        return float(target_50), "50_percent_and_reciprocal_abcd_tie"
    if distance_50 < distance_reciprocal:
        return float(target_50), "50_percent"
    return float(reciprocal_abcd_target), "reciprocal_abcd"


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

    source_contract = build_shark_source_contract(points[:4])
    prz = source_contract.prz
    if not source_contract.has_source_prz:
        reasons.append("Shark 0B and AB source completion corridors do not converge")
    elif not source_contract.contains_source_prz(float(points[4].price)):
        reasons.append("C does not test the frozen Shark Source Raw PRZ")

    c = points[4]
    if source_contract.has_source_prz:
        anchor = (float(source_contract.source_prz_low) + float(source_contract.source_prz_high)) / 2.0
    else:
        anchor = (prz.ideal_core_low + prz.ideal_core_high) / 2.0
    ob = leg_length(points[0].price, points[3].price)
    convergence_error = abs(float(c.price) - anchor) / max(ob, 1e-12)
    geometry_score = round(max(0.0, 100.0 * (1.0 - min(1.0, 4.0 * convergence_error))), 2)

    target_50, target_618, reciprocal_target = _reaction_targets(points, direction)
    initial_target, initial_target_basis = _initial_shark_target(
        c_price=c.price,
        target_50=target_50,
        reciprocal_abcd_target=reciprocal_target,
    )

    return SharkEvaluation(
        pattern_id="shark",
        direction=direction,
        state=PatternState.COMPLETED if not reasons else PatternState.REJECTED,
        points=points,
        metrics=metrics,
        prz=prz,
        source_contract=source_contract,
        geometry_score=geometry_score,
        target_50=target_50,
        target_618=target_618,
        reciprocal_abcd_target=reciprocal_target,
        initial_target=initial_target,
        initial_target_basis=initial_target_basis,
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
    if min(ox, xa, ab) <= 0:
        return None
    a_0x = xa / ox
    b_xa = ab / xa
    if not _in_band(a_0x, 0.382, 0.618) or not _in_band(b_xa, 1.13, 1.618):
        return None
    if direction is PatternDirection.BULLISH and not (zero.price < a.price < x.price < b.price):
        return None
    if direction is PatternDirection.BEARISH and not (zero.price > a.price > x.price > b.price):
        return None

    source_contract = build_shark_source_contract(points)
    if not source_contract.has_source_prz:
        return None
    return SharkProjection(
        pattern_id="shark",
        direction=direction,
        points=points,
        a_0x=a_0x,
        b_xa=b_xa,
        prz=source_contract.prz,
        source_contract=source_contract,
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
