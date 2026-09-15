"""HT-CN harmonic core.

This package contains deterministic geometry only. A-share context and trading decisions
must live outside this namespace so they cannot mutate Carney pattern identity.
"""

from .models import HarmonicPoint, PatternDirection, PatternState, RatioMeasurement
from .ratios import RECIPROCAL_ABCD, leg_length, ratio_of_legs, reciprocal_bc_targets
from .rules import CARNEY_RULES, PatternRule, RatioConstraint

__all__ = [
    "CARNEY_RULES",
    "RECIPROCAL_ABCD",
    "HarmonicPoint",
    "PatternDirection",
    "PatternRule",
    "PatternState",
    "RatioConstraint",
    "RatioMeasurement",
    "leg_length",
    "ratio_of_legs",
    "reciprocal_bc_targets",
]
