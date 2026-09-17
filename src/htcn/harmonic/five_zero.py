from __future__ import annotations

from dataclasses import dataclass

from .five_zero_source import FiveZeroSourceContract, build_five_zero_source_contract
from .models import HarmonicPoint, PatternDirection, PatternState, Pivot, RatioMeasurement
from .prz import PotentialReversalZone
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
    source_contract: FiveZeroSourceContract
    geometry_score: float
    reciprocal_abcd_price: float
    reciprocal_inside_execution_band: bool
    source_raw_prz_test: bool
    within_v3_execution_envelope: bool
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
    source_contract: FiveZeroSourceContract
    reciprocal_abcd_price: float


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
) -> FiveZeroEvaluation:
    direction = _direction(points)
    metrics = measure_five_zero(points)
    reasons: list[str] = []

    if not _turning_geometry_ok(points, direction):
        reasons.append("5-0 points do not match the required X-A-B-C-D turning geometry")
    if not _in_band(metrics.b_xa.value, 1.13, 1.618):
        reasons.append(f"B/XA={metrics.b_xa.value:.6f} outside 1.13-1.618")
    if not _in_band(metrics.c_ab.value, 1.618, 2.24):
        reasons.append(f"C/AB={metrics.c_ab.value:.6f} outside 1.618-2.24")

    contract = build_five_zero_source_contract(points[:4])
    d = points[4]
    completion_class = contract.classify_completion(float(d.price))
    if completion_class == "outside_reconciled_completion_zone":
        reasons.append(
            "D does not test the Volume Two Source Raw PRZ or the reconciled Volume Three 61.8 execution envelope"
        )

    # Compatibility diagnostic only.  M2.29 explicitly removes this old 50%-61.8-band test
    # from identity: a Reciprocal AB=CD can complete before 50% and still be source-valid.
    reciprocal_inside_legacy_band = contract.legacy_reciprocal_inside_50_618_band
    source_raw_prz_test = contract.contains_raw_prz(float(d.price))
    within_execution_envelope = contract.contains_execution_envelope(float(d.price))

    bc = max(leg_length(points[2].price, points[3].price), 1e-12)
    preferred = contract.execution_refinement.preferred_execution_price
    preferred_distance = abs(float(d.price) - preferred) / bc
    geometry_score = round(max(0.0, 100.0 * (1.0 - min(1.0, 3.0 * preferred_distance))), 2)

    return FiveZeroEvaluation(
        pattern_id="five_zero",
        direction=direction,
        state=PatternState.COMPLETED if not reasons else PatternState.REJECTED,
        points=points,
        metrics=metrics,
        prz=contract.prz,
        source_contract=contract,
        geometry_score=geometry_score,
        reciprocal_abcd_price=contract.reciprocal_abcd_price,
        reciprocal_inside_execution_band=reciprocal_inside_legacy_band,
        source_raw_prz_test=source_raw_prz_test,
        within_v3_execution_envelope=within_execution_envelope,
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

    # Volume Two structural eligibility is fully knowable from X/A/B/C.  Do not reject a
    # source-valid forming 5-0 merely because Reciprocal AB=CD lies before the 50% level.
    contract = build_five_zero_source_contract(points)
    return FiveZeroProjection(
        pattern_id="five_zero",
        direction=direction,
        points=points,
        b_xa=b_xa,
        c_ab=c_ab,
        prz=contract.prz,
        source_contract=contract,
        reciprocal_abcd_price=contract.reciprocal_abcd_price,
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
                    width_penalty = min(1.0, projection.source_contract.source_prz_width / bc)
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
