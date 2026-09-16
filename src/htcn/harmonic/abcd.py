from __future__ import annotations

from dataclasses import dataclass
from math import inf
from typing import Any

from .models import HarmonicPoint, PatternDirection, PatternState, Pivot, RatioMeasurement
from .prz import PRZComponent, PotentialReversalZone
from .ratios import RECIPROCAL_ABCD, leg_length


ABCD_SOURCE_PRZ_REFS = ("Volume One pp.45-46", "Volume Three pp.76-85")
ABCD_SOURCE_PRZ_NOTE = (
    "Standalone AB=CD Source Raw PRZ is the range between the exact equivalent AB=CD "
    "completion and the primary reciprocal BC projection selected by the C retracement. "
    "The exact AB=CD completion is the defining minimum; BC complements the zone."
)
ABCD_EXECUTION_LAYERING_REFS = ("Volume Three pp.81-86",)
# Only source-cleared secondary BC layers are executable here.  Do not infer a universal
# "next ratio" for every reciprocal row merely because a larger harmonic number exists.
ABCD_EXECUTION_LAYERING: dict[float, float] = {
    1.618: 2.0,
    2.0: 2.24,
}


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
class ABCDExecutionToleranceLayer:
    """Volume Three secondary BC layer; explicitly not part of identity or Source Raw PRZ."""

    status: str
    primary_bc_target: float
    secondary_bc_target: float | None
    price: float | None
    source_refs: tuple[str, ...]
    source_note: str

    @property
    def available(self) -> bool:
        return self.status == "source_backed" and self.secondary_bc_target is not None and self.price is not None

    def as_payload(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "status": self.status,
            "primary_bc_target": float(self.primary_bc_target),
            "secondary_bc_target": (
                None if self.secondary_bc_target is None else float(self.secondary_bc_target)
            ),
            "price": None if self.price is None else float(self.price),
            "source_refs": list(self.source_refs),
            "source_note": self.source_note,
            "affects_identity": False,
            "included_in_source_raw_prz": False,
            "role": "execution_tolerance_layer",
        }


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
class ABCDProjection:
    pattern_id: str
    direction: PatternDirection
    state: PatternState
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint]
    c_ab: float
    reciprocal_c_target: float
    reciprocal_bc_target: float
    source_tolerance_used: bool
    prz: PotentialReversalZone
    geometry_score: float


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


@dataclass(frozen=True, slots=True)
class ABCDFormingMatch:
    pattern_id: str
    direction: PatternDirection
    state: PatternState
    scale: int
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint]
    projection: ABCDProjection
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
    if len(points) < 2:
        raise ValueError("AB=CD direction requires at least A and B")
    a, b = points[0], points[1]
    if b.price == a.price:
        raise ValueError("A and B cannot have the same price")
    return PatternDirection.BULLISH if b.price < a.price else PatternDirection.BEARISH


def _turning_geometry_ok(
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
    direction: PatternDirection,
) -> bool:
    a, b, c, d = points
    if direction is PatternDirection.BULLISH:
        return a.price > b.price and c.price > b.price and d.price < c.price
    return a.price < b.price and c.price < b.price and d.price > c.price


def _forming_turning_geometry_ok(
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint],
    direction: PatternDirection,
) -> bool:
    a, b, c = points
    if direction is PatternDirection.BULLISH:
        return a.price > b.price and c.price > b.price and c.price < a.price
    return a.price < b.price and c.price < b.price and c.price > a.price


def _relative_error(value: float, target: float) -> float:
    if target <= 0:
        return inf
    return abs(float(value) - float(target)) / float(target)


def _nearest_c_target(c_ab: float) -> tuple[float, float]:
    target = min(RECIPROCAL_ABCD, key=lambda value: _relative_error(c_ab, value))
    return float(target), _relative_error(c_ab, target)


def _nearest_reciprocal_pair(c_ab: float, bc_projection: float) -> tuple[float, float, float, float]:
    """Return (C target, BC target, C relative error, BC relative error)."""

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


