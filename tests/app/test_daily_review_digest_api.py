from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

import services.api.main as api


def _digest() -> dict:
    return {
        "schema_version": 1,
        "status": "changes_ready",
        "review_ready": True,
        "trade_date": "2026-09-18",
        "source_observation_id": "a" * 64,
        "source_revision_ordinal": 1,
        "previous_recorded_trade_date": "2026-09-17",
        "delta_status": "ready",
        "change_count": 2,
        "change_type_counts": {
            "lifecycle_state_changed": 1,
            "next_key_changed": 1,
        },
        "workflow_bucket_counts": {
            "execution_evaluation": 1,
            "reaction_observation": 1,
        },
        "workflow_sections": [
            {
                "workflow_bucket": "execution_evaluation",
                "change_count": 1,
                "items": [{
                    "display_key": "k1",
                    "instrument_id": "SSE.688256",
                    "review_bucket": "execution_evaluation",
                    "change_types": ["lifecycle_state_changed"],
                    "previous": {"lifecycle_state": "t_plus_1"},
                    "current": {"lifecycle_state": "type_i_confirmed"},
                }],
            },
            {
                "workflow_bucket": "reaction_observation",
                "change_count": 1,
                "items": [{
                    "display_key": "k2",
                    "instrument_id": "SSE.600000",
                    "review_bucket": "reaction_observation",
                    "change_types": ["next_key_changed"],
                    "previous": {"next_key_price": 100.0},
                    "current": {"next_key_price": 110.0},
                }],
            },
        ],
        "analysis_incomplete_instruments": [],
        "analysis_incomplete_count": 0,
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "historical_outcome_used_for_ranking": False,
        "predictive_score_used": False,
        "alpha_inference_allowed": False,
        "is_trade_instruction": False,
    }


def test_review_digest_api_applies_presentation_filters_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        api,
        "build_latest_daily_review_digest",
        lambda **kwargs: (
            captured.update({"history_root": kwargs["history_root"]})
            or _digest()
        ),
    )

    def fake_filter(payload, **kwargs):
        captured.update(kwargs)
        result = dict(payload)
        result["filtered_change_count"] = 1
        result["filtered_workflow_sections"] = [
            payload["workflow_sections"][0]
        ]
        result["source_change_count_unchanged"] = payload["change_count"]
        return result

    monkeypatch.setattr(api, "filter_daily_review_digest", fake_filter)
    monkeypatch.setattr(api, "OPERATOR_HISTORY_ROOT", tmp_path)

    payload = api.operator_review_digest(
        workflow_bucket="execution_evaluation",
        change_type="lifecycle_state_changed",
        instrument_id="sse.688256",
    )

    assert payload["change_count"] == 2
    assert payload["filtered_change_count"] == 1
    assert payload["source_change_count_unchanged"] == 2
    assert captured["history_root"] == str(tmp_path)
    assert captured["workflow_bucket"] == "execution_evaluation"
    assert captured["change_type"] == "lifecycle_state_changed"
    assert captured["instrument_id"] == "sse.688256"


def test_review_digest_api_surfaces_history_integrity_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(**_kwargs):
        raise RuntimeError(
            "operator_history_integrity_failure:previous_observation_missing"
        )

    monkeypatch.setattr(api, "build_latest_daily_review_digest", fail)

    with pytest.raises(HTTPException) as raised:
        api.operator_review_digest(
            workflow_bucket=None,
            change_type=None,
            instrument_id=None,
        )

    assert raised.value.status_code == 500
    assert "daily review digest unavailable" in str(raised.value.detail)


def test_review_digest_api_rejects_unknown_presentation_filters() -> None:
    with pytest.raises(HTTPException) as workflow_error:
        api.operator_review_digest(
            workflow_bucket="best_opportunity",
            change_type=None,
            instrument_id=None,
        )
    assert workflow_error.value.status_code == 400
    assert "unknown review workflow bucket" in str(
        workflow_error.value.detail
    )

    with pytest.raises(HTTPException) as change_error:
        api.operator_review_digest(
            workflow_bucket=None,
            change_type="profit_probability_changed",
            instrument_id=None,
        )
    assert change_error.value.status_code == 400
    assert "unknown review change type" in str(change_error.value.detail)
