from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True, slots=True)
class RatioConstraint:
    """Explicit ratio band used by a pattern rule.

    `minimum`/`maximum` are the canonical geometry. Optional tolerances are stored
    separately so strict identity and permissive real-time matching never become the
    same operation by accident.
    """

    minimum: float
    maximum: float
    ideal: float | None = None
    tolerance_below: float = 0.0
    tolerance_above: float = 0.0

    def __post_init__(self) -> None:
        if self.minimum < 0 or self.maximum < 0:
            raise ValueError("ratio bounds must be non-negative")
        if self.minimum > self.maximum:
            raise ValueError("minimum must be <= maximum")
        if self.tolerance_below < 0 or self.tolerance_above < 0:
            raise ValueError("tolerances must be non-negative")
        if self.ideal is not None and not (self.minimum <= self.ideal <= self.maximum):
            raise ValueError("ideal must lie inside the canonical band")

    def contains(self, value: float, *, include_tolerance: bool = False) -> bool:
        low = self.minimum
        high = self.maximum
        if include_tolerance:
            low -= self.tolerance_below
            high += self.tolerance_above
        return low <= float(value) <= high


@dataclass(frozen=True, slots=True)
class PatternRule:
    pattern_id: str
    schema: str
    constraints: Mapping[str, RatioConstraint] = field(default_factory=dict)
    # These are preferred/complementary AB=CD variants used for PRZ projection and
    # geometry quality. They are NOT silently promoted to exact hard identity tests.
    abcd_types: tuple[float, ...] = ()
    # Carney frequently describes an "AB=CD minimum" rather than an exact CD/AB ratio.
    # When set, completed geometry must at least reach this CD/AB length ratio.
    abcd_minimum: float | None = None
    executable_identity: bool = True
    source_conflict: bool = False
    source_note: str = ""
    implementation_note: str = ""

    def __post_init__(self) -> None:
        if self.abcd_minimum is not None and self.abcd_minimum <= 0:
            raise ValueError("abcd_minimum must be positive")


