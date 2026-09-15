from __future__ import annotations

from dataclasses import dataclass
from math import inf

from .models import HarmonicPoint, PatternDirection, PatternState, Pivot, RatioMeasurement
from .prz import PRZComponent, PotentialReversalZone
from .ratios import RECIPROCAL_ABCD, leg_length


@dataclass(frozen=True, slots=True)
class ABCDMetrics:
    c_ab: RatioMeasurement
    bc_projection: RatioMeasurement
    cd_ab: RatioMeasurement


@dataclass(frozen=True, slots=True)
class ABCDCheck:
    name: str
    value: float
    target: float | None
    passed: bool
    relative_error: float


@dataclass(frozen=True, slots=True)
class ABCDEvaluation:
    pattern_id: str
    direction: PatternDirection
    state: PatternState
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint]
    metrics: ABCDMetrics
    checks: tuple[ABCDCheck, ...]
    prz: PotentialReversalZone
    reciprocal_c_target: float | None
    reciprocal_bc_target: float | None
    geometry_score: float
    reasons: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.state is PatternState.COMPLETED


@dataclass(frozen=True, slots=True)
class ABCDMatch:
    pattern_id: str
    direction: PatternDirection
    state: PatternState
    scale: int
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint]
    evaluation: ABCDEvaluation
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


def measure_abcd(
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
) -> ABCDMetrics:
    if tuple(point.label for point in points) != ("A", "B", "C", "D"):
        raise ValueError("points must be labelled A, B, C, D")
    if any(left.index >= right.index for left, right in zip(points, points[1:])):
        raise ValueError("A/B/C/D indices must be strictly increasing")
    a, b, c, d = points
    ab = leg_length(a.price, b.price)
    bc = leg_length(b.price, c.price)
    cd = leg_length(c.price, d.price)
    if ab <= 0 or bc <= 0:
        raise ValueError("AB and BC must have positive length")
    return ABCDMetrics(
        c_ab=_ratio("c_ab", bc, ab),
        bc_projection=_ratio("bc_projection", cd, bc),
        cd_ab=_ratio("cd_ab", cd, ab),
    )


def _infer_direction(points: tuple[HarmonicPoint, ...]) -> PatternDirection:
    a, b, _, _ = points
    if b.price == a.price:
        raise ValueError("A and B cannot have the same price")
    # AB down -> CD is expected to complete at a low -> bullish reversal structure.
    return PatternDirection.BULLISH if b.price < a.price else PatternDirection.BEARISH


def _turning_geometry_ok(
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
    direction: PatternDirection,
) -> bool:
    a, b, c, d = points
    if direction is PatternDirection.BULLISH:
        return a.price > b.price and c.price > b.price and d.price < c.price
    return a.price < b.price and c.price < b.price and d.price > c.price


def _relative_error(value: float, target: float) -> float:
    if target <= 0:
        return inf
    return abs(float(value) - float(target)) / float(target)


def _nearest_reciprocal_pair(c_ab: float, bc_projection: float) -> tuple[float, float, float, float]:
    """Return (C target, BC target, C relative error, BC relative error).

    The Volume One reciprocal table contains two valid BC projections for a 0.382 C
    retracement.  We evaluate every source-listed pair and choose the pair with the lowest
    combined normalized error.  No arbitrary interpolation between Carney ratios is used.
    """

    best: tuple[float, float, float, float] | None = None
    best_error = inf
    for c_target, bc_targets in RECIPROCAL_ABCD.items():
        c_error = _relative_error(c_ab, c_target)
        for bc_target in bc_targets:
            bc_error = _relative_error(bc_projection, bc_target)
            combined = c_error + bc_error
            if combined < best_error:
                best_error = combined
                best = (float(c_target), float(bc_target), c_error, bc_error)
    if best is None:
        raise RuntimeError("RECIPROCAL_ABCD table is empty")
    return best


def _project_completion_price(
    *,
    c_price: float,
    length: float,
    direction: PatternDirection,
) -> float:
    return c_price - length if direction is PatternDirection.BULLISH else c_price + length


def _build_prz(
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
    *,
    direction: PatternDirection,
    reciprocal_bc_target: float,
) -> PotentialReversalZone:
    a, b, c, _ = points
    ab = leg_length(a.price, b.price)
    bc = leg_length(b.price, c.price)
    abcd_price = _project_completion_price(c_price=c.price, length=ab, direction=direction)
    reciprocal_price = _project_completion_price(
        c_price=c.price,
        length=bc * reciprocal_bc_target,
        direction=direction,
    )
    if min(abcd_price, reciprocal_price) <= 0:
        raise ValueError("AB=CD projection produced a non-positive PRZ price")
    return PotentialReversalZone(
        pattern_id="abcd",
        direction=direction,
        components=(
            PRZComponent(
                name="AB=CD x1",
                price_low=abcd_price,
                price_high=abcd_price,
                ratio_low=1.0,
                ratio_high=1.0,
            ),
            PRZComponent(
                name="BC reciprocal",
                price_low=reciprocal_price,
                price_high=reciprocal_price,
                ratio_low=reciprocal_bc_target,
                ratio_high=reciprocal_bc_target,
            ),
        ),
    )


