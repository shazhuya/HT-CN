from __future__ import annotations

from htcn.research.type_i_holdout_eval import (
    evaluate_preregistered_type_i_holdout,
    newcombe_difference_interval,
    wilson_interval,
)


def _terminal_calibration() -> dict:
    return {
        "status": "terminal_bar_calibration_holdout_sealed",
        "boundaries": {
            "train_end": "2020-01-31",
            "validation_start": "2020-02-01",
            "validation_end": "2020-02-29",
            "holdout_start": "2020-03-01",
        },
    }


def _prereg() -> dict:
    return {
        "preregistration_id": "m2-type-i-holdout-v1",
        "selected_hypothesis": "full_prz_exit_by_t5",
        "primary_contrast": {
            "exposure": {"name": "full_prz_exit_by_t5"},
            "comparator": {"name": "no_full_exit_by_t5"},
            "endpoint": "First T2 hit from T+6 through T+20.",
        },
        "confirmatory_test": {
            "z": 1.959963984540054,
            "minimum_records_per_group": 20,
        },
    }


def _authorization(enabled: bool = True) -> dict:
    return {
        "authorization_id": "m2-type-i-holdout-open-v1",
        "preregistration_id": "m2-type-i-holdout-v1",
        "frozen_preregistration_commit": "286eead8b3fa1afa1e716161366b8edcf2c555b2",
        "authorized": enabled,
        "one_time_holdout_open": enabled,
    }


def _row(index: int, *, exposure: bool, hit: bool) -> dict:
    return {
        "instrument_id": f"SSE.{600000 + index:06d}",
        "pattern_id": "bat",
        "pattern_family": "XABCD",
        "schema": "XABCD",
        "direction": "bullish" if index % 2 == 0 else "bearish",
        "source_scale": 5 if index % 3 else 8,
        "terminal_bar_audit": {
            "status": "terminal_price_bar_observed",
            "terminal_bar": index,
            "terminal_trade_date": "2020-03-02",
            "reaction_observation_end_trade_date": "2020-03-27",
            "available_future_bars_after_terminal": 40,
            "bars_from_terminal_to_t1": None,
            "bars_from_terminal_to_t2": 8 if hit else None,
            "bars_from_terminal_to_full_prz_exit": 3 if exposure else None,
            "prz_overlap_within_t_plus_3": False,
            "prz_overlap_within_t_plus_5": False,
        },
    }


def test_newcombe_reference_values() -> None:
    low, high = wilson_interval(50, 100, z=1.959963984540054)
    assert abs(low - 0.4038315303659956) < 1e-12
    assert abs(high - 0.5961684696340044) < 1e-12
    diff_low, diff_high = newcombe_difference_interval(
        50, 100, 30, 100, z=1.959963984540054
    )
    assert abs(diff_low - 0.06422327745160028) < 1e-12
    assert abs(diff_high - 0.32576829087642145) < 1e-12


def test_one_time_holdout_confirms_only_fixed_primary_contrast() -> None:
    records = []
    # exposure: 15/30 endpoints; comparator: 3/30 endpoints
    for i in range(30):
        records.append(_row(i, exposure=True, hit=i < 15))
    for i in range(30, 60):
        records.append(_row(i, exposure=False, hit=(i - 30) < 3))

    report = evaluate_preregistered_type_i_holdout(
        records,
        _terminal_calibration(),
        _prereg(),
        _authorization(),
    )
    primary = report["primary_contrast"]
    assert report["status"] == "type_i_holdout_evaluated_once"
    assert report["holdout_opened"] is True
    assert primary["exposure"] == {"records": 30, "endpoint_hits": 15, "endpoint_rate": 0.5}
    assert primary["comparator"] == {"records": 30, "endpoint_hits": 3, "endpoint_rate": 0.1}
    assert primary["result"] == "confirmed"
    assert primary["newcombe_95_ci"]["lower"] > 0
    assert report["multiplicity"]["primary_tests_run"] == 1
    assert report["multiplicity"]["alternate_thresholds_searched"] is False
    assert report["policy_frozen"] is False


def test_holdout_refuses_to_open_without_separate_authorization() -> None:
    report = evaluate_preregistered_type_i_holdout(
        [],
        _terminal_calibration(),
        _prereg(),
        _authorization(False),
    )
    assert report["status"] == "type_i_holdout_not_opened"
    assert report["holdout_opened"] is False
