from __future__ import annotations

from htcn.research.type_i_confirmation import build_type_i_early_path_report


def _record(symbol: str, terminal_date: str, observation_end: str, terminal_bar: int, t1: int | None, t2: int | None, exit_bar: int | None, overlap3: bool, overlap5: bool) -> dict:
    return {
        "instrument_id": symbol,
        "pattern_id": "bat",
        "schema": "XABCD",
        "direction": "bullish",
        "source_scale": 5,
        "terminal_bar_audit": {
            "status": "terminal_price_bar_observed",
            "terminal_bar": terminal_bar,
            "terminal_trade_date": terminal_date,
            "reaction_observation_end_trade_date": observation_end,
            "available_future_bars_after_terminal": 40,
            "bars_from_terminal_to_t1": t1,
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
        "split_counts": {"train": 4, "validation": 3, "holdout": 2},
    }


def test_type_i_early_path_reuses_terminal_boundaries_and_seals_holdout() -> None:
    records = [
        _record("SSE.600001", "2020-01-02", "2020-01-22", 10, 3, 8, 2, False, False),
        _record("SSE.600002", "2020-01-04", "2020-01-24", 20, 6, None, 4, True, False),
        _record("SSE.600003", "2020-01-06", "2020-01-26", 30, None, None, None, True, True),
        _record("SSE.600004", "2020-01-08", "2020-01-28", 40, 2, 4, 1, False, False),
        _record("SSE.600005", "2020-02-02", "2020-02-22", 50, 4, 9, 2, False, False),
        _record("SSE.600006", "2020-02-04", "2020-02-24", 60, 7, None, 5, True, False),
        _record("SSE.600007", "2020-02-06", "2020-02-26", 70, None, None, None, True, True),
        _record("SSE.600008", "2020-03-02", "2020-03-22", 80, 1, 2, 1, False, False),
        _record("SSE.600009", "2020-03-04", "2020-03-24", 90, None, None, None, True, True),
    ]
    report = build_type_i_early_path_report(records, _calibration())
    assert report["status"] == "type_i_early_path_evidence_holdout_sealed"
    assert report["split_counts"] == {"train": 4, "validation": 3, "holdout": 2}
    assert report["split_consistency_with_m2_17"]["matches"] is True
    assert report["holdout"] == {"sealed": True, "records": 2, "outcomes_exposed": False}
    assert report["anti_leakage"]["holdout_outcomes_opened"] is False
    assert report["eligible_for_policy_freeze"] is False
    train = report["baseline"]["train"]
    assert train["early_t1_by_landmark"] == 2
    assert train["early_t2_by_landmark"] == 1
    assert train["t2_pending_at_landmark"] == 3
    assert train["t2_first_hit_after_landmark_within_horizon"] == 1
    assert train["t2_after_landmark_rate_among_pending"] == 1 / 3
    cohorts = {row["name"]: row for row in report["cohorts"]}
    assert cohorts["full_prz_exit_by_t3"]["train"]["records"] == 2
    assert cohorts["exit_by_t3_and_no_overlap_through_t3"]["train"]["records"] == 2
    assert "holdout" not in cohorts["full_prz_exit_by_t3"]


def test_type_i_early_path_stays_closed_when_terminal_calibration_is_not_ready() -> None:
    report = build_type_i_early_path_report([], {"status": "terminal_bar_sample_insufficient_holdout_sealed"})
    assert report["status"] == "type_i_early_path_not_ready_holdout_sealed"
    assert report["holdout"]["sealed"] is True
    assert report["policy_frozen"] is False
