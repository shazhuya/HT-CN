from __future__ import annotations

import pytest

from htcn.app.daily_review_digest import (
    build_daily_review_digest,
    filter_daily_review_digest,
)


def _change(
    *,
    instrument: str,
    key: str,
    change_types: list[str],
    previous_action: str | None,
    current_action: str | None,
    previous_lifecycle: str | None = "waiting_terminal",
    current_lifecycle: str | None = "t_plus_1",
) -> dict:
    previous = (
        None
        if previous_action is None
        else {
            "display_key": key,
            "instrument_id": instrument,
            "pattern_id": "bat",
            "schema": "XABCD",
            "direction": "bullish",
            "scale": 5,
            "pattern_state": "forming",
            "action_state": previous_action,
            "lifecycle_state": previous_lifecycle,
            "next_key_price": 100.0,
            "next_key_price_role": "source_prz_entry_edge",
            "execution_context_gate": "tradable",
            "context_cautions": [],
            "current_position": "before",
            "first_watch": "before",
            "upgrade_blocker": "before",
        }
    )
    current = (
        None
        if current_action is None
        else {
            "display_key": key,
            "instrument_id": instrument,
            "pattern_id": "bat",
            "schema": "XABCD",
            "direction": "bullish",
            "scale": 5,
            "pattern_state": "forming",
            "action_state": current_action,
            "lifecycle_state": current_lifecycle,
            "next_key_price": 110.0,
            "next_key_price_role": "type_i_38_2_target",
            "execution_context_gate": "tradable",
            "context_cautions": [],
            "current_position": "after",
            "first_watch": "after",
            "upgrade_blocker": "after",
        }
    )
    return {
        "display_key": key,
        "instrument_id": instrument,
        "change_types": change_types,
        "previous": previous,
        "current": current,
    }


def _history(changes: list[dict], *, incomplete: list[str] | None = None) -> dict:
    return {
        "schema_version": 1,
        "contract": {
            "version": 1,
            "semantics": "product_observation_only",
        },
        "filter": {},
        "observation_count": 1,
        "observations": [{
            "trade_date": "2026-09-18",
            "observation_id": "a" * 64,
            "revision_ordinal": 2,
            "source_generated_at_utc": "2026-09-18T09:00:00+00:00",
            "previous_recorded_trade_date": "2026-09-17",
            "queue_candidate_count": 100,
            "delta_total_change_count": len(changes),
            "item_count": 100,
            "items": [],
            "change_count": len(changes),
            "changes": changes,
            "delta_status": "ready",
            "comparison_incomplete_instruments": incomplete or [],
        }],
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "historical_outcome_used_for_ranking": False,
        "alpha_inference_allowed": False,
        "is_trade_instruction": False,
    }


def test_digest_orders_by_frozen_workflow_not_return_expectation() -> None:
    changes = [
        _change(
            instrument="SSE.3",
            key="k3",
            change_types=["lifecycle_state_changed"],
            previous_action="waiting",
            current_action="waiting",
        ),
        _change(
            instrument="SSE.1",
            key="k1",
            change_types=["action_state_changed", "lifecycle_state_changed"],
            previous_action="reaction_observation",
            current_action="execution_evaluation",
        ),
        _change(
            instrument="SSE.2",
            key="k2",
            change_types=["next_key_changed"],
            previous_action="reaction_observation",
            current_action="reaction_observation",
        ),
    ]

    payload = build_daily_review_digest(_history(changes))

    assert payload["status"] == "changes_ready"
    assert payload["review_ready"] is True
    assert payload["change_count"] == 3
    assert [
        section["workflow_bucket"]
        for section in payload["workflow_sections"]
    ] == [
        "execution_evaluation",
        "reaction_observation",
        "waiting",
    ]
    assert payload["ordering_is_product_workflow_not_expected_return"] is True
    assert payload["historical_outcome_used_for_ranking"] is False
    assert payload["predictive_score_used"] is False
    assert payload["alpha_inference_allowed"] is False
    assert payload["is_trade_instruction"] is False


