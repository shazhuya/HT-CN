from __future__ import annotations

from htcn.research.type_i_robustness import build_type_i_early_path_robustness_report


def _record(
    symbol: str,
    pattern_id: str,
    direction: str,
    terminal_date: str,
    observation_end: str,
    terminal_bar: int,
    *,
    t2: int | None,
    exit_bar: int | None,
    overlap3: bool,
    overlap5: bool,
    scale: int = 5,
) -> dict:
    return {
        "instrument_id": symbol,
        "pattern_id": pattern_id,
        "schema": "XABCD" if pattern_id != "abcd" else "ABCD",
        "direction": direction,
        "source_scale": scale,
        "terminal_bar_audit": {
            "status": "terminal_price_bar_observed",
            "terminal_bar": terminal_bar,
            "terminal_trade_date": terminal_date,
            "reaction_observation_end_trade_date": observation_end,
            "available_future_bars_after_terminal": 40,
            "bars_from_terminal_to_t1": None,
            "bars_from_terminal_to_t2": t2,
            "bars_from_terminal_to_full_prz_exit": exit_bar,
            "prz_overlap_within_t_plus_3": overlap3,
            "prz_overlap_within_t_plus_5": overlap5,
        },
    }


def _calibration() -> dict:
    return {
        "status": "terminal_bar_calibration_holdout_sealed",
        "boundaries": {
            "train_end": "2020-01-31",
            "validation_start": "2020-02-01",
            "validation_end": "2020-02-29",
            "holdout_start": "2020-03-01",
        },
        "split_counts": {"train": 6, "validation": 4, "holdout": 2},
    }


def _early_path() -> dict:
    names = [
        "full_prz_exit_by_t3",
        "full_prz_exit_by_t5",
        "no_prz_overlap_through_t3",
        "no_prz_overlap_through_t5",
        "exit_by_t3_and_no_overlap_through_t3",
        "exit_by_t5_and_no_overlap_through_t5",
    ]
    return {
        "status": "type_i_early_path_evidence_holdout_sealed",
        "split_counts": {"train": 6, "validation": 4, "holdout": 2},
        "cohorts": [{"name": name} for name in names],
        "holdout": {"sealed": True, "records": 2, "outcomes_exposed": False},
    }


def test_type_i_robustness_uses_landmark_progression_and_keeps_holdout_sealed() -> None:
    records = [
        _record("SSE.600001", "bat", "bullish", "2020-01-02", "2020-01-22", 10, t2=8, exit_bar=2, overlap3=False, overlap5=False, scale=3),
        _record("SSE.600002", "abcd", "bearish", "2020-01-04", "2020-01-24", 20, t2=9, exit_bar=3, overlap3=False, overlap5=False, scale=5),
        _record("SSE.600003", "bat", "bullish", "2020-01-06", "2020-01-26", 30, t2=10, exit_bar=2, overlap3=True, overlap5=True, scale=8),
        _record("SSE.600004", "abcd", "bearish", "2020-01-08", "2020-01-28", 40, t2=None, exit_bar=None, overlap3=True, overlap5=True, scale=3),
        _record("SSE.600005", "bat", "bullish", "2020-01-10", "2020-01-29", 50, t2=None, exit_bar=None, overlap3=True, overlap5=True, scale=5),
        _record("SSE.600006", "abcd", "bearish", "2020-01-12", "2020-01-30", 60, t2=None, exit_bar=None, overlap3=True, overlap5=True, scale=8),
        _record("SSE.600007", "bat", "bullish", "2020-02-02", "2020-02-20", 70, t2=8, exit_bar=2, overlap3=False, overlap5=False, scale=3),
        _record("SSE.600008", "abcd", "bearish", "2020-02-04", "2020-02-22", 80, t2=9, exit_bar=3, overlap3=False, overlap5=False, scale=5),
        _record("SSE.600009", "bat", "bullish", "2020-02-06", "2020-02-24", 90, t2=None, exit_bar=None, overlap3=True, overlap5=True, scale=3),
        _record("SSE.600010", "abcd", "bearish", "2020-02-08", "2020-02-26", 100, t2=None, exit_bar=None, overlap3=True, overlap5=True, scale=5),
        _record("SSE.600011", "bat", "bullish", "2020-03-02", "2020-03-22", 110, t2=6, exit_bar=1, overlap3=False, overlap5=False),
        _record("SSE.600012", "abcd", "bearish", "2020-03-04", "2020-03-24", 120, t2=None, exit_bar=None, overlap3=True, overlap5=True),
    ]

    report = build_type_i_early_path_robustness_report(
        records,
        _calibration(),
        _early_path(),
        minimum_train_candidate_pending=1,
        minimum_validation_candidate_pending=1,
    )

    assert report["status"] == "type_i_early_path_robustness_holdout_sealed"
    assert report["holdout"] == {"sealed": True, "records": 2, "outcomes_exposed": False}
    assert report["anti_leakage"]["holdout_outcomes_opened"] is False
    assert report["split_consistency_with_m2_18"]["matches"] is True

    cohorts = {row["name"]: row for row in report["cohorts"]}
    exit3 = cohorts["full_prz_exit_by_t3"]
    assert exit3["train"]["baseline"]["pending_records"] == 6
    assert exit3["train"]["baseline"]["later_t2_rate"] == 0.5
    assert exit3["train"]["gated"]["pending_records"] == 3
    assert exit3["train"]["gated"]["later_t2_rate"] == 1.0
    assert exit3["train"]["later_t2_lift"] == 0.5
    assert exit3["validation"]["later_t2_lift"] == 0.5

    families = {
        row["value"] for row in exit3["family_stability"]["details"]
    }
    assert {"ABCD", "XABCD"}.issubset(families)
    assert "holdout" not in exit3
    assert exit3["eligible_for_policy_freeze"] is False


def test_type_i_robustness_stays_closed_when_prior_stage_not_ready() -> None:
    report = build_type_i_early_path_robustness_report(
        [],
        {"status": "terminal_bar_sample_insufficient_holdout_sealed"},
        {"status": "type_i_early_path_not_ready_holdout_sealed"},
    )
    assert report["status"] == "type_i_early_path_robustness_not_ready_holdout_sealed"
    assert report["holdout"]["sealed"] is True
    assert report["robust_candidates"] == []
    assert report["policy_frozen"] is False
