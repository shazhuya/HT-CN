"""HT-CN harmonic core.

This package contains deterministic geometry only. A-share context and trading decisions
must live outside this namespace so they cannot mutate Carney pattern identity.
"""

from .models import (
    HarmonicPoint,
    PatternDirection,
    PatternState,
    Pivot,
    PivotKind,
    RatioMeasurement,
)
from .pivots import collapse_same_kind_pivots, detect_confirmed_pivots, detect_multi_scale_pivots
from .ratios import RECIPROCAL_ABCD, leg_length, ratio_of_legs, reciprocal_bc_targets
from .rules import CARNEY_RULES, PatternRule, RatioConstraint

__all__ = [
    "CARNEY_RULES",
    "RECIPROCAL_ABCD",
    "HarmonicPoint",
    "PatternDirection",
    "PatternRule",
    "PatternState",
    "Pivot",
    "PivotKind",
    "RatioConstraint",
    "RatioMeasurement",
    "collapse_same_kind_pivots",
    "detect_confirmed_pivots",
    "detect_multi_scale_pivots",
    "leg_length",
    "ratio_of_legs",
    "reciprocal_bc_targets",
]
