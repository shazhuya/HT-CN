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
    if window.is_completed:
        raise ValueError("forming projection requires a 4-pivot XABC window")
    x, a, b, c = window.harmonic_points()
    xa = leg_length(x, a)
    b_xa = leg_length(a, b) / xa
    direction = PatternDirection.BULLISH if a.price > x.price else PatternDirection.BEARISH

    # XABC must already alternate in the direction expected by a potential D reversal.
    if direction is PatternDirection.BULLISH and not (b.price < a.price and c.price > b.price):
        return ()
    if direction is PatternDirection.BEARISH and not (b.price > a.price and c.price < b.price):
        return ()

    projections: list[FormingPattern] = []
    for rule in executable_xabcd_rules():
        b_constraint = rule.constraints.get("b_xa")
        if b_constraint is None:
            continue
        if not b_constraint.contains(b_xa, include_tolerance=include_source_tolerance):
            continue
        projections.append(
            FormingPattern(
                pattern_id=rule.pattern_id,
                direction=direction,
                b_xa=b_xa,
                prz=build_xabcd_prz(rule, (x, a, b, c)),
                source_tolerance_used=(
                    not b_constraint.contains(b_xa, include_tolerance=False)
                    and include_source_tolerance
                ),
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
        result = evaluate_xabcd(
            rule,
            points,
            include_source_tolerance=include_source_tolerance,
            abcd_relative_tolerance=abcd_relative_tolerance,
        )
        if result.passed:
            evaluations.append(result)
    return tuple(evaluations)
