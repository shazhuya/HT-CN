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
    "abcd": SourcePRZEvidence(
        pattern_id="abcd",
        evidence_level="source_specification_plus_market_examples_membership_only",
        source_membership_authority="carney_vol1_vol3",
        selection_authority="carney_equivalent_abcd_plus_reciprocal_bc_pair",
        market_case_ids=(
            "v1-perfect-abcd-nqh4-10m",
            "v1-abcd-es-bearish",
        ),
        coordinate_regression_status="pending_reliable_source_pivots",
    ),
    "five_zero": SourcePRZEvidence(
        pattern_id="five_zero",
        evidence_level="structural_source_frozen_plus_market_examples_with_v3_execution_label_conflict",
        source_membership_authority="carney_vol2_structural_prz",
        selection_authority="carney_50_bc_plus_reciprocal_abcd",
        market_case_ids=(
            "v2-five-zero-eur-a0-fx-5m",
            "v2-five-zero-xoi-5m",
            "v2-five-zero-adobe-daily",
            "v3-five-zero-aud-a0-fx-60m",
            "v3-five-zero-gld-15m",
        ),
        known_tensions=(
            "Volume Two repeatedly defines the structural 5-0 PRZ as 50% BC retracement + Reciprocal AB=CD. "
            "Volume Three pp.129-138 adds a 61.8 execution/stop refinement but internally alternates XA and AB "
            "labels around 50%/61.8 while its structural figures and market cases preserve the B-C pullback geometry. "
            "M2.29 therefore freezes Volume Two Raw PRZ membership and keeps 61.8 execution-only under an explicit "
            "HT-CN BC-axis interpretation; it does not rewrite the conflicting Volume Three labels.",
        ),
        coordinate_regression_status="structural_membership_frozen_execution_label_conflict_recorded",
    ),
}


def source_prz_evidence(pattern_id: str) -> SourcePRZEvidence | None:
    return SOURCE_PRZ_EVIDENCE.get(pattern_id)
