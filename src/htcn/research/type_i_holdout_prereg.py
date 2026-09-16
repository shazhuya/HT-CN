from __future__ import annotations

from typing import Any


PREREGISTRATION_ID = "m2-type-i-holdout-v1"
DEFAULT_HOLDOUT_MIN_GROUP = 20
NEWCOMBE_Z_95 = 1.959963984540054


def build_type_i_holdout_preregistration(
    exit_timing_report: dict[str, Any],
    *,
    dataset_id: str | None,
    snapshot_cutoff: str | None,
    source_commit: str | None = None,
    minimum_holdout_group: int = DEFAULT_HOLDOUT_MIN_GROUP,
) -> dict[str, Any]:
    """Freeze a one-time Holdout test plan without opening or summarizing Holdout outcomes."""
    selected = exit_timing_report.get("selected_hypothesis")
    ready = bool(
        exit_timing_report.get("status") == "type_i_exit_timing_evidence_holdout_sealed"
        and exit_timing_report.get("eligible_for_preregistration") is True
        and selected in {"full_prz_exit_by_t3", "full_prz_exit_by_t5"}
        and (exit_timing_report.get("holdout") or {}).get("outcomes_exposed") is False
    )
    if not ready:
        return {
            "status": "type_i_holdout_preregistration_not_ready",
            "preregistration_id": PREREGISTRATION_ID,
            "selected_hypothesis": selected,
            "holdout": {"sealed": True, "outcomes_exposed": False},
            "holdout_open_authorized": False,
            "policy_frozen": False,
        }

    if selected == "full_prz_exit_by_t3":
        exposure = {
            "name": "exit_by_t3",
            "definition": "T2 pending at T+5 and first full PRZ exit occurs by T+3.",
        }
        comparator = {
            "name": "exit_on_t4_t5",
            "definition": "T2 pending at T+5, no full PRZ exit by T+3, and first full exit occurs on T+4 or T+5.",
        }
        claim = "Earlier full PRZ exit by T+3 has incremental progression evidence beyond a later T+4/T+5 exit."
    else:
        exposure = {
            "name": "full_prz_exit_by_t5",
            "definition": "T2 pending at T+5 and a full PRZ exit occurs at least once from T+1 through T+5.",
        }
        comparator = {
            "name": "no_full_exit_by_t5",
            "definition": "T2 pending at T+5 and no full PRZ exit occurs from T+1 through T+5.",
        }
        claim = "A full PRZ exit within five bars, rather than exit speed inside that window, is associated with higher later Type-I T2 progression."

    return {
        "status": "type_i_holdout_test_preregistered_sealed",
        "preregistration_id": PREREGISTRATION_ID,
        "dataset": {
            "dataset_id": dataset_id,
            "snapshot_cutoff": snapshot_cutoff,
            "price_mode": "qfq",
        },
        "source_commit": source_commit,
        "selected_hypothesis": selected,
        "claim": claim,
        "population": {
            "clock": "M2.17 source-aligned Terminal Price Bar",
            "eligibility": "Terminal event is mature for the 20-bar reaction horizon and T2 remains pending at T+5.",
            "split": "Only the already-sealed M2.17 Holdout is eligible for the confirmatory evaluation.",
        },
        "primary_contrast": {
            "exposure": exposure,
            "comparator": comparator,
            "endpoint": "First T2 hit from T+6 through T+20.",
            "effect_measure": "absolute difference in endpoint proportions: exposure minus comparator",
        },
        "confirmatory_test": {
            "method": "Newcombe score confidence interval for the difference of two independent proportions",
            "confidence_level": 0.95,
            "z": NEWCOMBE_Z_95,
            "minimum_records_per_group": minimum_holdout_group,
            "success_criterion": "lower bound of the 95% Newcombe interval for exposure-minus-comparator is > 0",
            "insufficient_sample_result": "inconclusive",
            "nonpositive_lower_bound_result": "not_confirmed",
        },
        "secondary_diagnostics": {
            "dimensions": ["direction", "pattern_family", "source_scale", "instrument_id"],
            "role": "descriptive only; they cannot rescue or overturn the primary confirmatory result",
        },
        "multiplicity": {
            "primary_tests": 1,
            "post_hoc_threshold_search_allowed": False,
            "alternate_endpoint_substitution_allowed": False,
        },
        "holdout": {
            "sealed": True,
            "records": int((exit_timing_report.get("holdout") or {}).get("records", 0)),
            "outcomes_exposed": False,
        },
        "holdout_open_authorized": False,
        "policy_frozen": False,
        "anti_leakage": {
            "hypothesis_selected_before_holdout_open": True,
            "primary_contrast_fixed_before_holdout_open": True,
            "success_criterion_fixed_before_holdout_open": True,
            "holdout_outcomes_opened": False,
        },
    }
