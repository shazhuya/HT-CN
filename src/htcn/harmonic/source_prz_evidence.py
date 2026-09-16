from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourcePRZEvidence:
    pattern_id: str
    evidence_level: str
    source_membership_authority: str
    selection_authority: str
    market_case_ids: tuple[str, ...]
    known_tensions: tuple[str, ...] = ()
    coordinate_regression_status: str = "pending_reliable_source_pivots"


SOURCE_PRZ_EVIDENCE: dict[str, SourcePRZEvidence] = {
    "abcd": SourcePRZEvidence(
        pattern_id="abcd",
        evidence_level="source_specification_plus_market_examples",
        source_membership_authority="carney_vol1_vol3",
        selection_authority="carney_exact_abcd_plus_primary_reciprocal_bc",
        market_case_ids=("v1-abcd-nqh4-10m", "v3-abcd-eurusd-15m"),
        coordinate_regression_status="source_price_examples_recorded_pivots_pending",
    ),
    "gartley": SourcePRZEvidence(
        pattern_id="gartley",
        evidence_level="source_specification_plus_market_examples",
        source_membership_authority="carney_vol1_vol3",
        selection_authority="htcn_operational_convergence_within_source_valid_family",
        market_case_ids=("v1-gartley-plce-weekly",),
    ),
    "bat": SourcePRZEvidence(
        pattern_id="bat",
        evidence_level="source_specification_plus_market_examples_with_recorded_tension",
        source_membership_authority="carney_vol1_vol3",
        selection_authority="htcn_operational_convergence_within_source_valid_family",
        market_case_ids=(
            "v1-bat-jpm-weekly",
            "v1-bat-dji-weekly",
            "v1-perfect-bat-ara-weekly",
        ),
        known_tensions=(
            "Volume One Perfect Bat simultaneously states B=0.50, C=0.50-0.618, D=0.886 XA, "
            "BC=2.0 and alternate 1.27 AB=CD. Those ideal ratios do not all share one exact D "
            "under the standard leg-length projection algebra, although the ARA market example "
            "shows the three measured prices converging near 14. M2.27 records this instead of "
            "changing projection formulas to force coincidence.",
        ),
    ),
    "alternate_bat": SourcePRZEvidence(
        pattern_id="alternate_bat",
        evidence_level="source_conflict_fail_closed",
        source_membership_authority="carney_vol2_vs_vol3_conflict",
        selection_authority="none_fail_closed",
        market_case_ids=(),
        known_tensions=(
            "Volume Two excludes AB=CD from the Alternate Bat setup while Volume Three lists "
            "1.618 AB=CD; executable Source PRZ remains blocked.",
        ),
        coordinate_regression_status="blocked_by_source_conflict",
    ),
    "butterfly": SourcePRZEvidence(
        pattern_id="butterfly",
        evidence_level="source_specification_plus_market_examples",
        source_membership_authority="carney_vol1_vol3",
        selection_authority="htcn_operational_convergence_within_source_valid_family",
        market_case_ids=("v1-butterfly-cin-daily", "v1-butterfly-clz3-60m"),
    ),
    "crab": SourcePRZEvidence(
        pattern_id="crab",
        evidence_level="source_specification_plus_market_examples",
        source_membership_authority="carney_vol1_vol3",
        selection_authority="htcn_xa_bc_primary_then_abcd_complement_within_source_valid_family",
        market_case_ids=("v1-perfect-crab-hd-15m", "v1-crab-nqz3-30m"),
    ),
    "deep_crab": SourcePRZEvidence(
        pattern_id="deep_crab",
        evidence_level="source_specification_plus_market_examples",
        source_membership_authority="carney_vol1_vol3",
        selection_authority="htcn_operational_convergence_within_source_valid_family",
        market_case_ids=("v1-deep-crab-nqz3-15m",),
    ),
}


def source_prz_evidence(pattern_id: str) -> SourcePRZEvidence | None:
    return SOURCE_PRZ_EVIDENCE.get(pattern_id)
