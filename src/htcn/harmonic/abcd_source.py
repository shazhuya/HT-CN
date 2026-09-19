from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .models import HarmonicPoint, PatternDirection
from .prz import PotentialReversalZone
from .ratios import leg_length


@dataclass(frozen=True, slots=True)
class ABCDSourcePRZ:
    price_low: float
    price_high: float
    component_names: tuple[str, ...]
    defining_component: str
    selection_method: str
    source_refs: tuple[str, ...]
    note: str

    @property
    def width(self) -> float:
        return self.price_high - self.price_low


@dataclass(frozen=True, slots=True)
class ABCDExecutionLayer:
    available: bool
    ratio: float | None
    price: float | None
    role: str
    source_refs: tuple[str, ...]
    note: str


ABCD_SOURCE_REFS = (
    "Volume One pp.45-58",
    "Volume Three pp.76-85",
)


def resolve_abcd_source_prz(prz: PotentialReversalZone) -> ABCDSourcePRZ | None:
    """Resolve standalone AB=CD Raw PRZ from its source-defined two measurements.

    Carney defines the exact/equivalent AB=CD completion as the most significant level and
    the reciprocal BC projection as the complementary measurement.  This helper does not use
    the HT-CN Ideal Core alias and does not add Volume Three BC layering to the Raw PRZ.
    """

    if prz.pattern_id != "abcd":
        return None
    defining = next((item for item in prz.components if item.name == "AB=CD x1"), None)
    reciprocal = next((item for item in prz.components if item.name == "BC reciprocal"), None)
    if defining is None or reciprocal is None:
        return None
    low = min(float(defining.price_low), float(reciprocal.price_low))
    high = max(float(defining.price_high), float(reciprocal.price_high))
    return ABCDSourcePRZ(
        price_low=low,
        price_high=high,
        component_names=(defining.name, reciprocal.name),
        defining_component=defining.name,
        selection_method="abcd_equivalent_plus_reciprocal_bc",
        source_refs=ABCD_SOURCE_REFS,
        note=(
            "Standalone AB=CD Raw PRZ = equivalent AB=CD completion plus the source-listed "
            "reciprocal BC projection. Volume Three BC layering is execution tolerance only."
        ),
    )


def with_abcd_source_prz(prz: PotentialReversalZone) -> PotentialReversalZone:
    """Return an auditable PRZ carrying standalone AB=CD Source-Raw-PRZ semantics."""

    source = resolve_abcd_source_prz(prz)
    if source is None:
        return prz
    return PotentialReversalZone(
        pattern_id=prz.pattern_id,
        direction=prz.direction,
        components=prz.components,
        source_prz_low=source.price_low,
        source_prz_high=source.price_high,
        source_prz_component_names=source.component_names,
        source_prz_defining_component=source.defining_component,
        source_prz_selection_method=source.selection_method,
        source_prz_source_refs=source.source_refs,
        source_prz_note=source.note,
        source_prz_reason=None,
    )


def _project_price(
    *,
    c_price: float,
    length: float,
    direction: PatternDirection,
) -> float:
    return c_price - length if direction is PatternDirection.BULLISH else c_price + length


def abcd_bc_layering_example(
    points: Sequence[HarmonicPoint],
    *,
    reciprocal_bc_target: float,
) -> ABCDExecutionLayer:
    """Expose only the explicitly illustrated 1.618 -> 2.0 BC layering case from Volume 3.

    This is deliberately not generalized to every reciprocal pair.  It is not identity and it
    is not part of Raw PRZ; it is a secondary execution-tolerance measurement.
    """

    refs = ("Volume Three pp.81-85",)
    if len(points) < 3 or abs(float(reciprocal_bc_target) - 1.618) > 1e-9:
        return ABCDExecutionLayer(
            available=False,
            ratio=None,
            price=None,
            role="not_source_cleared_for_this_reciprocal_pair",
            source_refs=refs,
            note=(
                "HT-CN does not invent a universal BC-layer mapping. The explicitly documented "
                "1.618 primary / 2.0 secondary example is the only frozen layer in M2.28."
            ),
        )
    a, b, c = points[:3]
    bc = leg_length(b.price, c.price)
    direction = PatternDirection.BULLISH if b.price < a.price else PatternDirection.BEARISH
    price = _project_price(c_price=c.price, length=bc * 2.0, direction=direction)
    return ABCDExecutionLayer(
        available=price > 0,
        ratio=2.0 if price > 0 else None,
        price=float(price) if price > 0 else None,
        role="execution_tolerance_only",
        source_refs=refs,
        note=(
            "Volume Three BC layering: with a 1.618 primary BC completion, 2.0 BC can gauge "
            "permissible price action beyond the ideal AB=CD completion. It does not redefine identity."
        ),
    )
