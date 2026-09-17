from __future__ import annotations

from dataclasses import dataclass

from .models import HarmonicPoint, PatternDirection
from .prz import PRZComponent, PotentialReversalZone
from .ratios import leg_length


_SOURCE_REFS = (
    "Volume Three pp.119-129: Shark 0B 0.886 minimum, 1.13 maximum/stop limit",
    "Volume Three pp.120-127: 1.618-2.24 AB Extreme Harmonic Impulse aligns with 0B retest",
    "Volume Three p.127: USD/CAD example describes alignment of minimum measures as preferred completion area",
)


@dataclass(frozen=True, slots=True)
class SharkSourceContract:
    direction: PatternDirection
    price_886_0b: float
    price_100_0b: float
    price_113_0b: float
    price_1618_ab: float
    price_224_ab: float
    source_prz_low: float | None
    source_prz_high: float | None
    stop_reference_price: float
    prz: PotentialReversalZone

    @property
    def has_source_prz(self) -> bool:
        return self.source_prz_low is not None and self.source_prz_high is not None

    def contains_source_prz(self, price: float) -> bool:
        if not self.has_source_prz:
            return False
        value = float(price)
        low = float(self.source_prz_low)
        high = float(self.source_prz_high)
        eps = 1e-12 * max(1.0, abs(value), abs(low), abs(high))
        return low - eps <= value <= high + eps


def _direction(
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
) -> PatternDirection:
    zero, x, _, _ = points
    if x.price == zero.price:
        raise ValueError("Shark 0 and X cannot have the same price")
    return PatternDirection.BULLISH if x.price > zero.price else PatternDirection.BEARISH


def _project_from_b(
    *,
    b_price: float,
    length: float,
    ratio: float,
    direction: PatternDirection,
) -> float:
    return b_price - ratio * length if direction is PatternDirection.BULLISH else b_price + ratio * length


def _range_component(
    *,
    name: str,
    p1: float,
    p2: float,
    ratio_low: float,
    ratio_high: float,
) -> PRZComponent:
    low, high = sorted((float(p1), float(p2)))
    if low <= 0:
        raise ValueError(f"{name} projects outside the positive-price domain")
    return PRZComponent(
        name=name,
        price_low=low,
        price_high=high,
        ratio_low=ratio_low,
        ratio_high=ratio_high,
    )


def build_shark_source_contract(
    points: tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint],
) -> SharkSourceContract:
    """Build the Volume Three Shark Source Raw PRZ from signal-visible 0/X/A/B geometry.

    Carney describes two source corridors at completion:

    * the 0B retest corridor begins at 0.886, usually focuses around 1.0, and must not
      exceed 1.13; and
    * the AB Extreme Harmonic Impulse must be at least 1.618 and can extend to 2.24.

    The source text and market examples describe the preferred completion area as the
    *alignment* of those measurements.  HT-CN therefore freezes the Raw PRZ as the
    geometric overlap of the two published source corridors.  This is intentionally
    separate from the generic ``ideal_core`` engineering alias.
    """

    zero, _, a, b = points
    direction = _direction(points)
    ob = leg_length(zero.price, b.price)
    ab = leg_length(a.price, b.price)
    if min(ob, ab) <= 0:
        raise ValueError("Shark 0B and AB spans must be positive")

    price_886 = _project_from_b(b_price=b.price, length=ob, ratio=0.886, direction=direction)
    price_100 = _project_from_b(b_price=b.price, length=ob, ratio=1.0, direction=direction)
    price_113 = _project_from_b(b_price=b.price, length=ob, ratio=1.13, direction=direction)
    price_1618 = _project_from_b(b_price=b.price, length=ab, ratio=1.618, direction=direction)
    price_224 = _project_from_b(b_price=b.price, length=ab, ratio=2.24, direction=direction)

    ob_component = _range_component(
        name="0B 0.886-1.13 completion corridor",
        p1=price_886,
        p2=price_113,
        ratio_low=0.886,
        ratio_high=1.13,
    )
    impulse_component = _range_component(
        name="AB impulse 1.618-2.24 completion corridor",
        p1=price_1618,
        p2=price_224,
        ratio_low=1.618,
        ratio_high=2.24,
    )

    overlap_low = max(ob_component.price_low, impulse_component.price_low)
    overlap_high = min(ob_component.price_high, impulse_component.price_high)
    has_overlap = overlap_low <= overlap_high
    source_low = overlap_low if has_overlap else None
    source_high = overlap_high if has_overlap else None

    prz = PotentialReversalZone(
        pattern_id="shark",
        direction=direction,
        components=(ob_component, impulse_component),
        source_prz_low=source_low,
        source_prz_high=source_high,
        source_prz_component_names=(
            "0B 0.886-1.13 completion corridor",
            "AB impulse 1.618-2.24 completion corridor",
        ) if has_overlap else (),
        source_prz_defining_component="0B 0.886-1.13 completion corridor" if has_overlap else None,
        source_prz_selection_method=(
            "volume3_shark_overlap_0b_886_113_with_ab_impulse_1618_224"
            if has_overlap
            else None
        ),
        source_prz_source_refs=_SOURCE_REFS if has_overlap else (),
        source_prz_note=(
            "Volume Three treats 0.886 0B as the minimum retest, 1.13 0B as the maximum "
            "completion/stop limit, and 1.618-2.24 AB as the Extreme Harmonic Impulse. "
            "The Raw PRZ is the overlap/alignment of those published source corridors."
            if has_overlap
            else "Published Shark source corridors do not overlap for this 0/X/A/B geometry."
        ),
        source_prz_reason=None if has_overlap else "source_components_do_not_converge",
    )

    return SharkSourceContract(
        direction=direction,
        price_886_0b=price_886,
        price_100_0b=price_100,
        price_113_0b=price_113,
        price_1618_ab=price_1618,
        price_224_ab=price_224,
        source_prz_low=source_low,
        source_prz_high=source_high,
        stop_reference_price=price_113,
        prz=prz,
    )
