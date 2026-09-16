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
    harmonic_family_tolerance_used: bool = False


def executable_xabcd_rules() -> tuple[PatternRule, ...]:
    return tuple(
        rule
        for rule in CARNEY_RULES.values()
        if rule.schema == "XABCD" and rule.executable_identity
    )


def _nearest_relative_error(value: float, targets: tuple[float, ...]) -> float:
    if not targets:
        return 0.0
    return min(abs(float(value) - float(target)) / float(target) for target in targets)


def project_forming_xabcd(
    window: SwingWindow,
    *,
    include_source_tolerance: bool = True,
    harmonic_family_relative_tolerance: float = 0.03,
) -> tuple[FormingPattern, ...]:
    """Project D/PRZ only after XABC satisfies source-backed geometry.

    C must lie inside the broad structural envelope AND near one of the finite harmonic
    retracement ratios listed by the source. The operational matching tolerance is HT-CN
    policy; it is not represented as a universal Carney constant.
    """
    if window.is_completed:
        raise ValueError("forming projection requires a 4-pivot XABC window")
    if harmonic_family_relative_tolerance < 0:
        raise ValueError("harmonic_family_relative_tolerance must be non-negative")

    x, a, b, c = window.harmonic_points()
    xa = leg_length(x.price, a.price)
    ab = leg_length(a.price, b.price)
    bc = leg_length(b.price, c.price)
    if xa <= 0 or ab <= 0:
        return ()
    b_xa = ab / xa
    c_ab = bc / ab
    direction = PatternDirection.BULLISH if a.price > x.price else PatternDirection.BEARISH

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

        c_family = rule.harmonic_targets.get("c_ab", ())
        c_family_error = _nearest_relative_error(c_ab, c_family)
        if c_family and c_family_error > harmonic_family_relative_tolerance:
            continue

        try:
            prz = build_xabcd_prz(rule, (x, a, b, c))
        except ValueError:
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
                harmonic_family_tolerance_used=bool(c_family and c_family_error > 1e-12),
            )
        )
    return tuple(projections)


def classify_completed_xabcd(
    window: SwingWindow,
    *,
    include_source_tolerance: bool = True,
    abcd_relative_tolerance: float = 0.03,
    harmonic_family_relative_tolerance: float = 0.03,
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
                harmonic_family_relative_tolerance=harmonic_family_relative_tolerance,
            )
        except ValueError:
            continue
        if result.passed:
            evaluations.append(result)
    return tuple(evaluations)
