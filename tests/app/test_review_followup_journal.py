from __future__ import annotations

from pathlib import Path

import pytest

import htcn.app.review_followup_journal as journal
from htcn.app.review_followup_journal import (
    append_review_event,
    build_latest_review_session,
    filter_review_session,
    verify_review_journal_event,
)


OBS_A = "a" * 64
OBS_B = "b" * 64
KEY = "SSE.688256:bat:XABCD:bullish:S5:2026-09-01"


def _source_meta(
    *,
    observation_id: str,
    display_key: str,
) -> dict:
    return {
        "trade_date": (
            "2026-09-18"
            if observation_id == OBS_A
            else "2026-09-19"
        ),
        "revision_ordinal": 1,
        "source_generated_at_utc": "2026-09-19T01:00:00+00:00",
        "instrument_id": "SSE.688256",
        "change_types": ["lifecycle_state_changed"],
    }


def _patch_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        journal,
        "_find_source_change",
        lambda **kwargs: _source_meta(
            observation_id=kwargs["source_observation_id"],
            display_key=kwargs["display_key"],
        ),
    )


def _digest(observation_id: str) -> dict:
    return {
        "schema_version": 1,
        "contract": {},
        "status": "changes_ready",
        "review_ready": True,
        "trade_date": (
            "2026-09-18"
            if observation_id == OBS_A
            else "2026-09-19"
        ),
        "source_observation_id": observation_id,
        "source_revision_ordinal": 1,
        "source_generated_at_utc": "2026-09-19T01:00:00+00:00",
        "previous_recorded_trade_date": "2026-09-17",
        "delta_status": "ready",
        "change_count": 1,
        "change_type_counts": {"lifecycle_state_changed": 1},
        "workflow_bucket_counts": {"reaction_observation": 1},
        "workflow_sections": [{
            "workflow_bucket": "reaction_observation",
            "change_count": 1,
            "items": [{
                "display_key": KEY,
                "instrument_id": "SSE.688256",
                "review_bucket": "reaction_observation",
                "change_types": ["lifecycle_state_changed"],
                "previous": {
                    "action_state": "waiting",
                    "lifecycle_state": "waiting_terminal",
                    "next_key_price": 100.0,
                },
                "current": {
                    "action_state": "reaction_observation",
                    "lifecycle_state": "t_plus_1",
                    "next_key_price": 110.0,
                },
            }],
        }],
        "analysis_incomplete_instruments": [],
        "analysis_incomplete_count": 0,
        "review_order": [],
        "change_type_order": [],
        "ordering_is_product_workflow_not_expected_return": True,
        "all_changes_are_retained": True,
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "historical_outcome_used_for_ranking": False,
        "predictive_score_used": False,
        "alpha_inference_allowed": False,
        "is_trade_instruction": False,
    }


