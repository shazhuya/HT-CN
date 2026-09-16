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
from .completed_reaction import (
    DEFAULT_COMPLETED_REACTION_HORIZON,
    DEFAULT_COMPLETED_REACTION_SCALES,
    audit_confirmed_reaction,
    completed_reaction_summary,
    confirmed_completed_reaction_records,
)
from .completed_reaction_robustness import build_completed_reaction_robustness_report
from .quality_gate import (
    GateClause,
    GateSpec,
    build_gate_library,
    evaluate_gate_library,
    gate_matches,
)
from .quality_layers import (
    build_layered_quality_report,
    classify_gate_layer,
    gate_generalization_diagnostics,
    pattern_family,
)
from .quality_robustness import build_quality_robustness_report
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
    "DEFAULT_COMPLETED_REACTION_HORIZON",
    "DEFAULT_COMPLETED_REACTION_SCALES",
    "DEFAULT_FORWARD_HORIZON",
    "DEFAULT_OBSERVATION_HORIZON",
    "DEFAULT_WALK_FORWARD_SCALES",
    "GateClause",
    "GateSpec",
    "NumericThresholds",
    "SplitBoundaries",
    "assign_purged_split",
    "audit_confirmed_reaction",
    "build_completed_case_record",
    "build_completed_reaction_robustness_report",
    "build_gate_library",
    "build_layered_quality_report",
    "build_quality_robustness_report",
    "canonical_case_key",
    "classify_gate_layer",
    "completed_reaction_summary",
    "confirmed_completed_reaction_records",
    "dedupe_case_records",
    "derive_boundaries",
    "evaluate_gate_library",
    "gate_generalization_diagnostics",
    "gate_matches",
    "grouped_summary",
    "learn_numeric_thresholds",
    "mature_forward_records",
    "outcome_summary",
    "pattern_family",
    "signal_features",
    "split_manifest",
    "walk_forward_forming_signals",
]
