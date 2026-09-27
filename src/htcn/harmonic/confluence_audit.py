"""Projection qualification evidence, never a replacement for Source identity.

This is a conservative diagnostic screen. Compatibility at the nominal XA anchor
is necessary for this screen to clear, but is NOT asserted as a universal exact-D
rule. Failure requires review; success is not full semantic acceptance. Terminal
observations remain visible for audit in either case.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import HarmonicPoint
from .prz import PotentialReversalZone
from .rules import CARNEY_RULES


@dataclass(frozen=True, slots=True)
class ConfluenceAudit:
    status: str
    reason: str
    required_bc_at_nominal_xa: float | None
    bc_envelope: tuple[float, float] | None
    primary_separation_xa: float | None
    raw_width_xa: float | None
    policy: str = "nominal_anchor_review_screen_v1"

    @property
    def validated_identity(self) -> bool:
        # This screen never grants Source identity or production promotion.
        return False


def audit_projection_confluence(
    pattern_id: str,
    points: tuple[HarmonicPoint, ...],
    prz: PotentialReversalZone,
) -> ConfluenceAudit:
    rule = CARNEY_RULES.get(pattern_id)
    if (rule is None or pattern_id in {"alternate_bat", "five_zero"}
            or len(points) != 4 or not prz.has_source_prz):
        return ConfluenceAudit("unresolved", "unsupported_or_unresolved_source", None,
                               None, None, None)
    x, a, b, c = points
    xa, bc = abs(a.price - x.price), abs(c.price - b.price)
    defining = next((v for v in prz.components if v.name == "XA completion"), None)
    bc_components = [v for v in prz.components
                     if v.name in prz.source_prz_component_names
                     and v.name.startswith("BC projection")]
    envelope = rule.constraints.get("bc_projection")
    if xa <= 0 or bc <= 0 or defining is None or not bc_components or envelope is None:
        return ConfluenceAudit("unresolved", "missing_measurement", None, None, None, None)
    anchor = defining.midpoint
    required = abs(c.price - anchor) / bc
    bounds = (envelope.minimum, envelope.maximum)
    separation = min(abs(anchor - v.midpoint) / xa for v in bc_components)
    width = (prz.source_prz_high - prz.source_prz_low) / xa
    # Epsilon is floating point comparison slack, not a trading tolerance.
    compatible = bounds[0] - 1e-9 <= required <= bounds[1] + 1e-9
    return ConfluenceAudit(
        "primary_compatible_unverified" if compatible else "review_required",
        "full_confluence_and_identity_not_yet_adjudicated" if compatible
        else "nominal_xa_requires_bc_outside_source_envelope",
        required, bounds, separation, width,
    )