def test_append_review_event_is_valid_and_non_authoritative(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_source(monkeypatch)
    root = tmp_path / "journal"

    payload = append_review_event(
        history_root=tmp_path / "history",
        journal_root=root,
        source_observation_id=OBS_A,
        display_key=KEY,
        review_state="reviewed",
        note="已核对结构，暂不需要继续盯。",
        client_request_id="req-1",
    )

    assert payload["status"] == "appended"
    event = payload["event"]
    assert event["review_state"] == "reviewed"
    assert event["contract"]["append_only"] is True
    assert event["contract"]["mutates_lifecycle"] is False
    assert event["contract"]["mutates_action_state"] is False
    assert event["authoritative_evidence"] is False
    assert event["writes_m4_evidence"] is False
    assert event["is_trade_instruction"] is False

    checked = verify_review_journal_event(payload["path"])
    assert checked["status"] == "valid"


def test_client_request_id_makes_retry_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_source(monkeypatch)
    kwargs = {
        "history_root": tmp_path / "history",
        "journal_root": tmp_path / "journal",
        "source_observation_id": OBS_A,
        "display_key": KEY,
        "review_state": "follow_up",
        "note": "后续跟踪",
        "client_request_id": "req-idempotent",
    }

    first = append_review_event(**kwargs)
    second = append_review_event(**kwargs)

    assert first["status"] == "appended"
    assert second["status"] == "idempotent_existing"
    assert second["event"]["event_id"] == first["event"]["event_id"]
    assert len(list((tmp_path / "journal").glob("*/*/*.json"))) == 1


def test_client_request_replay_conflict_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_source(monkeypatch)
    append_review_event(
        history_root=tmp_path / "history",
        journal_root=tmp_path / "journal",
        source_observation_id=OBS_A,
        display_key=KEY,
        review_state="reviewed",
        note="first",
        client_request_id="same-request",
    )

    with pytest.raises(ValueError, match="replay conflict"):
        append_review_event(
            history_root=tmp_path / "history",
            journal_root=tmp_path / "journal",
            source_observation_id=OBS_A,
            display_key=KEY,
            review_state="follow_up",
            note="different",
            client_request_id="same-request",
        )


def test_deleted_prior_event_breaks_append_only_chain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_source(monkeypatch)
    root = tmp_path / "journal"
    first = append_review_event(
        history_root=tmp_path / "history",
        journal_root=root,
        source_observation_id=OBS_A,
        display_key=KEY,
        review_state="reviewed",
        note="one",
        client_request_id="req-one",
    )
    append_review_event(
        history_root=tmp_path / "history",
        journal_root=root,
        source_observation_id=OBS_A,
        display_key=KEY,
        review_state="follow_up",
        note="two",
        client_request_id="req-two",
    )
    Path(first["path"]).unlink()

    monkeypatch.setattr(
        journal,
        "build_latest_daily_review_digest",
        lambda **_kwargs: _digest(OBS_A),
    )
    with pytest.raises(RuntimeError, match="integrity_failure"):
        build_latest_review_session(
            history_root=tmp_path / "history",
            journal_root=root,
        )


def test_follow_up_carries_across_observations_but_new_change_is_unseen(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_source(monkeypatch)
    root = tmp_path / "journal"
    append_review_event(
        history_root=tmp_path / "history",
        journal_root=root,
        source_observation_id=OBS_A,
        display_key=KEY,
        review_state="follow_up",
        note="明天继续看",
        client_request_id="req-follow",
    )

    monkeypatch.setattr(
        journal,
        "build_latest_daily_review_digest",
        lambda **_kwargs: _digest(OBS_B),
    )
    payload = build_latest_review_session(
        history_root=tmp_path / "history",
        journal_root=root,
    )
    review = payload["workflow_sections"][0]["items"][0]["review"]

    assert review["review_state"] == "unseen"
    assert review["active_follow_up"] is True
    assert review["active_follow_up_origin_observation_id"] == OBS_A
    assert review["active_follow_up_origin_trade_date"] == "2026-09-18"
    assert payload["review_state_counts"]["unseen"] == 1
    assert payload["active_follow_up_count"] == 1


def test_current_reviewed_event_closes_prior_follow_up(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_source(monkeypatch)
    root = tmp_path / "journal"
    append_review_event(
        history_root=tmp_path / "history",
        journal_root=root,
        source_observation_id=OBS_A,
        display_key=KEY,
        review_state="follow_up",
        note="carry",
        client_request_id="req-follow-a",
    )
    append_review_event(
        history_root=tmp_path / "history",
        journal_root=root,
        source_observation_id=OBS_B,
        display_key=KEY,
        review_state="reviewed",
        note="今天已经复核，结束跟踪",
        client_request_id="req-reviewed-b",
    )

    monkeypatch.setattr(
        journal,
        "build_latest_daily_review_digest",
        lambda **_kwargs: _digest(OBS_B),
    )
    payload = build_latest_review_session(
        history_root=tmp_path / "history",
        journal_root=root,
    )
    review = payload["workflow_sections"][0]["items"][0]["review"]

    assert review["review_state"] == "reviewed"
    assert review["active_follow_up"] is False
    assert payload["active_follow_up_count"] == 0


def test_review_filter_is_presentation_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_source(monkeypatch)
    root = tmp_path / "journal"
    append_review_event(
        history_root=tmp_path / "history",
        journal_root=root,
        source_observation_id=OBS_A,
        display_key=KEY,
        review_state="follow_up",
        note="keep",
        client_request_id="req-filter",
    )
    monkeypatch.setattr(
        journal,
        "build_latest_daily_review_digest",
        lambda **_kwargs: _digest(OBS_A),
    )
    source = build_latest_review_session(
        history_root=tmp_path / "history",
        journal_root=root,
    )

    filtered = filter_review_session(
        source,
        review_state="follow_up",
        follow_up_only=True,
    )

    assert filtered["filtered_change_count"] == 1
    assert filtered["change_count"] == 1
    assert filtered["source_review_state_counts_unchanged"] == {
        "unseen": 0,
        "reviewed": 0,
        "follow_up": 1,
    }
    assert filtered["source_active_follow_up_count_unchanged"] == 1


def test_invalid_review_state_and_long_note_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_source(monkeypatch)

    with pytest.raises(ValueError, match="unknown review state"):
        append_review_event(
            history_root=tmp_path / "history",
            journal_root=tmp_path / "journal",
            source_observation_id=OBS_A,
            display_key=KEY,
            review_state="buy_now",
            note="",
            client_request_id="req-invalid",
        )

    with pytest.raises(ValueError, match="exceeds"):
        append_review_event(
            history_root=tmp_path / "history",
            journal_root=tmp_path / "journal",
            source_observation_id=OBS_A,
            display_key=KEY,
            review_state="reviewed",
            note="x" * 1001,
            client_request_id="req-long-note",
        )


def test_missing_source_binding_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="binding not found"):
        append_review_event(
            history_root=tmp_path / "history",
            journal_root=tmp_path / "journal",
            source_observation_id=OBS_A,
            display_key=KEY,
            review_state="reviewed",
            note="",
            client_request_id="req-missing",
        )