CARNEY_RULES: dict[str, PatternRule] = {
    "gartley": PatternRule(
        pattern_id="gartley",
        schema="XABCD",
        constraints={
            "b_xa": RatioConstraint(0.618, 0.618, ideal=0.618, tolerance_below=0.03, tolerance_above=0.03),
            "bc_projection": RatioConstraint(1.13, 1.618),
            "d_xa": RatioConstraint(0.786, 0.786, ideal=0.786),
        },
        abcd_types=(1.0, 1.27),
        abcd_minimum=1.0,
        source_note="Volume One Gartley chapter; Volume Three p.92 specification and B-point tolerance classification.",
        implementation_note="AB=CD is required as a completed minimum/PRZ component; preferred variants contribute to quality but are not given an invented hard tolerance.",
    ),
    "bat": PatternRule(
        pattern_id="bat",
        schema="XABCD",
        constraints={
            "b_xa": RatioConstraint(0.382, 0.50, ideal=0.50, tolerance_above=0.05),
            "bc_projection": RatioConstraint(1.618, 2.618),
            "d_xa": RatioConstraint(0.886, 0.886, ideal=0.886),
        },
        abcd_types=(1.0, 1.27, 1.618),
        abcd_minimum=1.0,
        source_note="Volume One Bat chapter; Volume Three p.98 specification. V3 calls for a minimum AB=CD, typically 1.27AB=CD.",
    ),
    "alternate_bat": PatternRule(
        pattern_id="alternate_bat",
        schema="XABCD",
        constraints={
            "b_xa": RatioConstraint(0.0, 0.382, ideal=0.382),
            "bc_projection": RatioConstraint(2.0, 3.618),
            "d_xa": RatioConstraint(0.886, 1.13),
        },
        abcd_types=(1.618,),
        abcd_minimum=None,
        source_conflict=True,
        source_note="Volume Two Alternate Bat chapter vs. Volume Three p.101 specification.",
        implementation_note=(
            "Volume Two explicitly says AB=CD is not included in this setup, while Volume Three lists 1.618AB=CD. "
            "Therefore AB=CD remains an auditable quality/PRZ reference, not a hard identity gate."
        ),
    ),
    "butterfly": PatternRule(
        pattern_id="butterfly",
        schema="XABCD",
        constraints={
            "b_xa": RatioConstraint(0.786, 0.786, ideal=0.786, tolerance_below=0.03, tolerance_above=0.03),
            "bc_projection": RatioConstraint(1.618, 2.24),
            "d_xa": RatioConstraint(1.27, 1.27, ideal=1.27),
        },
        abcd_types=(1.0, 1.27),
        abcd_minimum=1.0,
        source_note="Volume One Ideal/Perfect Butterfly chapters; Volume Three p.113 specification. Equivalent AB=CD is a minimum; 1.27 alternate is common/preferred.",
    ),
    "crab": PatternRule(
        pattern_id="crab",
        schema="XABCD",
        constraints={
            "b_xa": RatioConstraint(0.382, 0.618),
            "bc_projection": RatioConstraint(2.618, 3.618),
            "d_xa": RatioConstraint(1.618, 1.618, ideal=1.618),
        },
        abcd_types=(1.0, 1.27, 1.618),
        abcd_minimum=1.0,
        source_note="Volume One Crab chapter; Volume Three p.104 specification.",
        implementation_note="Volume One describes minimum AB=CD completion; alternate 1.27/1.618 are common but not exact hard identity ratios.",
    ),
    "deep_crab": PatternRule(
        pattern_id="deep_crab",
        schema="XABCD",
        constraints={
            "b_xa": RatioConstraint(0.886, 0.886, ideal=0.886, tolerance_above=0.05),
            "bc_projection": RatioConstraint(2.0, 3.618),
            "d_xa": RatioConstraint(1.618, 1.618, ideal=1.618),
        },
        abcd_types=(1.0, 1.27, 1.618),
        abcd_minimum=1.0,
        source_note="Volume One Deep Crab chapter; Volume Three p.107 specification.",
    ),
    "abcd": PatternRule(
        pattern_id="abcd",
        schema="ABCD",
        constraints={"c_ab": RatioConstraint(0.382, 0.886)},
        abcd_types=(1.0, 1.13, 1.27, 1.41, 1.618, 2.0),
        source_note="Volume One Ch.4 reciprocal table; Volume Three pp.76-80 AB=CD and reciprocal-ratio review.",
        implementation_note="Reciprocal C/AB -> BC projection mapping is frozen separately in ratios.RECIPROCAL_ABCD.",
    ),
    "shark": PatternRule(
        pattern_id="shark",
        schema="0XABC",
        constraints={
            "a_0x": RatioConstraint(0.382, 0.618),
            "extreme_impulse": RatioConstraint(1.618, 2.24),
            "completion_0b": RatioConstraint(0.886, 1.13),
        },
        executable_identity=False,
        source_note="Volume Three pp.116-129 advanced Shark specification.",
        implementation_note="Requires dedicated 0XABC evaluator; do not force into XABCD code paths.",
    ),
    "five_zero": PatternRule(
        pattern_id="five_zero",
        schema="0XABCD",
        constraints={
            "extreme_impulse": RatioConstraint(1.618, 2.24),
            "completion_zone": RatioConstraint(0.50, 0.618),
        },
        executable_identity=False,
        source_conflict=True,
        source_note="Volume Two 5-0 chapter plus Volume Three pp.129-136 refinement.",
        implementation_note=(
            "Figure-level reconciliation is required before executable identity: Volume Two "
            "describes 50% BC retracement + Reciprocal AB=CD, while Volume Three uses 50%/61.8% "
            "completion and stop language with differing segment wording."
        ),
    ),
}
