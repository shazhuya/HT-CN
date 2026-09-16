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

__all__ = [
    "DEFAULT_OBSERVATION_HORIZON",
    "build_completed_case_record",
    "canonical_case_key",
    "dedupe_case_records",
]
