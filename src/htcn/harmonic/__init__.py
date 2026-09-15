"""HT-CN harmonic core.

This package contains deterministic geometry only. A-share context and trading decisions
must live outside this namespace so they cannot mutate Carney pattern identity.
"""

from .evaluator import (
    ConstraintCheck,
    PatternEvaluation,
    XABCDMetrics,
    evaluate_xabcd,
    measure_xabcd,
)
from .models import (
    HarmonicPoint,
    PatternDirection,
    PatternState,
    Pivot,
    PivotKind,
    RatioMeasurement,
)
from .pivots import collapse_same_kind_pivots, detect_confirmed_pivots, detect_multi_scale_pivots
from .prz import PRZComponent, PotentialReversalZone, build_xabcd_prz
from .ratios import RECIPROCAL_ABCD, leg_length, ratio_of_legs, reciprocal_bc_targets
from .rules import CARNEY_RULES, PatternRule, RatioConstraint

__all__ = [
    "CARNEY_RULES",
    "RECIPROCAL_ABCD",
    "ConstraintCheck",
    "HarmonicPoint",
    "PRZComponent",
    "PatternDirection",
    "PatternEvaluation",
    "PatternRule",
    "PatternState",
    "Pivot",
    "PivotKind",
    "PotentialReversalZone",
    "RatioConstraint",
    "RatioMeasurement",
    "XABCDMetrics",
    "build_xabcd_prz",
    "collapse_same_kind_pivots",
    "detect_confirmed_pivots",
    "detect_multi_scale_pivots",
    "evaluate_xabcd",
    "leg_length",
    "measure_xabcd",
    "ratio_of_legs",
    "reciprocal_bc_targets",
]
