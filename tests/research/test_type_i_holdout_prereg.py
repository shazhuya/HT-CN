from __future__ import annotations

from htcn.research.type_i_holdout_prereg import build_type_i_holdout_preregistration


def _timing(selected: str | None) -> dict:
    return {
        "status": "type_i_exit_timing_evidence_holdout_sealed",
        "selected_hypothesis": selected,
        "eligible_for_preregistration": selected is not None,
        "holdout": {"sealed": True, "records": 355, "outcomes_exposed": False},
    }


def test_preregistration_freezes_t5_primary_contrast_without_opening_holdout() -> None:
    report = build_type_i_holdout_preregistration(
        _timing("full_prz_exit_by_t5"),
        dataset_id="a-share-research-v1",
        snapshot_cutoff="2026-09-15",
        source_commit="abc123",
    )
    assert report["status"] == "type_i_holdout_test_preregistered_sealed"
    assert report["selected_hypothesis"] == "full_prz_exit_by_t5"
    assert report["primary_contrast"]["exposure"]["name"] == "full_prz_exit_by_t5"
    assert report["primary_contrast"]["comparator"]["name"] == "no_full_exit_by_t5"
    assert report["confirmatory_test"]["minimum_records_per_group"] == 20
    assert "> 0" in report["confirmatory_test"]["success_criterion"]
    assert report["holdout"]["outcomes_exposed"] is False
    assert report["holdout_open_authorized"] is False
    assert report["policy_frozen"] is False


def test_preregistration_uses_incremental_fast_vs_late_contrast_for_t3() -> None:
    report = build_type_i_holdout_preregistration(
        _timing("full_prz_exit_by_t3"),
        dataset_id="a-share-research-v1",
        snapshot_cutoff="2026-09-15",
    )
    assert report["primary_contrast"]["exposure"]["name"] == "exit_by_t3"
    assert report["primary_contrast"]["comparator"]["name"] == "exit_on_t4_t5"
    assert report["multiplicity"]["primary_tests"] == 1


def test_preregistration_refuses_to_exist_without_visible_selection() -> None:
    report = build_type_i_holdout_preregistration(
        _timing(None),
        dataset_id="a-share-research-v1",
        snapshot_cutoff="2026-09-15",
    )
    assert report["status"] == "type_i_holdout_preregistration_not_ready"
    assert report["holdout_open_authorized"] is False
    assert report["holdout"]["outcomes_exposed"] is False
