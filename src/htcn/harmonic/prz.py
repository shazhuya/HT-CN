from __future__ import annotations

from dataclasses import dataclass

from .models import HarmonicPoint, PatternDirection
from .rules import PatternRule, RatioConstraint
from .source_prz import select_source_prz

_PRICE_FLOOR = 1e-9


@dataclass(frozen=True, slots=True)
class PRZComponent:
    """One auditable price component that contributes to a projected reversal area."""

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
    """Auditable harmonic measurements plus explicitly separated PRZ semantics.

    ``component_envelope_*`` is the outer envelope of every stored measurement/variant and
    is audit data only. ``ideal_core_*`` is HT-CN's generic narrow convergence selection.
    Neither is automatically the source Raw PRZ.

    ``source_prz_low/high`` are populated only by a pattern-specific frozen Source-PRZ
    profile.  The selected component names and source references remain attached so the API
    can explain why those bounds exist.  Unsupported or source-conflict patterns fail closed.
    """

    pattern_id: str
    direction: PatternDirection
    components: tuple[PRZComponent, ...]
    source_prz_low: float | None = None
    source_prz_high: float | None = None
    source_prz_component_names: tuple[str, ...] = ()
    source_prz_defining_component: str | None = None
    source_prz_selection_method: str | None = None
    source_prz_source_refs: tuple[str, ...] = ()
    source_prz_note: str = ""
    source_prz_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.components:
            raise ValueError("PRZ must contain at least one component")
        if (self.source_prz_low is None) != (self.source_prz_high is None):
            raise ValueError("source PRZ bounds must be both set or both omitted")
        if self.source_prz_low is not None and self.source_prz_high is not None:
            if self.source_prz_low <= 0 or self.source_prz_high <= 0:
                raise ValueError("source PRZ prices must be positive")
            if self.source_prz_low > self.source_prz_high:
                raise ValueError("source_prz_low must be <= source_prz_high")
        known_names = {component.name for component in self.components}
        unknown = set(self.source_prz_component_names).difference(known_names)
        if unknown:
            raise ValueError(f"source PRZ references unknown components: {sorted(unknown)}")
        if self.has_source_prz and not self.source_prz_component_names:
            # Compatibility: historical/tests may construct explicit source bounds directly.
            # Runtime XABCD builders always provide auditable source component names.
            pass

    @property
    def has_source_prz(self) -> bool:
        return self.source_prz_low is not None and self.source_prz_high is not None

    @property
    def source_prz_status(self) -> str:
        if self.has_source_prz:
            return "frozen"
        if self.source_prz_reason == "source_conflict":
            return "source_conflict_fail_closed"
        return "unresolved_fail_closed"

    @property
    def component_envelope_low(self) -> float:
        return min(component.price_low for component in self.components)

    @property
    def component_envelope_high(self) -> float:
        return max(component.price_high for component in self.components)

    @property
    def component_price_low(self) -> float:
        return self.component_envelope_low

    @property
    def component_price_high(self) -> float:
        return self.component_envelope_high

    @property
    def convergence_prices(self) -> tuple[float, ...]:
        """Representative measurements that form the current HT-CN ideal core.

        This remains a generic engineering layer and is intentionally independent from the
        pattern-specific Source-PRZ selector.  The two layers may happen to select the same
        prices in an ideal example, but they do not share semantics or authority.
        """
        if self.pattern_id == "shark" and len(self.components) >= 2:
            overlap_low = max(component.price_low for component in self.components)
            overlap_high = min(component.price_high for component in self.components)
            if overlap_low <= overlap_high:
                return (overlap_low, overlap_high)

        xa = [component for component in self.components if component.name == "XA completion"]
        anchor = xa[0].midpoint if xa else self.components[0].midpoint
        prices: list[float] = [anchor]

        bc_components = [
            component for component in self.components if component.name.startswith("BC projection")
        ]
        if bc_components:
            best_bc = min(bc_components, key=lambda component: abs(component.midpoint - anchor))
            prices.append(best_bc.midpoint)

        abcd = [component for component in self.components if component.name.startswith("AB=CD")]
        if abcd:
            best_abcd = min(abcd, key=lambda component: abs(component.midpoint - anchor))
            prices.append(best_abcd.midpoint)

        other = [
            component
            for component in self.components
            if component.name != "XA completion"
            and not component.name.startswith("BC projection")
            and not component.name.startswith("AB=CD")
        ]
        prices.extend(component.nearest_price(anchor) for component in other)

        return tuple(prices)

    @property
    def ideal_core_low(self) -> float:
        return min(self.convergence_prices)

    @property
    def ideal_core_high(self) -> float:
        return max(self.convergence_prices)

    @property
    def ideal_core_width(self) -> float:
        return self.ideal_core_high - self.ideal_core_low

    @property
    def price_low(self) -> float:
        """Legacy alias for ``ideal_core_low``; not the full/raw source PRZ."""
        return self.ideal_core_low

    @property
    def price_high(self) -> float:
        """Legacy alias for ``ideal_core_high``; not the full/raw source PRZ."""
        return self.ideal_core_high

    @property
    def width(self) -> float:
        return self.ideal_core_width


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


def _point_component(*, name: str, ratio: float, price: float) -> PRZComponent | None:
    if price <= 0:
        return None
    return PRZComponent(
        name=name,
        price_low=float(price),
        price_high=float(price),
        ratio_low=float(ratio),
        ratio_high=float(ratio),
    )


def build_xabcd_prz(
    rule: PatternRule,
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
) -> PotentialReversalZone:
    """Project auditable XABCD measurements from X/A/B/C and select Source PRZ.

    Source-listed discrete BC ratios and AB=CD variants are all retained as audit
    components.  A separate pattern-specific Source-PRZ profile then selects the subset
    that forms the executable Raw PRZ.  No selector may fall back to the all-component
    envelope or the HT-CN ideal core.
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

    bc_targets = rule.harmonic_targets.get("bc_projection", ())
    if bc_targets:
        for ratio in bc_targets:
            component = _point_component(
                name=f"BC projection x{ratio:g}",
                ratio=ratio,
                price=_project_bc_completion(b, c, ratio, direction),
            )
            if component is not None:
                components.append(component)
    else:
        # Fallback exists only for a rule whose source has not yet been encoded as a
        # discrete family. Standard production XABCD rules should not use this branch.
        bc = rule.constraints.get("bc_projection")
        if bc is not None:
            components.append(
                _component_from_constraint(
                    name="BC projection envelope",
                    constraint=bc,
                    projector=lambda ratio: _project_bc_completion(b, c, ratio, direction),
                )
            )

    for ratio in rule.abcd_types:
        component = _point_component(
            name=f"AB=CD x{ratio:g}",
            ratio=ratio,
            price=_project_abcd_completion(a, b, c, ratio, direction),
        )
        if component is not None:
            components.append(component)

    if not components:
        raise ValueError(f"rule {rule.pattern_id!r} has no reachable XABCD PRZ components")

    selection = select_source_prz(rule.pattern_id, components)
    return PotentialReversalZone(
        pattern_id=rule.pattern_id,
        direction=direction,
        components=tuple(components),
        source_prz_low=selection.price_low if selection.available else None,
        source_prz_high=selection.price_high if selection.available else None,
        source_prz_component_names=selection.component_names,
        source_prz_defining_component=selection.defining_component,
        source_prz_selection_method=selection.selection_method,
        source_prz_source_refs=selection.source_refs,
        source_prz_note=selection.note,
        source_prz_reason=selection.reason,
    )
