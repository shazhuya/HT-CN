from __future__ import annotations

from copy import deepcopy

import pandas as pd
import pytest

from htcn.research.outcome_evaluator import (
    canonical_market_path_hash,
    evaluate_candidate_outcome,
)


BASIS = "qfq:" + "1" * 64
METHOD = "a" * 64


def _summary(
    *,
    direction: str = "bullish",
    schema: str = "ABCD",
    source_low: float = 95.0,
    source_high: float = 97.0,
    anchor_price: float = 110.0,
    enrollment: str = "2026-09-17",
) -> dict:
    return {
        "candidate_key": "SSE.600000|ABCD|abcd|bullish|S5|A:2026-09-01",
        "instrument_id": "SSE.600000",
        "outcome_enrollment_trade_date": enrollment,
        "enrollment_price_mode": "qfq",
        "enrollment_price_basis_id": BASIS,
        "price_basis_drift_snapshot_count": 0,
        "first_source_terminal_trade_date": None,
        "first_lifecycle_state_observed": {
            "approaching_source_prz": enrollment,
        },
        "enrollment_source_clock_seed": {
            "pattern_id": "shark" if schema == "0XABC" else "abcd",
            "schema": schema,
            "direction": direction,
            "scale": 5,
            "source_lifecycle_state": "approaching_source_prz",
            "source_prz_low": source_low,
            "source_prz_high": source_high,
            "source_signal_trade_date": "2026-09-16",
            "source_signal_clock_basis": (
                "last_frontier_pivot_confirmed_at=index+scale"
            ),
            "source_reaction_anchor_label": (
                "B" if schema == "0XABC" else "A"
            ),
            "source_reaction_anchor_price": anchor_price,
        },
    }


def _frame(rows: list[tuple[str, float, float, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "trade_date": day,
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": 1000.0 + index,
            }
            for index, (day, open_, high, low, close) in enumerate(rows)
        ]
    )


def _bullish_type_ii_frame() -> pd.DataFrame:
    return _frame([
        ("2026-09-16", 105.0, 107.0, 103.0, 106.0),
        ("2026-09-17", 100.0, 102.0, 98.0, 99.0),
        ("2026-09-18", 98.0, 99.0, 95.0, 96.0),
        ("2026-09-21", 96.0, 98.0, 94.0, 97.0),
        ("2026-09-22", 99.0, 101.0, 98.0, 100.0),
        ("2026-09-23", 101.0, 105.0, 100.0, 104.0),
        ("2026-09-24", 99.0, 101.0, 96.0, 98.0),
        ("2026-09-25", 97.0, 99.0, 95.0, 96.0),
        ("2026-09-28", 99.0, 102.0, 98.0, 101.0),
    ])


def test_bullish_source_events_reuse_core_and_start_windows_at_t_plus_1() -> None:
    result = evaluate_candidate_outcome(
        _summary(),
        _bullish_type_ii_frame(),
        outcome_as_of_trade_date="2026-09-28",
        current_price_mode="qfq",
        current_price_basis_id=BASIS,
        methodology_fingerprint=METHOD,
    )
    assert result["status"] == "source_outcome_observed"
    events = result["source_events"]
    assert events["source_terminal_trade_date"] == "2026-09-18"
    assert events["source_terminal_price"] == 95.0
    assert events["type_i_382_first_hit_offset"] == 2
    assert events["type_i_618_first_hit_offset"] == 3
    assert events["type_i_early_result"] == "confirmed_38_2_within_5"
    assert events["first_source_prz_exit_trade_date"] == "2026-09-22"
    assert events["type_ii_retest_entry_trade_date"] == "2026-09-24"
    assert events["type_ii_terminal_trade_date"] == "2026-09-25"
    assert events["post_type_ii_reversal_exit_trade_date"] == "2026-09-28"
    assert events["type_ii_price_structure_status"] == (
        "post_terminal_reversal_exit_observed"
    )
    assert events["full_carney_type_ii_reversal_claim_allowed"] is False

    window = result["descriptive_path_windows"]["5"]
    assert window["status"] == "mature"
    assert window["first_trade_date"] == "2026-09-21"
    assert window["last_trade_date"] == "2026-09-25"
    assert window["metrics"]["mfe_price"] == 10.0
    assert window["metrics"]["mae_price"] == 1.0
    assert result["descriptive_path_windows"]["10"]["status"] == "immature"
    assert result["source_reconstruction"]["duplicate_formula_implementation_used"] is False