def _select_forming_bc_target(c_ab: float, c_target: float) -> float:
    """Choose the source-listed reciprocal projection that best converges with x1 AB=CD.

    The 0.382 row contains both 2.24 and 2.618. Before D exists there is no observed CD
    leg to choose between them, so the projection closest to the equivalent AB=CD implied
    ratio (1/C) is used for the primary live PRZ. Source alternatives remain recoverable
    from ``RECIPROCAL_ABCD`` and are never rewritten.
    """

    targets = RECIPROCAL_ABCD[c_target]
    implied = 1.0 / c_ab
    return float(min(targets, key=lambda value: abs(float(value) - implied)))


def _project_completion_price(
    *,
    c_price: float,
    length: float,
    direction: PatternDirection,
) -> float:
    return c_price - length if direction is PatternDirection.BULLISH else c_price + length


def _source_layer_target(primary_bc_target: float) -> float | None:
    for source_primary, secondary in ABCD_EXECUTION_LAYERING.items():
        if abs(float(primary_bc_target) - float(source_primary)) <= 1e-9:
            return float(secondary)
    return None


def build_abcd_execution_tolerance_layer(
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint] | tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
    *,
    direction: PatternDirection,
    primary_bc_target: float,
) -> ABCDExecutionToleranceLayer:
    """Build only source-cleared Volume Three secondary BC execution layers.

    This is deliberately separate from identity and Source Raw PRZ.  Unsupported primary BC
    rows remain unresolved rather than extrapolating a universal next-ratio rule.
    """

    secondary = _source_layer_target(primary_bc_target)
    if secondary is None:
        return ABCDExecutionToleranceLayer(
            status="unresolved_fail_closed",
            primary_bc_target=float(primary_bc_target),
            secondary_bc_target=None,
            price=None,
            source_refs=ABCD_EXECUTION_LAYERING_REFS,
            source_note=(
                "No figure-backed secondary BC layer is frozen for this primary reciprocal row; "
                "HT-CN does not infer a generic next harmonic ratio."
            ),
        )
    _, b, c = points[:3]
    bc = leg_length(b.price, c.price)
    price = _project_completion_price(
        c_price=c.price,
        length=bc * secondary,
        direction=direction,
    )
    if price <= 0:
        return ABCDExecutionToleranceLayer(
            status="unresolved_fail_closed",
            primary_bc_target=float(primary_bc_target),
            secondary_bc_target=float(secondary),
            price=None,
            source_refs=ABCD_EXECUTION_LAYERING_REFS,
            source_note="Projected secondary BC layer is non-positive and is therefore not executable.",
        )
    return ABCDExecutionToleranceLayer(
        status="source_backed",
        primary_bc_target=float(primary_bc_target),
        secondary_bc_target=float(secondary),
        price=float(price),
        source_refs=ABCD_EXECUTION_LAYERING_REFS,
        source_note=(
            "Volume Three BC Layering is a secondary execution-tolerance measurement for price "
            "action that exceeds the ideal AB=CD completion; it is not part of pattern identity "
            "and is not included in the Source Raw PRZ."
        ),
    )


def _build_prz_from_abc(
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint] | tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
    *,
    direction: PatternDirection,
    reciprocal_bc_target: float,
) -> PotentialReversalZone:
    a, b, c = points[:3]
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
    source_low = min(float(abcd_price), float(reciprocal_price))
    source_high = max(float(abcd_price), float(reciprocal_price))
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
        source_prz_low=source_low,
        source_prz_high=source_high,
        source_prz_component_names=("AB=CD x1", "BC reciprocal"),
        source_prz_defining_component="AB=CD x1",
        source_prz_selection_method="exact_abcd_plus_primary_reciprocal_bc",
        source_prz_source_refs=ABCD_SOURCE_PRZ_REFS,
        source_prz_note=ABCD_SOURCE_PRZ_NOTE,
        source_prz_reason=None,
    )


