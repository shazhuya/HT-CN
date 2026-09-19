from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

import services.api.main as api


def _session() -> dict:
    return {
        "schema_version": 1,
        "status": "changes_ready",
        "review_ready": True,
        "trade_date": "2026-09-19",
        "source_observation_id": "a" * 64,
        "source_revision_ordinal": 1,
        "previous_recorded_trade_date": "2026-09-18",
        "change_count": 2,
        "workflow_sections": [],
        "review_state_counts": {
            "unseen": 1,
            "reviewed": 0,
            "follow_up": 1,
        },
        "active_follow_up_count": 1,
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "historical_outcome_used_for_ranking": False,
        "predictive_score_used": False,
        "alpha_inference_allowed": False,
        "is_trade_instruction": False,
    }


def test_review_session_api_passes_filters_without_changing_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        api,
        "build_latest_review_session",
        lambda **kwargs: (
            captured.update(kwargs)
            or _session()
        ),
    )

    def fake_filter(payload, **kwargs):
        captured.update(kwargs)
        result = dict(payload)
        result["filtered_change_count"] = 1
        result["filtered_workflow_sections"] = []
        result["source_change_count_unchanged"] = payload["change_count"]
        result["source_review_state_counts_unchanged"] = payload[
            "review_state_counts"
        ]
        return result

    monkeypatch.setattr(api, "filter_review_session", fake_filter)
    monkeypatch.setattr(api, "OPERATOR_HISTORY_ROOT", tmp_path / "history")
    monkeypatch.setattr(api, "REVIEW_JOURNAL_ROOT", tmp_path / "journal")

    payload = api.operator_review_session(
        workflow_bucket="reaction_observation",
        change_type="next_key_changed",
        instrument_id="sse.688256",
        review_state="follow_up",
        follow_up_only=True,
    )

    assert payload["change_count"] == 2
    assert payload["filtered_change_count"] == 1
    assert payload["source_change_count_unchanged"] == 2
    assert captured["history_root"] == tmp_path / "history"
    assert captured["journal_root"] == tmp_path / "journal"
    assert captured["review_state"] == "follow_up"
    assert captured["follow_up_only"] is True


def test_review_session_api_rejects_unknown_review_state() -> None:
    with pytest.raises(HTTPException) as raised:
        api.operator_review_session(
            workflow_bucket=None,
            change_type=None,
            instrument_id=None,
            review_state="buy_now",
            follow_up_only=False,
        )

    assert raised.value.status_code == 400
    assert "unknown review state" in str(raised.value.detail)


def test_review_event_api_requires_binding_and_request_id() -> None:
    with pytest.raises(HTTPException) as raised:
        api.operator_review_session_event({
            "source_observation_id": "",
            "display_key": "key",
            "review_state": "reviewed",
        })

    assert raised.value.status_code == 400
    assert "missing review event fields" in str(raised.value.detail)


def test_review_event_api_appends_and_hides_local_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = {
        "event_id": "b" * 64,
        "review_state": "reviewed",
        "source": {
            "observation_id": "a" * 64,
            "display_key": "key",
        },
    }
    monkeypatch.setattr(
        api,
        "append_review_event",
        lambda **_kwargs: {
            "status": "appended",
            "event": event,
            "path": "/private/local/path.json",
            "waited_for_lock": False,
            "wait_seconds": 0.0,
        },
    )

    payload = api.operator_review_session_event({
        "source_observation_id": "a" * 64,
        "display_key": "key",
        "review_state": "reviewed",
        "note": "checked",
        "client_request_id": "request-1",
    })

    assert payload["status"] == "appended"
    assert payload["event"] == event
    assert "path" not in payload
    assert payload["authoritative_evidence"] is False
    assert payload["writes_m4_evidence"] is False
    assert payload["is_trade_instruction"] is False


def test_review_event_api_maps_validation_and_integrity_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        api,
        "append_review_event",
        lambda **_kwargs: (_ for _ in ()).throw(
            ValueError("unknown review state: buy_now")
        ),
    )
    with pytest.raises(HTTPException) as bad_request:
        api.operator_review_session_event({
            "source_observation_id": "a" * 64,
            "display_key": "key",
            "review_state": "buy_now",
            "client_request_id": "request-2",
        })
    assert bad_request.value.status_code == 400

    monkeypatch.setattr(
        api,
        "append_review_event",
        lambda **_kwargs: (_ for _ in ()).throw(
            RuntimeError("review_journal_integrity_failure:tampered")
        ),
    )
    with pytest.raises(HTTPException) as integrity:
        api.operator_review_session_event({
            "source_observation_id": "a" * 64,
            "display_key": "key",
            "review_state": "reviewed",
            "client_request_id": "request-3",
        })
    assert integrity.value.status_code == 500
    assert "review journal unavailable" in str(integrity.value.detail)
