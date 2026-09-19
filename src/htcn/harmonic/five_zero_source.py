from __future__ import annotations

from dataclasses import dataclass

from .models import HarmonicPoint, PatternDirection
from .prz import PotentialReversalZone, PRZComponent
from .ratios import leg_length

_SOURCE_REFS = (
    "Volume Two Ch.3 pp.83-103: 50% BC retracement + Reciprocal AB=CD define the 5-0 PRZ",
    "Volume Three pp.129-138: 61.8 execution/stop refinement with internally inconsistent leg labels",
)


@dataclass(frozen=True, slots=True)
class FiveZeroExecutionRefinement:
    """Volume Three execution layer, deliberately outside the structural Raw PRZ.

    Volume Three alternates XA/AB labels around the 50%/61.8 drawings while the 5-0
    structural figures and market examples continue to show the D pullback on the B->C axis.
    HT-CN therefore preserves the source conflict instead of silently rewriting the book: the
    61.8 price below is an explicit BC-axis operational interpretation used only for research
    execution refinement until the source-label conflict can be resolved more strongly.
    """

    price_618: float
    preferred_execution_price: float
    preferred_execution_basis: str
    stop_reference_price: float
    execution_zone_low: float
    execution_zone_high: float
    projection_basis: str = "htcn_bc_axis_interpretation_of_v3_61_8"
    source_label_status: str = "conflicted_xa_ab_labels_vs_bc_axis_figures"
    raw_prz_membership: bool = False
    identity_membership: bool = False
    source_note: str = (
        "Volume Two fixes structural completion at 50% BC + Reciprocal AB=CD. "
        "Volume Three adds a 61.8 make-or-break/stop refinement, but its prose/PRZ figures "
        "alternate XA and AB labels while the structural figures/cases preserve the B-C pullback geometry."
    )


@dataclass(frozen=True, slots=True)
class FiveZeroSourceContract:
    direction: PatternDirection
    price_50_bc: float
    reciprocal_abcd_price: float
    reciprocal_relation: str
    source_prz_low: float
    source_prz_high: float
    execution_refinement: FiveZeroExecutionRefinement
    prz: PotentialReversalZone

    @property
    def source_prz_width(self) -> float:
        return self.source_prz_high - self.source_prz_low

    @property
    def legacy_reciprocal_inside_50_618_band(self) -> bool:
        low, high = sorted((self.price_50_bc, self.execution_refinement.price_618))
        return low <= self.reciprocal_abcd_price <= high

    def contains_raw_prz(self, price: float) -> bool:
        return _contains(float(price), self.source_prz_low, self.source_prz_high)

    def contains_execution_envelope(self, price: float) -> bool:
        return _contains(
            float(price),
            self.execution_refinement.execution_zone_low,
            self.execution_refinement.execution_zone_high,
        )

    def classify_completion(self, price: float) -> str:
        value = float(price)
        if self.contains_raw_prz(value):
            return "source_raw_prz_test"
        if self.reciprocal_relation == "beyond_50_toward_618" and self.contains_execution_envelope(value):
            return "v3_618_execution_refinement"
        return "outside_reconciled_completion_zone"

    def distance_to_valid_completion(self, price: float) -> float:
        value = float(price)
        if self.classify_completion(value) != "outside_reconciled_completion_zone":
            return 0.0
        low = self.execution_refinement.execution_zone_low
        high = self.execution_refinement.execution_zone_high
        return min(abs(value - low), abs(value - high))


def _contains(value: float, low: float, high: float) -> bool:
    eps = 1e-12 * max(1.0, abs(value), abs(low), abs(high))
    return low - eps <= value <= high + eps


def _direction(points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint]) -> PatternDirection:
    x, a, _, _ = points
    if a.price == x.price:
        raise ValueError("5-0 X and A cannot have the same price")
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


def _relation(
    direction: PatternDirection,
    *,
    reciprocal: float,
    price_50: float,
) -> str:
    eps = 1e-12 * max(1.0, abs(reciprocal), abs(price_50))
    if abs(reciprocal - price_50) <= eps:
        return "at_50"
    if direction is PatternDirection.BULLISH:
        return "before_50" if reciprocal > price_50 else "beyond_50_toward_618"
    return "before_50" if reciprocal < price_50 else "beyond_50_toward_618"


def build_five_zero_source_contract(
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
) -> FiveZeroSourceContract:
    """Build the reconciled 5-0 source contract from signal-visible X/A/B/C geometry.

    Structural authority is Volume Two: the Raw PRZ has exactly two members, the 50% BC
    retracement and Reciprocal AB=CD.  The Volume Three 61.8 level is retained as a separate
    execution/stop refinement and never becomes a Raw PRZ or identity member.
    """

    _, a, b, c = points
    direction = _direction(points)
    ab = leg_length(a.price, b.price)
    bc = leg_length(b.price, c.price)
    if ab <= 0 or bc <= 0:
        raise ValueError("5-0 AB and BC spans must be positive")

    price_50 = _project_from_c(c_price=c.price, length=bc, ratio=0.50, direction=direction)
    reciprocal = _project_from_c(c_price=c.price, length=ab, ratio=1.0, direction=direction)
    price_618 = _project_from_c(c_price=c.price, length=bc, ratio=0.618, direction=direction)
    relation = _relation(direction, reciprocal=reciprocal, price_50=price_50)

    source_low, source_high = sorted((price_50, reciprocal))
    if relation == "beyond_50_toward_618":
        execution_prices = sorted((source_low, source_high, price_618))
        execution_low, execution_high = execution_prices[0], execution_prices[-1]
        preferred_price = price_618
        preferred_basis = "v3_61_8_optimal_entry_after_reciprocal_beyond_50"
    elif relation == "before_50":
        execution_low, execution_high = source_low, source_high
        preferred_price = reciprocal
        preferred_basis = "v3_immediate_reciprocal_before_50"
    else:
        execution_low, execution_high = source_low, source_high
        preferred_price = price_50
        preferred_basis = "source_50_and_reciprocal_converge"

    components = (
        _point_component("BC 50% structural completion", price_50, 0.50),
        _point_component("Reciprocal AB=CD x1", reciprocal, 1.0),
        _point_component("BC 61.8% V3 execution boundary", price_618, 0.618),
    )
    prz = PotentialReversalZone(
        pattern_id="five_zero",
        direction=direction,
        components=components,
        source_prz_low=source_low,
        source_prz_high=source_high,
        source_prz_component_names=(
            "BC 50% structural completion",
            "Reciprocal AB=CD x1",
        ),
        source_prz_defining_component="BC 50% structural completion",
        source_prz_selection_method="volume2_50_bc_plus_reciprocal_abcd",
        source_prz_source_refs=_SOURCE_REFS,
        source_prz_note=(
            "Volume Two defines the 5-0 Raw PRZ with exactly two measurements: 50% BC "
            "retracement and Reciprocal AB=CD. The stored 61.8 component is audit/execution-only."
        ),
    )
    refinement = FiveZeroExecutionRefinement(
        price_618=price_618,
        preferred_execution_price=preferred_price,
        preferred_execution_basis=preferred_basis,
        stop_reference_price=price_618,
        execution_zone_low=execution_low,
        execution_zone_high=execution_high,
    )
    return FiveZeroSourceContract(
        direction=direction,
        price_50_bc=price_50,
        reciprocal_abcd_price=reciprocal,
        reciprocal_relation=relation,
        source_prz_low=source_low,
        source_prz_high=source_high,
        execution_refinement=refinement,
        prz=prz,
    )
