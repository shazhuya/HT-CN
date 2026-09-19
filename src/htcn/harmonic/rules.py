from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

_NUMERIC_EPSILON = 1e-12

# Volume One explicitly defines the finite ratio family used to identify precise harmonic
# structures. A broad min/max band is still useful as a fast structural guard, but values
# inside that band are not automatically harmonic merely because they are numerically between
# two valid ratios.
HARMONIC_RETRACEMENT_FAMILY: tuple[float, ...] = (0.382, 0.50, 0.618, 0.707, 0.786, 0.886)


@dataclass(frozen=True, slots=True)
class RatioConstraint:
    """Explicit ratio band used by a pattern rule.

    `minimum`/`maximum` are the canonical structural envelope. Optional source-backed
    tolerances are stored separately so strict identity and permissive matching never become
    the same operation by accident. A machine-precision epsilon is always used at inclusive
    boundaries; this is numerical hygiene, not a trading tolerance.
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
        numeric_pad = _NUMERIC_EPSILON * max(1.0, abs(low), abs(high), abs(float(value)))
        return (low - numeric_pad) <= float(value) <= (high + numeric_pad)


@dataclass(frozen=True, slots=True)
class PatternRule:
    pattern_id: str
    schema: str
    constraints: Mapping[str, RatioConstraint] = field(default_factory=dict)
    # Discrete source harmonic families. The evaluator may apply an explicit HT-CN
    # operational matching tolerance around these source-listed values, but it must never
    # interpret the entire min/max envelope as a continuous harmonic family.
    harmonic_targets: Mapping[str, tuple[float, ...]] = field(default_factory=dict)
    # Preferred/complementary AB=CD variants used for PRZ projection and geometry quality.
    # They are NOT silently promoted to exact hard identity tests.
    abcd_types: tuple[float, ...] = ()
    # Carney frequently describes an "AB=CD minimum" rather than an exact CD/AB ratio.
    # When set, completed geometry must at least reach this CD/AB length ratio.
    abcd_minimum: float | None = None
    # True means the generic standard XABCD evaluator can execute this registry row.
    # Dedicated schemas can be fully executable in their own module while remaining False here.
    executable_identity: bool = True
    source_conflict: bool = False
    source_note: str = ""
    implementation_note: str = ""

    def __post_init__(self) -> None:
        if self.abcd_minimum is not None and self.abcd_minimum <= 0:
            raise ValueError("abcd_minimum must be positive")
        for name, targets in self.harmonic_targets.items():
            if not targets:
                raise ValueError(f"harmonic target family {name!r} cannot be empty")
            if any(target <= 0 for target in targets):
                raise ValueError(f"harmonic target family {name!r} must be positive")
            constraint = self.constraints.get(name)
            if constraint is not None:
                for target in targets:
                    if not constraint.contains(target, include_tolerance=True):
                        raise ValueError(
                            f"harmonic target {target:g} for {name!r} lies outside its structural envelope"
                        )


# Standard M/W XABCD structures use a C-point retracement from the source-listed harmonic
# family bounded by 0.382 and 0.886. The broad band is only the structural envelope; the
# discrete family is enforced separately by PatternRule.harmonic_targets.
C_POINT_STANDARD = RatioConstraint(0.382, 0.886)


CARNEY_RULES: dict[str, PatternRule] = {
    "gartley": PatternRule(
        pattern_id="gartley",
        schema="XABCD",
        constraints={
            "b_xa": RatioConstraint(0.618, 0.618, ideal=0.618, tolerance_below=0.03, tolerance_above=0.03),
            "c_ab": C_POINT_STANDARD,
            "bc_projection": RatioConstraint(1.13, 1.618),
            "d_xa": RatioConstraint(0.786, 0.786, ideal=0.786),
        },
        harmonic_targets={
            "c_ab": HARMONIC_RETRACEMENT_FAMILY,
            "bc_projection": (1.13, 1.27, 1.414, 1.618),
        },
        abcd_types=(1.0, 1.27),
        abcd_minimum=1.0,
        source_note="Volume One Gartley chapter; Volume Three p.92 specification and B-point tolerance classification.",
        implementation_note=(
            "C and BC use source-listed harmonic ratio families rather than arbitrary continuous values. "
            "AB=CD is required as a completed minimum/PRZ component; preferred variants contribute to quality."
        ),
    ),
    "bat": PatternRule(
        pattern_id="bat",
        schema="XABCD",
        constraints={
            "b_xa": RatioConstraint(0.382, 0.50, ideal=0.50, tolerance_above=0.05),
            "c_ab": C_POINT_STANDARD,
            "bc_projection": RatioConstraint(1.618, 2.618),
            "d_xa": RatioConstraint(0.886, 0.886, ideal=0.886),
        },
        harmonic_targets={
            "c_ab": HARMONIC_RETRACEMENT_FAMILY,
            "bc_projection": (1.618, 2.0, 2.24, 2.618),
        },
        abcd_types=(1.0, 1.27, 1.618),
        abcd_minimum=1.0,
        source_note="Volume One Bat chapter; Volume Three p.98 specification. V3 calls for a minimum AB=CD, typically 1.27AB=CD.",
        implementation_note="C/BC are matched to the discrete harmonic family inside the source structural envelopes.",
    ),
    "alternate_bat": PatternRule(
        pattern_id="alternate_bat",
        schema="XABCD",
        constraints={
            "b_xa": RatioConstraint(0.0, 0.382, ideal=0.382),
            "c_ab": C_POINT_STANDARD,
            "bc_projection": RatioConstraint(2.0, 3.618),
            "d_xa": RatioConstraint(0.886, 1.13),
        },
        harmonic_targets={
            "c_ab": HARMONIC_RETRACEMENT_FAMILY,
            "bc_projection": (2.0, 2.24, 2.618, 3.14, 3.618),
        },
        abcd_types=(1.618,),
        abcd_minimum=None,
        source_conflict=True,
        source_note="Volume Two Alternate Bat chapter vs. Volume Three p.101 specification.",
        implementation_note=(
            "Volume Two explicitly says AB=CD is not included in this setup, while Volume Three lists 1.618AB=CD. "
            "Therefore AB=CD remains an auditable quality/PRZ reference, not a hard identity gate. "
            "Shared C/BC geometry is restricted to the source harmonic ratio family."
        ),
    ),
    "butterfly": PatternRule(
        pattern_id="butterfly",
        schema="XABCD",
        constraints={
            "b_xa": RatioConstraint(0.786, 0.786, ideal=0.786, tolerance_below=0.03, tolerance_above=0.03),
            "c_ab": C_POINT_STANDARD,
            "bc_projection": RatioConstraint(1.618, 2.24),
            "d_xa": RatioConstraint(1.27, 1.27, ideal=1.27),
        },
        harmonic_targets={
            "c_ab": HARMONIC_RETRACEMENT_FAMILY,
            "bc_projection": (1.618, 2.0, 2.24),
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
            "c_ab": C_POINT_STANDARD,
            "bc_projection": RatioConstraint(2.618, 3.618),
            "d_xa": RatioConstraint(1.618, 1.618, ideal=1.618),
        },
        harmonic_targets={
            "c_ab": HARMONIC_RETRACEMENT_FAMILY,
            "bc_projection": (2.618, 3.14, 3.618),
        },
        abcd_types=(1.0, 1.27, 1.618),
        abcd_minimum=1.0,
        source_note="Volume One Crab chapter; Volume Three p.104 canonical specification.",
        implementation_note=(
            "Volume Three canonical BC family is 2.618/3.14/3.618 inside 2.618-3.618. "
            "Volume One mentions occasional 2.0/2.24 variants; those remain outside the canonical identity pending variant-level Golden Cases."
        ),
    ),
    "deep_crab": PatternRule(
        pattern_id="deep_crab",
        schema="XABCD",
        constraints={
            "b_xa": RatioConstraint(0.886, 0.886, ideal=0.886, tolerance_above=0.05),
            "c_ab": C_POINT_STANDARD,
            "bc_projection": RatioConstraint(2.0, 3.618),
            "d_xa": RatioConstraint(1.618, 1.618, ideal=1.618),
        },
        harmonic_targets={
            "c_ab": HARMONIC_RETRACEMENT_FAMILY,
            "bc_projection": (2.0, 2.24, 2.618, 3.14, 3.618),
        },
        abcd_types=(1.0, 1.27, 1.618),
        abcd_minimum=1.0,
        source_note="Volume One Deep Crab chapter; Volume Three p.107 specification.",
    ),
    "abcd": PatternRule(
        pattern_id="abcd",
        schema="ABCD",
        constraints={"c_ab": C_POINT_STANDARD},
        harmonic_targets={"c_ab": HARMONIC_RETRACEMENT_FAMILY},
        abcd_types=(1.0, 1.13, 1.27, 1.41, 1.618, 2.0),
        source_note="Volume One Ch.4 reciprocal table; Volume Three pp.76-80 AB=CD and reciprocal-ratio review.",
        implementation_note="Reciprocal C/AB -> BC projection mapping is frozen separately in ratios.RECIPROCAL_ABCD.",
    ),
    "shark": PatternRule(
        pattern_id="shark",
        schema="0XABC",
        constraints={
            "a_0x": RatioConstraint(0.382, 0.618),
            "b_xa": RatioConstraint(1.13, 1.618),
            "c_ab": RatioConstraint(1.618, 2.24),
            "c_0b": RatioConstraint(0.886, 1.13),
        },
        executable_identity=False,
        source_note="Volume Three pp.116-129 advanced Shark specification and figure-level 0-X-A-B-C ratios.",
        implementation_note=(
            "Executed only by the dedicated Shark evaluator. A/0X=0.382-0.618, "
            "B/XA=1.13-1.618, C/AB=1.618-2.24 and C/0B=0.886-1.13 must converge. "
            "Dedicated Shark figure reconciliation remains separate from standard XABCD family matching."
        ),
    ),
    "five_zero": PatternRule(
        pattern_id="five_zero",
        schema="FIVE_ZERO",
        constraints={
            "b_xa": RatioConstraint(1.13, 1.618),
            "c_ab": RatioConstraint(1.618, 2.24),
        },
        executable_identity=False,
        source_conflict=True,
        source_note=(
            "Volume Two Ch.3 freezes the structural 5-0 Raw PRZ as 50% BC retracement + "
            "Reciprocal AB=CD. Volume Three pp.129-138 adds 61.8 execution/stop refinement "
            "but alternates XA/AB labels while its structural figures/cases preserve B-C geometry."
        ),
        implementation_note=(
            "Research-only production quarantine. The structural Source Raw PRZ is resolved and "
            "must never be collapsed into a generic 50%-61.8% band. The 61.8 measure is execution-only, "
            "raw_prz_membership=false and identity_membership=false; the remaining source_conflict flag "
            "records Volume Three's inconsistent leg labels rather than an unresolved Volume Two structure."
        ),
    ),
}
