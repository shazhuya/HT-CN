from __future__ import annotations

from datetime import date, timedelta

from htcn.research.completed_reaction_robustness import build_completed_reaction_robustness_report


def _row(
    index: int,
    *,
    split: str,
    family: str = "ABCD",
    scale: int = 3,
    geometry: float = 95.0,
    hit_t1: bool = True,
    hit_t2: bool = False,
) -> dict:
    if split == "train":
        signal = date(2020, 1, 2) + timedelta(days=index * 5)
    elif split == "validation":
        signal = date(2020, 7, 2) + timedelta(days=index * 8)
    else:
        signal = date(2021, 1, 4) + timedelta(days=index * 8)
    if hit_t2:
        outcome_class = "t2_within_horizon"
    elif hit_t1:
        outcome_class = "t1_only_within_horizon"
    else:
        outcome_class = "no_t1_within_horizon"
    return {
        "instrument_id": f"SSE.60{index:04d}{split[0]}",
        "pattern_id": "abcd" if family == "ABCD" else "shark",
        "pattern_family": family,
        "schema": family,
        "direction": "bullish",
        "source_scale": scale,
        "geometry_score": geometry,
        "source_tolerance_used": None,
        "signal_trade_date": signal.isoformat(),
        "observation_end_trade_date": (signal + timedelta(days=2)).isoformat(),
        "confirmation_lag_bars": scale,
        "quality_at_signal": {"prz_width_ratio": 0.02},
        "outcome": {"outcome_class": outcome_class},
    }


def _calibration() -> dict:
    return {
        "status": "completed_reaction_calibration_holdout_sealed",
        "boundaries": {
            "train_end": "2020-06-30",
            "validation_start": "2020-07-01",
            "validation_end": "2020-12-31",
            "holdout_start": "2021-01-01",
        },
        "holdout": {"sealed": True, "records": 4, "outcomes_exposed": False},
    }


def _quality(candidate: str) -> dict:
    return {
        "status": "completed_reaction_quality_evidence_holdout_sealed",
        "thresholds": {
            "geometry_q50": 80.0,
            "geometry_q75": 90.0,
            "prz_width_q25": 0.01,
            "prz_width_q50": 0.02,
            "confirmation_lag_q25": 3.0,
            "confirmation_lag_q50": 5.0,
        },
        "consistent_t1_candidates": [candidate],
    }


def test_fast_confirmation_is_rejected_when_it_is_exact_scale_alias() -> None:
    records: list[dict] = []
    for index in range(18):
        scale = 3 if index % 2 == 0 else 5
        records.append(
            _row(
                index,
                split="train",
                family="ABCD" if index % 3 else "SHARK",
                scale=scale,
                hit_t1=(scale == 3 or index % 4 == 0),
                hit_t2=(scale == 3 and index % 4 == 0),
            )
        )
    for index in range(10):
        scale = 3 if index % 2 == 0 else 5
        records.append(
            _row(
                index,
                split="validation",
                family="ABCD" if index % 2 == 0 else "SHARK",
                scale=scale,
                hit_t1=(scale == 3),
                hit_t2=(scale == 3 and index % 4 == 0),
            )
        )
    sealed = _row(0, split="holdout")
    sealed["outcome"] = {"sealed": True}
    records.append(sealed)

    report = build_completed_reaction_robustness_report(
        records,
        _calibration(),
        _quality("fast_confirmation_q1"),
    )
    gate = report["gates"][0]
    assert report["holdout"]["outcomes_exposed"] is False
    assert report["holdout_opened"] is False
    assert gate["semantic_alias"]["is_scale_alias"] is True
    assert gate["effective_layer"] == "context_scale_alias"
    assert "confirmation_lag_is_scale_alias" in gate["blockers"]
    assert gate["eligible_for_policy_freeze"] is False
    assert report["robust_candidates"] == []


def test_family_instability_blocks_geometry_candidate_even_if_aggregate_is_positive() -> None:
    records: list[dict] = []
    # Aggregate geometry evidence is favorable, but SHARK moves the other way. This is the
    # exact counterexample M2.16 must reject instead of promoting an aggregate-only result.
    for index in range(10):
        records.append(
            _row(
                index,
                split="train",
                family="ABCD",
                scale=3 if index % 2 == 0 else 8,
                geometry=95.0 if index < 4 else 70.0,
                hit_t1=index < 4,
            )
        )
    for index in range(10, 20):
        records.append(
            _row(
                index,
                split="train",
                family="SHARK",
                scale=5 if index % 2 == 0 else 8,
                geometry=95.0 if index < 14 else 70.0,
                hit_t1=index in {14, 16},
            )
        )
    for index in range(6):
        records.append(
            _row(
                index,
                split="validation",
                family="ABCD",
                scale=3 if index % 2 == 0 else 8,
                geometry=95.0 if index < 2 else 70.0,
                hit_t1=index < 2,
            )
        )
    for index in range(6, 12):
        records.append(
            _row(
                index,
                split="validation",
                family="SHARK",
                scale=5 if index % 2 == 0 else 8,
                geometry=95.0 if index < 8 else 70.0,
                hit_t1=index in {8, 10},
            )
        )

    report = build_completed_reaction_robustness_report(
        records,
        _calibration(),
        _quality("geometry_top_quartile"),
    )
    gate = report["gates"][0]
    assert gate["train"]["t1_lift"] > 0
    assert gate["validation"]["t1_lift"] > 0
    assert gate["family_stability"]["jointly_eligible_families"] >= 2
    assert gate["family_stability"]["generalizes_across_families"] is False
    assert "family_generalization" in gate["blockers"]
    assert gate["robust_research_candidate"] is False


def test_not_ready_quality_report_does_not_open_holdout() -> None:
    report = build_completed_reaction_robustness_report(
        [],
        _calibration(),
        {"status": "completed_reaction_quality_sample_insufficient_holdout_sealed"},
    )
    assert report["status"] == "completed_reaction_robustness_not_ready_holdout_sealed"
    assert report["holdout_opened"] is False
    assert report["policy_frozen"] is False
