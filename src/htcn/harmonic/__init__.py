"""HT-CN harmonic core.

This package contains deterministic geometry and source-backed harmonic lifecycle audits.
A-share context and trading decisions must live outside this namespace so they cannot mutate
Carney pattern identity.
"""

from .candidates import (
    SwingWindow,
    iter_completed_xabcd_windows,
    iter_forming_xabc_windows,
    iter_swing_windows,
)
from .engine import CompletedMatch, FormingMatch, HarmonicScan, scan_frame, scan_pivots
from .evaluator import (
    ConstraintCheck,
    PatternEvaluation,
    XABCDMetrics,
    evaluate_xabcd,
    measure_xabcd,
)
from .indicators import wilder_rsi
from .lifecycle import ReactionAudit, audit_completed_reaction
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
from .scanner import (
    FormingPattern,
    classify_completed_xabcd,
    executable_xabcd_rules,
    project_forming_xabcd,
)

__all__ = [
    "CARNEY_RULES",
    "RECIPROCAL_ABCD",
    "CompletedMatch",
    "ConstraintCheck",
    "FormingMatch",
    "FormingPattern",
    "HarmonicPoint",
    "HarmonicScan",
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
    "ReactionAudit",
    "SwingWindow",
    "XABCDMetrics",
    "audit_completed_reaction",
    "build_xabcd_prz",
    "classify_completed_xabcd",
    "collapse_same_kind_pivots",
    "detect_confirmed_pivots",
    "detect_multi_scale_pivots",
    "evaluate_xabcd",
    "executable_xabcd_rules",
    "iter_completed_xabcd_windows",
    "iter_forming_xabc_windows",
    "iter_swing_windows",
    "leg_length",
    "measure_xabcd",
    "project_forming_xabcd",
    "ratio_of_legs",
    "reciprocal_bc_targets",
    "scan_frame",
    "scan_pivots",
    "wilder_rsi",
]