def evaluate_abcd(
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
    *,
    c_relative_tolerance: float = 0.03,
    bc_relative_tolerance: float = 0.03,
    abcd_relative_tolerance: float = 0.03,
) -> ABCDEvaluation:
    """Evaluate one completed standalone AB=CD structure.

    The tolerance values are explicit HT-CN operational matching policy, not claimed as
    constants published by Carney.
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

    prz = _build_prz_from_abc(points, direction=direction, reciprocal_bc_target=bc_target)
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


def project_forming_abcd(
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint],
    *,
    c_relative_tolerance: float = 0.03,
) -> ABCDProjection | None:
    """Project a live D-zone from the current A/B/C frontier.

    Only the latest three confirmed pivots for each scale are eligible upstream. C must
    already align with a source-listed Carney retracement. No historical ABC slice remains
    permanently "forming" after a later confirmed pivot appears.
    """

    if tuple(point.label for point in points) != ("A", "B", "C"):
        raise ValueError("forming AB=CD points must be labelled A, B, C")
    if any(left.index >= right.index for left, right in zip(points, points[1:])):
        raise ValueError("A/B/C indices must be strictly increasing")
    if c_relative_tolerance < 0:
        raise ValueError("c_relative_tolerance must be non-negative")

    direction = _infer_direction(points)
    if not _forming_turning_geometry_ok(points, direction):
        return None
    a, b, c = points
    ab = leg_length(a.price, b.price)
    bc = leg_length(b.price, c.price)
    if ab <= 0 or bc <= 0:
        return None
    c_ab = bc / ab
    c_target, c_error = _nearest_c_target(c_ab)
    if c_error > c_relative_tolerance:
        return None
    bc_target = _select_forming_bc_target(c_ab, c_target)
    try:
        prz = _build_prz_from_abc(points, direction=direction, reciprocal_bc_target=bc_target)
    except ValueError:
        return None
    width_ratio = prz.width / max(ab, 1e-12)
    penalty = min(1.0, (2.5 * c_error) + min(width_ratio, 0.5))
    return ABCDProjection(
        pattern_id="abcd",
        direction=direction,
        state=PatternState.FORMING,
        points=points,
        c_ab=float(c_ab),
        reciprocal_c_target=float(c_target),
        reciprocal_bc_target=float(bc_target),
        source_tolerance_used=c_error > 1e-12,
        prz=prz,
        geometry_score=round(100.0 * (1.0 - penalty), 2),
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


def forming_abc_points(pivots: tuple[Pivot, ...] | list[Pivot]) -> tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint] | None:
    """Return only the current A/B/C frontier for one scale."""

    ordered = tuple(pivots)
    if len(ordered) < 3:
        return None
    if any(left.index >= right.index for left, right in zip(ordered, ordered[1:])):
        raise ValueError("pivot sequence must be ordered")
    if len({pivot.scale for pivot in ordered}) > 1:
        raise ValueError("forming AB=CD candidate must operate on one scale")
    chunk = ordered[-3:]
    if any(left.kind == right.kind for left, right in zip(chunk, chunk[1:])):
        return None
    return tuple(
        HarmonicPoint(label=label, index=pivot.index, price=pivot.price)
        for label, pivot in zip(("A", "B", "C"), chunk)
    )  # type: ignore[return-value]


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
        key=lambda item: (-item.points[-1].index, -item.geometry_score, -item.scale)
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


def scan_forming_abcd_pivots(
    pivots_by_scale: dict[int, tuple[Pivot, ...] | list[Pivot]],
    *,
    c_relative_tolerance: float = 0.03,
    max_forming: int = 100,
) -> tuple[ABCDFormingMatch, ...]:
    matches: list[ABCDFormingMatch] = []
    for scale, pivots in pivots_by_scale.items():
        points = forming_abc_points(pivots)
        if points is None:
            continue
        projection = project_forming_abcd(points, c_relative_tolerance=c_relative_tolerance)
        if projection is None:
            continue
        matches.append(
            ABCDFormingMatch(
                pattern_id="abcd",
                direction=projection.direction,
                state=PatternState.FORMING,
                scale=int(scale),
                points=projection.points,
                projection=projection,
                geometry_score=projection.geometry_score,
                conflict_key=tuple(point.index for point in projection.points),
            )
        )

    matches.sort(key=lambda item: (-item.points[-1].index, -item.geometry_score, -item.scale))
    out: list[ABCDFormingMatch] = []
    seen: set[tuple[PatternDirection, tuple[int, ...]]] = set()
    for item in matches:
        key = (item.direction, item.conflict_key)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return tuple(out[:max_forming])