def test_terminal_not_observed_is_right_censored_not_failure() -> None:
    frame = _frame([
        ("2026-09-16", 105.0, 107.0, 103.0, 106.0),
        ("2026-09-17", 100.0, 102.0, 98.0, 99.0),
        ("2026-09-18", 100.0, 103.0, 98.0, 102.0),
        ("2026-09-21", 101.0, 104.0, 98.0, 103.0),
    ])
    result = evaluate_candidate_outcome(
        _summary(),
        frame,
        outcome_as_of_trade_date="2026-09-21",
        current_price_mode="qfq",
        current_price_basis_id=BASIS,
        methodology_fingerprint=METHOD,
    )
    assert result["status"] == "right_censored_ongoing"
    assert result["censoring_state"] == "terminal_not_observed"
    assert result["source_events"]["source_terminal_observed"] is False
    assert result["descriptive_path_windows"] == {}


def test_terminal_on_enrollment_date_is_evidence_contradiction() -> None:
    frame = _frame([
        ("2026-09-16", 105.0, 107.0, 103.0, 106.0),
        ("2026-09-17", 98.0, 99.0, 95.0, 96.0),
        ("2026-09-18", 99.0, 101.0, 98.0, 100.0),
    ])
    result = evaluate_candidate_outcome(
        _summary(),
        frame,
        outcome_as_of_trade_date="2026-09-18",
        current_price_mode="qfq",
        current_price_basis_id=BASIS,
        methodology_fingerprint=METHOD,
    )
    assert result["status"] == "evidence_contradiction"
    assert "on or before" in result["contradiction"]
    assert result["source_events"]["source_terminal_trade_date"] == (
        "2026-09-17"
    )


def test_basis_drift_blocks_recalculation_even_when_current_id_matches() -> None:
    summary = _summary()
    summary["price_basis_drift_snapshot_count"] = 1
    summary["first_source_terminal_trade_date"] = "2026-09-18"
    result = evaluate_candidate_outcome(
        summary,
        _bullish_type_ii_frame(),
        outcome_as_of_trade_date="2026-09-28",
        current_price_mode="qfq",
        current_price_basis_id=BASIS,
        methodology_fingerprint=METHOD,
    )
    assert result["status"] == "unresolved_price_basis_interruption"
    assert result["observed_price_basis_drift"] is True
    assert result["captured_pre_drift_facts"][
        "first_source_terminal_trade_date"
    ] == "2026-09-18"
    assert result["descriptive_path_windows"] == {}


def test_current_basis_mismatch_blocks_source_price_comparison() -> None:
    result = evaluate_candidate_outcome(
        _summary(),
        _bullish_type_ii_frame(),
        outcome_as_of_trade_date="2026-09-28",
        current_price_mode="qfq",
        current_price_basis_id="qfq:" + "2" * 64,
        methodology_fingerprint=METHOD,
    )
    assert result["status"] == "unresolved_price_basis_interruption"
    assert result["price_basis_compatible"] is False


def test_missing_signal_date_is_unresolved_market_data() -> None:
    summary = _summary()
    summary["enrollment_source_clock_seed"][
        "source_signal_trade_date"
    ] = "2026-09-15"
    result = evaluate_candidate_outcome(
        summary,
        _bullish_type_ii_frame(),
        outcome_as_of_trade_date="2026-09-28",
        current_price_mode="qfq",
        current_price_basis_id=BASIS,
        methodology_fingerprint=METHOD,
    )
    assert result["status"] == "unresolved_missing_market_data"
    assert result["missing_market_dates"] == ["2026-09-15"]


def test_late_382_is_reaction_only_not_reclassified_as_early_confirm() -> None:
    frame = _frame([
        ("2026-09-16", 105.0, 107.0, 103.0, 106.0),
        ("2026-09-17", 100.0, 102.0, 98.0, 99.0),
        ("2026-09-18", 98.0, 99.0, 95.0, 96.0),
        ("2026-09-21", 96.0, 99.0, 95.0, 98.0),
        ("2026-09-22", 97.0, 100.0, 95.0, 99.0),
        ("2026-09-23", 98.0, 100.0, 95.0, 99.0),
        ("2026-09-24", 98.0, 100.0, 95.0, 99.0),
        ("2026-09-25", 98.0, 100.0, 95.0, 99.0),
        ("2026-09-28", 99.0, 101.0, 95.0, 100.0),
    ])
    result = evaluate_candidate_outcome(
        _summary(),
        frame,
        outcome_as_of_trade_date="2026-09-28",
        current_price_mode="qfq",
        current_price_basis_id=BASIS,
        methodology_fingerprint=METHOD,
    )
    events = result["source_events"]
    assert events["type_i_382_first_hit_offset"] == 6
    assert events["type_i_early_result"] == "failed_38_2_within_5"
    assert events["reaction_only_later_382"] is True


