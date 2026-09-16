from __future__ import annotations

from dataclasses import dataclass

from .candidates import SwingWindow
from .evaluator import PatternEvaluation, evaluate_xabcd
from .models import PatternDirection
from .prz import PotentialReversalZone, build_xabcd_prz
from .ratios import leg_length
from .rules import CARNEY_RULES, PatternRule


@dataclass(frozen=True, slots=True)
class FormingPattern:
    pattern_id: str
    direction: PatternDirection
    b_xa: float
    c_ab: float
    prz: PotentialReversalZone
    source_tolerance_used: bool


def executable_xabcd_rules() -> tuple[PatternRule, ...]:
    return tuple(
        rule
        for rule in CARNEY_RULES.values()
        if rule.schema == "XABCD" and rule.executable_identity
    )


def project_forming_xabcd(
    window: SwingWindow,
    *,
    include_source_tolerance: bool = True,
) -> tuple[FormingPattern, ...]:
    """Project D/PRZ only after XABC already satisfies source-backed B and C geometry.

    A forming pattern is not merely "B looks like a Bat/Gartley". C already exists and its
    AB retracement is therefore known. Letting an invalid C through creates large numbers of
    visually plausible but source-invalid projected PRZs, exactly the kind of candidate noise
    that a live A-share chart must avoid.
    """
    if window.is_completed:
        raise ValueError("forming projection requires a 4-pivot XABC window")
    x, a, b, c = window.harmonic_points()
    xa = leg_length(x.price, a.price)
    ab = leg_length(a.price, b.price)
    bc = leg_length(b.price, c.price)
    if xa <= 0 or ab <= 0:
        return ()
    b_xa = ab / xa
    c_ab = bc / ab
    direction = PatternDirection.BULLISH if a.price > x.price else PatternDirection.BEARISH

    # XABC must already alternate in the direction expected by a potential D reversal.
    if direction is PatternDirection.BULLISH and not (b.price < a.price and c.price > b.price):
        return ()
    if direction is PatternDirection.BEARISH and not (b.price > a.price and c.price < b.price):
        return ()

    projections: list[FormingPattern] = []
    for rule in executable_xabcd_rules():
        b_constraint = rule.constraints.get("b_xa")
        c_constraint = rule.constraints.get("c_ab")
        if b_constraint is None or c_constraint is None:
            continue
        if not b_constraint.contains(b_xa, include_tolerance=include_source_tolerance):
            continue
        if not c_constraint.contains(c_ab, include_tolerance=include_source_tolerance):
            continue
        try:
            prz = build_xabcd_prz(rule, (x, a, b, c))
        except ValueError:
            # A mathematically projected price can become non-positive for a pathological
            # candidate. That candidate is isolated here instead of crashing the scan.
            continue
        tolerance_used = include_source_tolerance and (
            not b_constraint.contains(b_xa, include_tolerance=False)
            or not c_constraint.contains(c_ab, include_tolerance=False)
        )
        projections.append(
            FormingPattern(
                pattern_id=rule.pattern_id,
                direction=direction,
                b_xa=b_xa,
                c_ab=c_ab,
                prz=prz,
                source_tolerance_used=tolerance_used,
            )
        )
    return tuple(projections)


def classify_completed_xabcd(
    window: SwingWindow,
    *,
    include_source_tolerance: bool = True,
    abcd_relative_tolerance: float = 0.03,
) -> tuple[PatternEvaluation, ...]:
    if not window.is_completed:
        raise ValueError("completed classification requires a 5-pivot XABCD window")
    points = window.harmonic_points()
    evaluations: list[PatternEvaluation] = []
    for rule in executable_xabcd_rules():
        try:
            result = evaluate_xabcd(
                rule,
                points,
                include_source_tolerance=include_source_tolerance,
                abcd_relative_tolerance=abcd_relative_tolerance,
            )
        except ValueError:
            # Rule/candidate incompatibility must reject only this identity attempt; one
            # malformed projected PRZ must never abort scanning other patterns/scales.
            continue
        if result.passed:
            evaluations.append(result)
    return tuple(evaluations)