def evaluate_abcd(
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
    *,
    c_relative_tolerance: float = 0.03,
    bc_relative_tolerance: float = 0.03,
    abcd_relative_tolerance: float = 0.03,
) -> ABCDEvaluation:
    """Evaluate one completed standalone AB=CD structure.

    Carney's source geometry is discrete: C must align with one of the harmonic
    retracements in the 0.382-0.886 family, its BC projection must align with the
    corresponding reciprocal extension, and the defining completion is equivalent AB=CD.

    The three tolerance values are explicit HT-CN matching policy, *not* claimed as book
    constants.  Keeping them separate prevents an operational real-market tolerance from
    silently becoming part of the canonical Carney rule registry.
    """

    if min(c_relative_tolerance, bc_relative_tolerance, abcd_relative_tolerance) < 0:
        raise ValueError("AB=CD tolerances must be non-negative")

    direction = _infer_direction(points)
    metrics = measure_abcd(points)
    c_target, bc_target, c_error, bc_error = _nearest_reciprocal_pair(
        metrics.c_ab.value,
        metrics.bc_projection.value,
    )
    abcd_error = _relative_error(metrics.cd_ab.value, 1.0)
    reasons: list[str] = []
    checks: list[ABCDCheck] = []

    if not _turning_geometry_ok(points, direction):
        reasons.append("AB=CD points do not alternate in the expected reversal geometry")

    c_passed = c_error <= c_relative_tolerance
    checks.append(ABCDCheck("c_ab_reciprocal", metrics.c_ab.value, c_target, c_passed, c_error))
    if not c_passed:
        reasons.append(
            f"C/AB={metrics.c_ab.value:.6f} not close to a source-listed reciprocal C ratio"
        )

    bc_passed = bc_error <= bc_relative_tolerance
    checks.append(
        ABCDCheck("bc_projection_reciprocal", metrics.bc_projection.value, bc_target, bc_passed, bc_error)
    )
    if not bc_passed:
        reasons.append(
            f"CD/BC={metrics.bc_projection.value:.6f} does not align with reciprocal {bc_target:g}"
        )

    abcd_passed = abcd_error <= abcd_relative_tolerance
    checks.append(ABCDCheck("equivalent_abcd", metrics.cd_ab.value, 1.0, abcd_passed, abcd_error))
    if not abcd_passed:
        reasons.append(f"CD/AB={metrics.cd_ab.value:.6f} is not an equivalent AB=CD completion")

    prz = _build_prz(points, direction=direction, reciprocal_bc_target=bc_target)
    width_ratio = prz.width / max(leg_length(points[0].price, points[1].price), 1e-12)
    penalty = min(1.0, (2.0 * c_error) + (2.0 * bc_error) + (2.5 * abcd_error) + width_ratio)
    geometry_score = round(100.0 * (1.0 - penalty), 2)

    return ABCDEvaluation(
        pattern_id="abcd",
        direction=direction,
        state=PatternState.COMPLETED if not reasons else PatternState.REJECTED,
        points=points,
        metrics=metrics,
        checks=tuple(checks),
        prz=prz,
        reciprocal_c_target=c_target,
        reciprocal_bc_target=bc_target,
        geometry_score=geometry_score,
        reasons=tuple(reasons),
    )


def iter_abcd_points(pivots: tuple[Pivot, ...] | list[Pivot]) -> tuple[tuple[HarmonicPoint, ...], ...]:
    """Return historical four-pivot A/B/C/D windows independent of XABCD semantics."""

    ordered = tuple(pivots)
    if any(left.index >= right.index for left, right in zip(ordered, ordered[1:])):
        raise ValueError("pivot sequence must be ordered")
    if len({pivot.scale for pivot in ordered}) > 1:
        raise ValueError("AB=CD candidate generation must operate on one scale")

    out: list[tuple[HarmonicPoint, ...]] = []
    for start in range(0, len(ordered) - 3):
        chunk = ordered[start : start + 4]
        if any(left.kind == right.kind for left, right in zip(chunk, chunk[1:])):
            continue
        out.append(
            tuple(
                HarmonicPoint(label=label, index=pivot.index, price=pivot.price)
                for label, pivot in zip(("A", "B", "C", "D"), chunk)
            )
        )
    return tuple(out)


def scan_abcd_pivots(
    pivots_by_scale: dict[int, tuple[Pivot, ...] | list[Pivot]],
    *,
    c_relative_tolerance: float = 0.03,
    bc_relative_tolerance: float = 0.03,
    abcd_relative_tolerance: float = 0.03,
    max_completed: int = 100,
) -> tuple[ABCDMatch, ...]:
    matches: list[ABCDMatch] = []
    for scale, pivots in pivots_by_scale.items():
        for points in iter_abcd_points(pivots):
            try:
                evaluation = evaluate_abcd(
                    points,  # type: ignore[arg-type]
                    c_relative_tolerance=c_relative_tolerance,
                    bc_relative_tolerance=bc_relative_tolerance,
                    abcd_relative_tolerance=abcd_relative_tolerance,
                )
            except ValueError:
                continue
            if not evaluation.passed:
                continue
            matches.append(
                ABCDMatch(
                    pattern_id="abcd",
                    direction=evaluation.direction,
                    state=PatternState.COMPLETED,
                    scale=int(scale),
                    points=evaluation.points,
                    evaluation=evaluation,
                    geometry_score=evaluation.geometry_score,
                    conflict_key=tuple(point.index for point in evaluation.points),
                )
            )

    matches.sort(
        key=lambda item: (
            -item.points[-1].index,
            -item.geometry_score,
            -item.scale,
        )
    )
    out: list[ABCDMatch] = []
    seen: set[tuple[PatternDirection, tuple[int, ...]]] = set()
    for item in matches:
        key = (item.direction, item.conflict_key)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return tuple(out[:max_completed])