def test_bearish_excursion_and_target_direction_are_symmetric() -> None:
    summary = _summary(
        direction="bearish",
        source_low=103.0,
        source_high=105.0,
        anchor_price=90.0,
    )
    frame = _frame([
        ("2026-09-16", 95.0, 97.0, 93.0, 96.0),
        ("2026-09-17", 100.0, 102.0, 98.0, 101.0),
        ("2026-09-18", 103.0, 105.0, 102.0, 104.0),
        ("2026-09-21", 103.0, 104.0, 101.0, 102.0),
        ("2026-09-22", 101.0, 102.0, 99.0, 100.0),
        ("2026-09-23", 98.0, 100.0, 95.0, 96.0),
        ("2026-09-24", 97.0, 101.0, 96.0, 100.0),
        ("2026-09-25", 101.0, 105.0, 100.0, 104.0),
        ("2026-09-28", 101.0, 102.0, 98.0, 99.0),
    ])
    result = evaluate_candidate_outcome(
        summary,
        frame,
        outcome_as_of_trade_date="2026-09-28",
        current_price_mode="qfq",
        current_price_basis_id=BASIS,
        methodology_fingerprint=METHOD,
    )
    events = result["source_events"]
    assert events["source_terminal_price"] == 105.0
    assert events["type_i_382_first_hit_offset"] == 2
    assert events["type_i_618_first_hit_offset"] == 3
    window = result["descriptive_path_windows"]["5"]
    assert window["status"] == "mature"
    assert window["metrics"]["mfe_price"] == 10.0
    assert window["metrics"]["mae_price"] == 0.0


def test_shark_generic_type_i_is_never_exposed_as_management_target() -> None:
    summary = _summary(schema="0XABC")
    result = evaluate_candidate_outcome(
        summary,
        _bullish_type_ii_frame(),
        outcome_as_of_trade_date="2026-09-28",
        current_price_mode="qfq",
        current_price_basis_id=BASIS,
        methodology_fingerprint=METHOD,
    )
    assert result["source_events"]["target_382"] is not None
    assert result["interpretation"][
        "shark_generic_type_i_is_management_target"
    ] is False
    assert "shark_management_target" not in result


def test_market_path_hash_is_deterministic_and_detects_ohlcv_mutation() -> None:
    frame = _bullish_type_ii_frame()
    first = canonical_market_path_hash(frame, price_basis_id=BASIS)
    second = canonical_market_path_hash(
        frame.copy(),
        price_basis_id=BASIS,
    )
    changed = frame.copy()
    changed.loc[changed.index[-1], "close"] = 100.5
    third = canonical_market_path_hash(changed, price_basis_id=BASIS)
    assert first == second
    assert first != third


def test_outcome_result_does_not_define_pnl_win_rate_or_alpha() -> None:
    result = evaluate_candidate_outcome(
        _summary(),
        _bullish_type_ii_frame(),
        outcome_as_of_trade_date="2026-09-28",
        current_price_mode="qfq",
        current_price_basis_id=BASIS,
        methodology_fingerprint=METHOD,
    )
    serialized = str(result)
    for forbidden in (
        "execution_pnl",
        "win_loss_label",
        "win_rate",
        "benchmark_alpha",
    ):
        assert result["interpretation"].get(
            forbidden + "_computed",
            result["interpretation"].get(forbidden + "_defined", False),
        ) is False
    assert "buy_sell_ranking" not in serialized


def test_invalid_partial_seed_fails_closed() -> None:
    summary = _summary()
    broken = deepcopy(summary)
    broken["enrollment_source_clock_seed"].pop(
        "source_reaction_anchor_price"
    )
    with pytest.raises(ValueError, match="seed missing fields"):
        evaluate_candidate_outcome(
            broken,
            _bullish_type_ii_frame(),
            outcome_as_of_trade_date="2026-09-28",
            current_price_mode="qfq",
            current_price_basis_id=BASIS,
            methodology_fingerprint=METHOD,
        )