def test_digest_retains_multi_type_change_without_scoring() -> None:
    payload = build_daily_review_digest(
        _history([
            _change(
                instrument="SSE.1",
                key="k1",
                change_types=[
                    "action_state_changed",
                    "lifecycle_state_changed",
                    "next_key_changed",
                    "context_cautions_changed",
                ],
                previous_action="waiting",
                current_action="reaction_observation",
            )
        ])
    )

    assert payload["change_count"] == 1
    assert payload["change_type_counts"] == {
        "action_state_changed": 1,
        "lifecycle_state_changed": 1,
        "next_key_changed": 1,
        "context_cautions_changed": 1,
    }
    item = payload["workflow_sections"][0]["items"][0]
    assert item["change_types"] == [
        "action_state_changed",
        "lifecycle_state_changed",
        "next_key_changed",
        "context_cautions_changed",
    ]


def test_disappeared_candidate_gets_explicit_non_predictive_bucket() -> None:
    payload = build_daily_review_digest(
        _history([
            _change(
                instrument="SSE.9",
                key="gone",
                change_types=["disappeared_candidate"],
                previous_action="waiting",
                current_action=None,
            )
        ])
    )

    assert payload["workflow_bucket_counts"] == {
        "disappeared_candidate": 1,
    }
    section = payload["workflow_sections"][0]
    assert section["workflow_bucket"] == "disappeared_candidate"
    assert section["items"][0]["current"] is None


def test_analysis_gaps_are_separate_from_candidate_disappearance() -> None:
    payload = build_daily_review_digest(
        _history([], incomplete=["SSE.600000", "SZSE.000001"])
    )

    assert payload["status"] == "no_changes_with_analysis_gaps"
    assert payload["change_count"] == 0
    assert payload["analysis_incomplete_count"] == 2
    assert payload["analysis_incomplete_instruments"] == [
        "SSE.600000",
        "SZSE.000001",
    ]


def test_baseline_day_is_ready_but_has_no_cross_day_change() -> None:
    source = _history([])
    source["observations"][0]["delta_status"] = (
        "baseline_no_previous_observation"
    )
    source["observations"][0]["previous_recorded_trade_date"] = None

    payload = build_daily_review_digest(source)

    assert payload["status"] == "baseline"
    assert payload["review_ready"] is True
    assert payload["change_count"] == 0


def test_no_history_is_not_review_ready() -> None:
    source = _history([])
    source["observation_count"] = 0
    source["observations"] = []

    payload = build_daily_review_digest(source)

    assert payload["status"] == "no_history"
    assert payload["review_ready"] is False


def test_history_boundary_violation_fails_closed() -> None:
    source = _history([])
    source["alpha_inference_allowed"] = True

    with pytest.raises(ValueError, match="boundary violation"):
        build_daily_review_digest(source)


def test_presentation_filter_does_not_change_source_totals() -> None:
    source = build_daily_review_digest(
        _history([
            _change(
                instrument="SSE.1",
                key="k1",
                change_types=["lifecycle_state_changed"],
                previous_action="waiting",
                current_action="execution_evaluation",
            ),
            _change(
                instrument="SSE.2",
                key="k2",
                change_types=["next_key_changed"],
                previous_action="reaction_observation",
                current_action="reaction_observation",
            ),
        ])
    )

    filtered = filter_daily_review_digest(
        source,
        workflow_bucket="reaction_observation",
        change_type="next_key_changed",
        instrument_id="sse.2",
    )

    assert filtered["filtered_change_count"] == 1
    assert filtered["source_change_count_unchanged"] == 2
    assert filtered["change_count"] == 2
    assert filtered["filtered_workflow_sections"][0]["items"][0][
        "instrument_id"
    ] == "SSE.2"


def test_digest_rejects_non_exhaustive_history_delta() -> None:
    source = _history([
        _change(
            instrument="SSE.1",
            key="k1",
            change_types=["lifecycle_state_changed"],
            previous_action="waiting",
            current_action="reaction_observation",
        )
    ])
    source["observations"][0]["delta_total_change_count"] = 2

    with pytest.raises(ValueError, match="not an exhaustive"):
        build_daily_review_digest(source)


def test_presentation_filter_rejects_unknown_bucket_and_change_type() -> None:
    source = build_daily_review_digest(_history([]))

    with pytest.raises(ValueError, match="unknown review workflow bucket"):
        filter_daily_review_digest(
            source,
            workflow_bucket="best_opportunity",
        )

    with pytest.raises(ValueError, match="unknown review change type"):
        filter_daily_review_digest(
            source,
            change_type="profit_probability_changed",
        )
