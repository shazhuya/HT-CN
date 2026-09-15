from __future__ import annotations

from dataclasses import dataclass

from .models import HarmonicPoint, PatternDirection
from .rules import PatternRule, RatioConstraint


@dataclass(frozen=True, slots=True)
class PRZComponent:
    """One auditable price component that contributes to a PRZ.

    A component can be a single target or a bounded target interval.  We keep the
    originating measurement and ratio bounds so the UI can later explain *why* a
    zone exists instead of rendering an opaque rectangle.
    """

    name: str
    price_low: float
    price_high: float
    ratio_low: float
    ratio_high: float

    def __post_init__(self) -> None:
        if self.price_low <= 0 or self.price_high <= 0:
            raise ValueError("PRZ prices must be positive")
        if self.price_low > self.price_high:
            raise ValueError("price_low must be <= price_high")


@dataclass(frozen=True, slots=True)
class PotentialReversalZone:
    pattern_id: str
    direction: PatternDirection
    components: tuple[PRZComponent, ...]

    @property
    def price_low(self) -> float:
        return min(component.price_low for component in self.components)

    @property
    def price_high(self) -> float:
        return max(component.price_high for component in self.components)

    @property
    def width(self) -> float:
        return self.price_high - self.price_low


def _direction_from_xa(x: HarmonicPoint, a: HarmonicPoint) -> PatternDirection:
    if a.price == x.price:
        raise ValueError("X and A cannot have the same price")
    return PatternDirection.BULLISH if a.price > x.price else PatternDirection.BEARISH


def _project_xa_completion(
    x: HarmonicPoint,
    a: HarmonicPoint,
    ratio: float,
    direction: PatternDirection,
) -> float:
    span = abs(a.price - x.price)
    if direction is PatternDirection.BULLISH:
        return a.price - ratio * span
    return a.price + ratio * span


def _project_bc_completion(
    b: HarmonicPoint,
    c: HarmonicPoint,
    ratio: float,
    direction: PatternDirection,
) -> float:
    span = abs(c.price - b.price)
    if direction is PatternDirection.BULLISH:
        return c.price - ratio * span
    return c.price + ratio * span


def _project_abcd_completion(
    a: HarmonicPoint,
    b: HarmonicPoint,
    c: HarmonicPoint,
    ratio: float,
    direction: PatternDirection,
) -> float:
    ab = abs(b.price - a.price)
    if direction is PatternDirection.BULLISH:
        return c.price - ratio * ab
    return c.price + ratio * ab


def _component_from_constraint(
    *,
    name: str,
    constraint: RatioConstraint,
    projector,
) -> PRZComponent:
    p1 = float(projector(constraint.minimum))
    p2 = float(projector(constraint.maximum))
    return PRZComponent(
        name=name,
        price_low=min(p1, p2),
        price_high=max(p1, p2),
        ratio_low=constraint.minimum,
        ratio_high=constraint.maximum,
    )


def build_xabcd_prz(
    rule: PatternRule,
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
) -> PotentialReversalZone:
    """Project an auditable forming PRZ from X/A/B/C.

    This function intentionally supports only executable XABCD rules.  Shark and
    5-0 use different segment semantics and must have dedicated projectors instead
    of being coerced into this path.
    """

    if rule.schema != "XABCD":
        raise ValueError(f"rule {rule.pattern_id!r} is not XABCD")
    if not rule.executable_identity:
        raise ValueError(f"rule {rule.pattern_id!r} is not executable yet")

    x, a, b, c = points
    if tuple(point.label for point in points) != ("X", "A", "B", "C"):
        raise ValueError("points must be labelled X, A, B, C")
    if not (x.index < a.index < b.index < c.index):
        raise ValueError("X/A/B/C indices must be strictly increasing")

    direction = _direction_from_xa(x, a)
    components: list[PRZComponent] = []

    d_xa = rule.constraints.get("d_xa")
    if d_xa is not None:
        components.append(
            _component_from_constraint(
                name="XA completion",
                constraint=d_xa,
                projector=lambda ratio: _project_xa_completion(x, a, ratio, direction),
            )
        )

    bc = rule.constraints.get("bc_projection")
    if bc is not None:
        components.append(
            _component_from_constraint(
                name="BC projection",
                constraint=bc,
                projector=lambda ratio: _project_bc_completion(b, c, ratio, direction),
            )
        )

    for ratio in rule.abcd_types:
        price = _project_abcd_completion(a, b, c, ratio, direction)
        components.append(
            PRZComponent(
                name=f"AB=CD x{ratio:g}",
                price_low=price,
                price_high=price,
                ratio_low=ratio,
                ratio_high=ratio,
            )
        )

    if not components:
        raise ValueError(f"rule {rule.pattern_id!r} has no XABCD PRZ components")
    if any(component.price_low <= 0 for component in components):
        raise ValueError("projected PRZ contains non-positive price; candidate geometry is invalid")

    return PotentialReversalZone(
        pattern_id=rule.pattern_id,
        direction=direction,
        components=tuple(components),
    )
