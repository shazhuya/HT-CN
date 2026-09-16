from __future__ import annotations

from htcn.research.type_i_external_replication import evaluate_external_type_i_replication


def _prereg() -> dict:
    return {
        "preregistration_id": "m2-type-i-external-replication-v1",
        "replication_dataset": {
            "dataset_id": "replication-test",
            "minimum_successful_symbols": 48,
        },
        "primary_contrast": {
            "exposure": {"name": "full_prz_exit_by_t5"},
            "comparator": {"name": "no_full_exit_by_t5"},
        },
        "endpoint": {
            "landmark_bar": 5,
            "reaction_horizon_bars": 20,
        },
        "confirmatory_test": {
            "z": 1.959963984540054,
            "minimum_records_per_group": 20,
        },
    }


def _row(index: int, *, exposure: bool, hit: bool, early_t2: bool = False) -> dict:
    t2 = 3 if early_t2 else (8 if hit else None)
    return {
        "instrument_id": f"SSE.{600000 + (index % 50):06d}",
        "pattern_id": "bat" if index % 2 == 0 else "gartley",
        "schema": "XABCD",
        "direction": "bullish" if index % 2 == 0 else "bearish",
        "source_scale": 5 if index % 3 else 8,
        "terminal_bar_audit": {
            "status": "terminal_price_bar_observed",
            "terminal_bar": index,
            "terminal_trade_date": "2020-01-02",
            "reaction_observation_end_trade_date": "2020-02-03",
            "available_future_bars_after_terminal": 30,
            "bars_from_terminal_to_t2": t2,
            "bars_from_terminal_to_full_prz_exit": 3 if exposure else None,
        },
    }


def test_external_replication_confirms_only_frozen_primary_contrast() -> None:
    records = []
    # exposure 18/30 vs comparator 3/30 produces a clearly positive difference.
    for i in range(30):
        records.append(_row(i, exposure=True, hit=i < 18))
    for i in range(30, 60):
        records.append(_row(i, exposure=False, hit=(i - 30) < 3))

    report = evaluate_external_type_i_replication(
        records,
        _prereg(),
        successful_symbols=50,
        requested_symbols=60,
    )
    primary = report["primary_contrast"]
    assert report["status"] == "external_type_i_replication_evaluated_once"
    assert report["coverage_ok"] is True
    assert primary["exposure"] == {
        "records": 30,
        "endpoint_hits": 18,
        "endpoint_rate": 0.6,
    }
    assert primary["comparator"] == {
        "records": 30,
        "endpoint_hits": 3,
        "endpoint_rate": 0.1,
    }
    assert primary["result"] == "confirmed"
    assert primary["newcombe_95_ci"]["lower"] > 0
    assert report["multiplicity"]["primary_tests_run"] == 1
    assert report["identity"]["carney_geometry_changed"] is False


def test_t2_hit_by_t5_is_excluded_before_group_assignment() -> None:
    records = [_row(i, exposure=True, hit=False, early_t2=True) for i in range(25)]
    records.extend(_row(i + 100, exposure=False, hit=False) for i in range(25))
    report = evaluate_external_type_i_replication(
        records,
        _prereg(),
        successful_symbols=60,
        requested_symbols=60,
    )
    assert report["mature_terminal_events"] == 50
    assert report["eligible_pending_t2_at_t5"] == 25
    assert report["primary_contrast"]["exposure"]["records"] == 0
    assert report["primary_contrast"]["result"] == "inconclusive"


def test_coverage_gate_forces_inconclusive_even_with_large_effect() -> None:
    records = []
    for i in range(25):
        records.append(_row(i, exposure=True, hit=i < 20))
        records.append(_row(i + 100, exposure=False, hit=i < 2))
    report = evaluate_external_type_i_replication(
        records,
        _prereg(),
        successful_symbols=47,
        requested_symbols=60,
    )
    assert report["coverage_ok"] is False
    assert report["primary_contrast"]["sample_floor_ok"] is True
    assert report["primary_contrast"]["result"] == "inconclusive"
    assert report["primary_contrast"]["newcombe_95_ci"] is None


def test_mature_horizon_filter_uses_source_aligned_terminal_events() -> None:
    mature = _row(1, exposure=True, hit=True)
    immature = _row(2, exposure=False, hit=True)
    immature["terminal_bar_audit"]["available_future_bars_after_terminal"] = 19
    report = evaluate_external_type_i_replication(
        [mature, immature],
        _prereg(),
        successful_symbols=60,
        requested_symbols=60,
    )
    assert report["mature_terminal_events"] == 1
    assert report["eligible_pending_t2_at_t5"] == 1
