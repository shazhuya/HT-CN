from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Literal

Direction = Literal["bullish", "bearish"]

_HARMONIC_RETRACEMENTS = (0.382, 0.500, 0.618, 0.707, 0.786, 0.886)
_HARMONIC_TOLERANCE = 0.03
_EPSILON = 1e-12


@dataclass(frozen=True, slots=True)
class OracleRule:
    pattern_id: str
    b_min: float
    b_max: float
    b_tol_below: float
    b_tol_above: float
    c_min: float
    c_max: float
    bc_min: float
    bc_max: float
    bc_targets: tuple[float, ...]
    d_min: float
    d_max: float
    abcd_minimum: float


@dataclass(frozen=True, slots=True)
class OracleMetrics:
    b_xa: float
    c_ab: float
    bc_projection: float
    d_xa: float
    cd_ab: float


@dataclass(frozen=True, slots=True)
class OracleMatch:
    pattern_id: str
    direction: Direction
    metrics: OracleMetrics


# Independent, literal snapshot of the source-cleared standard XABCD identity contract.
# Deliberately do not import CARNEY_RULES, evaluator.py, scanner.py or discovery.py here.
_ORACLE_RULES: tuple[OracleRule, ...] = (
    OracleRule(
        "gartley",
        0.618,
        0.618,
        0.03,
        0.03,
        0.382,
        0.886,
        1.13,
        1.618,
        (1.13, 1.27, 1.414, 1.618),
        0.786,
        0.786,
        1.0,
    ),
    OracleRule(
        "bat",
        0.382,
        0.500,
        0.0,
        0.05,
        0.382,
        0.886,
        1.618,
        2.618,
        (1.618, 2.0, 2.24, 2.618),
        0.886,
        0.886,
        1.0,
    ),
    OracleRule(
        "butterfly",
        0.786,
        0.786,
        0.03,
        0.03,
        0.382,
        0.886,
        1.618,
        2.24,
        (1.618, 2.0, 2.24),
        1.27,
        1.27,
        1.0,
    ),
    OracleRule(
        "crab",
        0.382,
        0.618,
        0.0,
        0.0,
        0.382,
        0.886,
        2.618,
        3.618,
        (2.618, 3.14, 3.618),
        1.618,
        1.618,
        1.0,
    ),
    OracleRule(
        "deep_crab",
        0.886,
        0.886,
        0.0,
        0.05,
        0.382,
        0.886,
        2.0,
        3.618,
        (2.0, 2.24, 2.618, 3.14, 3.618),
        1.618,
        1.618,
        1.0,
    ),
)


def _ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        raise ValueError("ratio denominator must be positive")
    return numerator / denominator


def _within(value: float, minimum: float, maximum: float) -> bool:
    pad = _EPSILON * max(1.0, abs(value), abs(minimum), abs(maximum))
    return minimum - pad <= value <= maximum + pad


def _near_family(
    value: float,
    targets: tuple[float, ...],
    *,
    relative_tolerance: float = _HARMONIC_TOLERANCE,
) -> bool:
    return any(
        abs(value - target) / target <= relative_tolerance + _EPSILON
        for target in targets
    )


def measure_xabcd_prices(prices: tuple[float, float, float, float, float]) -> OracleMetrics:
    x, a, b, c, d = (float(value) for value in prices)
    xa = abs(a - x)
    ab = abs(b - a)
    bc = abs(c - b)
    cd = abs(d - c)
    ad = abs(d - a)
    if min(xa, ab, bc) <= 0:
        raise ValueError("XABCD legs XA/AB/BC must be non-zero")
    return OracleMetrics(
        b_xa=_ratio(ab, xa),
        c_ab=_ratio(bc, ab),
        bc_projection=_ratio(cd, bc),
        d_xa=_ratio(ad, xa),
        cd_ab=_ratio(cd, ab),
    )


def infer_direction(prices: tuple[float, float, float, float, float]) -> Direction:
    x, a, _, _, _ = prices
    if a == x:
        raise ValueError("X and A cannot have the same price")
    return "bullish" if a > x else "bearish"


def turning_geometry_is_valid(
    prices: tuple[float, float, float, float, float],
    direction: Direction,
) -> bool:
    x, a, b, c, d = prices
    if direction == "bullish":
        return a > x and b < a and c > b and d < c
    return a < x and b > a and c < b and d > c


def _rule_matches(rule: OracleRule, metrics: OracleMetrics) -> bool:
    if not _within(
        metrics.b_xa,
        rule.b_min - rule.b_tol_below,
        rule.b_max + rule.b_tol_above,
    ):
        return False
    if not _within(metrics.c_ab, rule.c_min, rule.c_max):
        return False
    if not _near_family(metrics.c_ab, _HARMONIC_RETRACEMENTS):
        return False
    if not _within(metrics.bc_projection, rule.bc_min, rule.bc_max):
        return False
    if not _near_family(metrics.bc_projection, rule.bc_targets):
        return False
    if not _within(metrics.d_xa, rule.d_min, rule.d_max):
        return False
    if metrics.cd_ab + _EPSILON < rule.abcd_minimum:
        return False
    return all(
        isfinite(value)
        for value in (
            metrics.b_xa,
            metrics.c_ab,
            metrics.bc_projection,
            metrics.d_xa,
            metrics.cd_ab,
        )
    )


def classify_xabcd_prices(
    prices: tuple[float, float, float, float, float],
) -> tuple[OracleMatch, ...]:
    normalized = tuple(float(value) for value in prices)
    if len(normalized) != 5:
        raise ValueError("oracle requires exactly five X/A/B/C/D prices")
    direction = infer_direction(normalized)
    if not turning_geometry_is_valid(normalized, direction):
        return ()
    metrics = measure_xabcd_prices(normalized)
    return tuple(
        OracleMatch(rule.pattern_id, direction, metrics)
        for rule in _ORACLE_RULES
        if _rule_matches(rule, metrics)
    )


def oracle_pattern_ids(
    prices: tuple[float, float, float, float, float],
) -> tuple[str, ...]:
    return tuple(match.pattern_id for match in classify_xabcd_prices(prices))
