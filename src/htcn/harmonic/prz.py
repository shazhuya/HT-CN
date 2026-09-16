from __future__ import annotations

from dataclasses import dataclass

from .models import HarmonicPoint, PatternDirection
from .rules import PatternRule, RatioConstraint


_PRICE_FLOOR = 1e-9


@dataclass(frozen=True, slots=True)
class PRZComponent:
    """One auditable price component that contributes to a PRZ.

    A component can be a single target or a bounded target interval. We keep the
    originating measurement and ratio bounds so the UI can explain *why* a zone exists
    instead of rendering an opaque rectangle.
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

    @property
    def midpoint(self) -> float:
        return (self.price_low + self.price_high) / 2.0

    def nearest_price(self, target: float) -> float:
        return min(max(target, self.price_low), self.price_high)


@dataclass(frozen=True, slots=True)
class PotentialReversalZone:
    pattern_id: str
    direction: PatternDirection
    components: tuple[PRZComponent, ...]

    def __post_init__(self) -> None:
        if not self.components:
            raise ValueError("PRZ must contain at least one component")

    @property
    def component_price_low(self) -> float:
        """Outer audit envelope across every physically reachable component/variant."""
        return min(component.price_low for component in self.components)

    @property
    def component_price_high(self) -> float:
        """Outer audit envelope across every physically reachable component/variant."""
        return max(component.price_high for component in self.components)

    @property
    def convergence_prices(self) -> tuple[float, ...]:
        """Representative prices that actually form the projected reversal cluster.

        Standard XABCD patterns anchor on the defining XA completion and select the
        complementary BC / AB=CD measurements that converge most closely with it.

        Shark is structurally different: its PRZ is the *overlap* of the 0B 0.886-1.13
        completion range and the 1.618-2.24 AB impulse range. Returning that intersection
        explicitly prevents the dedicated Shark schema from being collapsed to an opaque
        midpoint by the standard M/W convergence heuristic.
        """
        if self.pattern_id == "shark" and len(self.components) >= 2:
            overlap_low = max(component.price_low for component in self.components)
            overlap_high = min(component.price_high for component in self.components)
            if overlap_low <= overlap_high:
                return (overlap_low, overlap_high)

        xa = [component for component in self.components if component.name == "XA completion"]
        anchor = xa[0].midpoint if xa else self.components[0].midpoint
        prices: list[float] = [anchor]

        non_abcd = [
            component
            for component in self.components
            if component.name != "XA completion" and not component.name.startswith("AB=CD")
        ]
        prices.extend(component.nearest_price(anchor) for component in non_abcd)

        abcd = [component for component in self.components if component.name.startswith("AB=CD")]
        if abcd:
            best = min(abcd, key=lambda component: abs(component.midpoint - anchor))
            prices.append(best.midpoint)

        return tuple(prices)

    @property
    def price_low(self) -> float:
        return min(self.convergence_prices)

    @property
    def price_high(self) -> float:
        return max(self.convergence_prices)

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
    raw_low = min(p1, p2)
    raw_high = max(p1, p2)
    if raw_high <= 0:
        raise ValueError(f"{name} projects entirely outside the positive-price domain")
    return PRZComponent(
        name=name,
        price_low=max(raw_low, _PRICE_FLOOR),
        price_high=raw_high,
        ratio_low=constraint.minimum,
        ratio_high=constraint.maximum,
    )


def build_xabcd_prz(
    rule: PatternRule,
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
) -> PotentialReversalZone:
    """Project an auditable forming PRZ from X/A/B/C.

    This function intentionally supports only executable standard XABCD rules. Shark and
    5-0 use different segment semantics and have dedicated projectors.
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
        if price <= 0:
            continue
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
        raise ValueError(f"rule {rule.pattern_id!r} has no reachable XABCD PRZ components")

    return PotentialReversalZone(
        pattern_id=rule.pattern_id,
        direction=direction,
        components=tuple(components),
    )
