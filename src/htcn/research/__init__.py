"""Research-only calibration helpers for HT-CN.

This namespace may analyze source-valid harmonic outputs and their later outcomes, but it
must never mutate Carney pattern identity or silently feed outcome success back into the
identity rules.
"""

from .case_calibration import (
    DEFAULT_OBSERVATION_HORIZON,
    build_completed_case_record,
    canonical_case_key,
    dedupe_case_records,
)
from .quality_gate import (
    GateClause,
    GateSpec,
    build_gate_library,
    evaluate_gate_library,
    gate_matches,
)
from .time_split import (
    NumericThresholds,
    SplitBoundaries,
    assign_purged_split,
    derive_boundaries,
    grouped_summary,
    learn_numeric_thresholds,
    mature_forward_records,
    outcome_summary,
    signal_features,
    split_manifest,
)
from .walk_forward import (
    DEFAULT_FORWARD_HORIZON,
    DEFAULT_WALK_FORWARD_SCALES,
    walk_forward_forming_signals,
)

__all__ = [
    "DEFAULT_FORWARD_HORIZON",
    "DEFAULT_OBSERVATION_HORIZON",
    "DEFAULT_WALK_FORWARD_SCALES",
    "GateClause",
    "GateSpec",
    "NumericThresholds",
    "SplitBoundaries",
    "assign_purged_split",
    "build_completed_case_record",
    "build_gate_library",
    "canonical_case_key",
    "dedupe_case_records",
    "derive_boundaries",
    "evaluate_gate_library",
    "gate_matches",
    "grouped_summary",
    "learn_numeric_thresholds",
    "mature_forward_records",
    "outcome_summary",
    "signal_features",
    "split_manifest",
    "walk_forward_forming_signals",
]
