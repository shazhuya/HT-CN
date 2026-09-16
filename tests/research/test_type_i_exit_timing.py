from __future__ import annotations

from htcn.research.type_i_exit_timing import build_type_i_exit_timing_report


def _row(symbol: str, date: str, terminal_bar: int, *, exit_bar: int | None, t2: int | None) -> dict:
    return {
        "instrument_id": symbol,
        "pattern_id": "bat",
        "pattern_family": "XABCD",
        "schema": "XABCD",
        "direction": "bullish",
        "source_scale": 5,
        "terminal_bar_audit": {
            "status": "terminal_price_bar_observed",
            "terminal_bar": terminal_bar,
            "terminal_trade_date": date,
            "reaction_observation_end_trade_date": date,
            "available_future_bars_after_terminal": 40,
            "bars_from_terminal_to_t1": None,
            "bars_from_terminal_to_t2": t2,
            "bars_from_terminal_to_full_prz_exit": exit_bar,
            "prz_overlap_within_t_plus_3": False,
            "prz_overlap_within_t_plus_5": False,
        },
    }


def _terminal_calibration() -> dict:
    return {
        "status": "terminal_bar_calibration_holdout_sealed",
        "boundaries": {
            "train_end": "2020-01-31",
            "validation_start": "2020-02-01",
            "validation_end": "2020-02-29",
            "holdout_start": "2020-03-01",
        },
        "split_counts": {"train": 6, "validation": 6, "holdout": 1},
    }


def _early_path() -> dict:
    return {
        "status": "type_i_early_path_evidence_holdout_sealed",
        "holdout": {"sealed": True, "records": 1, "outcomes_exposed": False},
    }


def _robustness() -> dict:
    return {
        "status": "type_i_early_path_robustness_holdout_sealed",
        "robust_candidates": ["full_prz_exit_by_t3", "full_prz_exit_by_t5"],
    }


def test_nested_exit_timing_selects_t5_when_late_exit_still_adds_value() -> None:
    records = [
        # Train: fast 1/2, late 2/2, no-exit 0/2.
        _row("SSE.600001", "2020-01-02", 10, exit_bar=2, t2=8),
        _row("SSE.600002", "2020-01-03", 11, exit_bar=3, t2=None),
        _row("SSE.600003", "2020-01-04", 12, exit_bar=4, t2=9),
        _row("SSE.600004", "2020-01-05", 13, exit_bar=5, t2=10),
        _row("SSE.600005", "2020-01-06", 14, exit_bar=None, t2=None),
        _row("SSE.600006", "2020-01-07", 15, exit_bar=8, t2=None),
        # Validation: fast 1/2, late 2/2, no-exit 0/2.
        _row("SSE.600007", "2020-02-02", 20, exit_bar=1, t2=8),
        _row("SSE.600008", "2020-02-03", 21, exit_bar=3, t2=None),
        _row("SSE.600009", "2020-02-04", 22, exit_bar=4, t2=7),
        _row("SSE.600010", "2020-02-05", 23, exit_bar=5, t2=11),
        _row("SSE.600011", "2020-02-06", 24, exit_bar=None, t2=None),
        _row("SSE.600012", "2020-02-07", 25, exit_bar=9, t2=None),
        _row("SSE.600013", "2020-03-02", 30, exit_bar=2, t2=8),
    ]

    report = build_type_i_exit_timing_report(
        records,
        _terminal_calibration(),
        _early_path(),
        _robustness(),
        minimum_train_exclusive=2,
        minimum_validation_exclusive=2,
    )

    assert report["status"] == "type_i_exit_timing_evidence_holdout_sealed"
    assert report["selected_hypothesis"] == "full_prz_exit_by_t5"
    assert report["decision_checks"]["exclusive_sample_floor_ok"] is True
    assert report["decision_checks"]["speed_advantage_fast_over_late_in_both_visible_splits"] is False
    assert report["decision_checks"]["late_exit_beats_no_exit_in_both_visible_splits"] is True
    assert report["holdout"] == {"sealed": True, "records": 1, "outcomes_exposed": False}
    assert report["eligible_for_policy_freeze"] is False


def test_nested_exit_timing_can_select_t3_when_speed_adds_incremental_value() -> None:
    records = [
        # Train: fast 2/2, late 1/2, no-exit 0/2.
        _row("SSE.600001", "2020-01-02", 10, exit_bar=2, t2=8),
        _row("SSE.600002", "2020-01-03", 11, exit_bar=3, t2=9),
        _row("SSE.600003", "2020-01-04", 12, exit_bar=4, t2=10),
        _row("SSE.600004", "2020-01-05", 13, exit_bar=5, t2=None),
        _row("SSE.600005", "2020-01-06", 14, exit_bar=None, t2=None),
        _row("SSE.600006", "2020-01-07", 15, exit_bar=8, t2=None),
        # Validation: same ordering.
        _row("SSE.600007", "2020-02-02", 20, exit_bar=1, t2=8),
        _row("SSE.600008", "2020-02-03", 21, exit_bar=3, t2=9),
        _row("SSE.600009", "2020-02-04", 22, exit_bar=4, t2=10),
        _row("SSE.600010", "2020-02-05", 23, exit_bar=5, t2=None),
        _row("SSE.600011", "2020-02-06", 24, exit_bar=None, t2=None),
        _row("SSE.600012", "2020-02-07", 25, exit_bar=9, t2=None),
        _row("SSE.600013", "2020-03-02", 30, exit_bar=2, t2=8),
    ]

    report = build_type_i_exit_timing_report(
        records,
        _terminal_calibration(),
        _early_path(),
        _robustness(),
        minimum_train_exclusive=2,
        minimum_validation_exclusive=2,
    )
    assert report["selected_hypothesis"] == "full_prz_exit_by_t3"
    assert report["decision_checks"]["speed_advantage_fast_over_late_in_both_visible_splits"] is True
    assert report["eligible_for_preregistration"] is True


def test_exit_timing_stays_closed_when_nested_robustness_prerequisite_missing() -> None:
    report = build_type_i_exit_timing_report(
        [],
        _terminal_calibration(),
        _early_path(),
        {"status": "type_i_early_path_robustness_holdout_sealed", "robust_candidates": []},
    )
    assert report["status"] == "type_i_exit_timing_not_ready_holdout_sealed"
    assert report["selected_hypothesis"] is None
    assert report["holdout_opened"] is False
