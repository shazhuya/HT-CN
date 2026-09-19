from __future__ import annotations

from types import SimpleNamespace
import io
import json
from pathlib import Path
import zipfile

import pytest

from htcn.app import handoff_v3_inspector as inspector


KEY = "SSE.688256:bat:XABCD:bullish:S5:2026-09-01-2026-09-19"


def _j(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")


def _zip_bytes(blobs: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in blobs.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def _queue() -> dict:
    item = {
        "display_key": KEY,
        "instrument_id": "SSE.688256",
        "pattern_id": "bat",
        "schema": "XABCD",
        "direction": "bullish",
        "scale": 5,
        "pattern_state": "forming",
        "action_state": "reaction_observation",
        "lifecycle_state": "t_plus_1",
        "current_position": "Source T-Bar 后第一观察日",
        "first_watch": "先看 38.2% 反应",
        "next_watch": "随后看 61.8%",
        "upgrade_blocker": "未达到早期反应目标",
        "next_key_price": 112.5,
        "next_key_price_role": "type_i_38_2_target",
        "execution_context_gate": "tradable",
        "context_cautions": [],
    }
    return {
        "schema_version": 2,
        "as_of_trade_date": "2026-09-19",
        "observation_integrity": "single_as_of",
        "candidate_count": 1,
        "candidate_instrument_count": 1,
        "action_state_counts": {"reaction_observation": 1},
        "lifecycle_state_counts": {"t_plus_1": 1},
        "items": [item],
        "errors": [],
    }


def _build_bundle(path: Path) -> None:
    current_snapshot = {
        "schema_version": 1,
        "contract_version": 2,
        "expected_trade_date": "2026-09-19",
        "queue": _queue(),
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
    }
    previous_snapshot = {
        "schema_version": 1,
        "contract_version": 2,
        "expected_trade_date": "2026-09-18",
        "queue": {
            **_queue(),
            "as_of_trade_date": "2026-09-18",
            "items": [
                {
                    **_queue()["items"][0],
                    "action_state": "waiting",
                    "lifecycle_state": "waiting_terminal",
                }
            ],
        },
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
    }
    nested_files = {
        "pipeline/m5-daily-close-pipeline.json": _j({
            "m5_product_ready": True,
            "m5_history_ready": True,
            "m5_review_digest_ready": True,
            "m4_research_ready": False,
        }),
        "m5/m5-operator-snapshot.json": _j({
            "schema_version": 2,
            "product_ready": True,
            "as_of_trade_date": "2026-09-19",
        }),
        "m5/operator_snapshots/current.json": _j(current_snapshot),
        "m5/operator_snapshots/previous.json": _j(previous_snapshot),
    }
    nested_manifest = {
        "schema_version": 2,
        "status": "product_transport_research_degraded",
        "m5_product_ready": True,
        "m4_research_ready": False,
        "product_binding": {"trade_date": "2026-09-19"},
        "m4_nested_bundle_verification": {"status": "valid"},
        "files": [
            {"arcname": "pipeline/m5-daily-close-pipeline.json", "role": "pipeline_summary"},
            {"arcname": "m5/m5-operator-snapshot.json", "role": "m5_final_product_report"},
            {"arcname": "m5/operator_snapshots/current.json", "role": "m5_current_product_snapshot"},
            {"arcname": "m5/operator_snapshots/previous.json", "role": "m5_previous_product_snapshot"},
        ],
    }
    nested_files["daily-handoff-manifest.json"] = _j(nested_manifest)
    nested = _zip_bytes(nested_files)

    current_history = {
        "trade_date": "2026-09-19",
        "observation_id": "obs-current",
        "revision_ordinal": 1,
        "previous_recorded_trade_date": "2026-09-18",
        "previous_observation_id": "obs-previous",
        "queue_snapshot": _queue(),
        "delta": {
            "status": "changes_ready",
            "change_count": 1,
            "changes": [{
                "display_key": KEY,
                "instrument_id": "SSE.688256",
                "change_types": ["lifecycle_state_changed"],
            }],
        },
    }
    previous_history = {
        "trade_date": "2026-09-18",
        "observation_id": "obs-previous",
        "revision_ordinal": 1,
        "queue_snapshot": previous_snapshot["queue"],
    }
    digest = {
        "schema_version": 1,
        "trade_date": "2026-09-19",
        "source_observation_id": "obs-current",
        "status": "changes_ready",
        "change_count": 1,
        "workflow_sections": [{
            "workflow": "reaction_observation",
            "items": [{
                "display_key": KEY,
                "instrument_id": "SSE.688256",
                "change_types": ["lifecycle_state_changed"],
            }],
        }],
    }
    session = {
        **digest,
        "review_state_counts": {"follow_up": 1},
        "active_follow_up_count": 1,
        "active_follow_ups": [{
            "event_id": "event-1",
            "display_key": KEY,
            "instrument_id": "SSE.688256",
            "review_state": "follow_up",
            "note": "继续观察下一关键价",
            "source_trade_date": "2026-09-19",
            "source_observation_id": "obs-current",
        }],
    }
    event = {
        "event_id": "event-1",
        "display_key": KEY,
        "instrument_id": "SSE.688256",
        "review_state": "follow_up",
        "note": "继续观察下一关键价",
        "source": {
            "trade_date": "2026-09-19",
            "observation_id": "obs-current",
        },
    }

    outer_files = {
        "base/htcn-daily-handoff-v2.zip": nested,
        "m5/history/current/2026-09-19/obs-current.json": _j(current_history),
        "m5/history/previous/2026-09-18/obs-previous.json": _j(previous_history),
        "m5/review/m5-daily-review-digest.json": _j(digest),
        "m5/review/m5-review-session-snapshot.json": _j(session),
        "m5/review_journal/2026-09-19/binding/event-1.json": _j(event),
    }
    manifest = {
        "schema_version": 3,
        "status": "complete_review_transport",
        "m5_product_ready": True,
        "m5_history_ready": True,
        "m5_review_digest_ready": True,
        "m4_research_ready": False,
        "history_binding": {"trade_date": "2026-09-19"},
        "files": [
            {"arcname": "base/htcn-daily-handoff-v2.zip", "role": "m5_handoff_v2_base"},
            {"arcname": "m5/history/current/2026-09-19/obs-current.json", "role": "m5_current_history_record"},
            {"arcname": "m5/history/previous/2026-09-18/obs-previous.json", "role": "m5_previous_history_record"},
            {"arcname": "m5/review/m5-daily-review-digest.json", "role": "m5_daily_review_digest"},
            {"arcname": "m5/review/m5-review-session-snapshot.json", "role": "m5_review_session_snapshot"},
            {"arcname": "m5/review_journal/2026-09-19/binding/event-1.json", "role": "m5_review_journal_event"},
        ],
    }
    outer_files["daily-handoff-v3-manifest.json"] = _j(manifest)
    path.write_bytes(_zip_bytes(outer_files))


def _valid_verification(path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        status="valid",
        bundle_path=str(path),
        schema_version=3,
        file_count=6,
        errors=(),
        warnings=(),
        manifest={},
    )


def test_inspector_builds_portable_model_from_verified_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = tmp_path / "handoff-v3.zip"
    _build_bundle(bundle)
    monkeypatch.setattr(
        inspector,
        "verify_daily_handoff_bundle_v3",
        lambda path: _valid_verification(Path(path)),
    )

    payload = inspector.build_handoff_v3_inspection(bundle)

    assert payload["contract"]["requires_market_database"] is False
    assert payload["contract"]["imports_product_state"] is False
    assert payload["contract"]["creates_review_events"] is False
    assert payload["summary"]["trade_date"] == "2026-09-19"
    assert payload["summary"]["candidate_count"] == 1
    assert payload["summary"]["daily_change_count"] == 1
    assert payload["summary"]["active_follow_up_count"] == 1
    assert payload["summary"]["current_history_observation_id"] == "obs-current"
    assert payload["summary"]["previous_history_observation_id"] == "obs-previous"
    assert payload["indexes"]["current_queue_items"][0]["instrument_id"] == "SSE.688256"


def test_inspector_drilldown_is_read_only_and_exact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = tmp_path / "handoff-v3.zip"
    _build_bundle(bundle)
    monkeypatch.setattr(
        inspector,
        "verify_daily_handoff_bundle_v3",
        lambda path: _valid_verification(Path(path)),
    )
    payload = inspector.build_handoff_v3_inspection(bundle)

    filtered = inspector.filter_handoff_v3_inspection(
        payload,
        instrument_id="SSE.688256",
        display_key=KEY,
    )

    assert len(filtered["drilldown"]["queue_items"]) == 1
    assert len(filtered["drilldown"]["digest_items"]) == 1
    assert len(filtered["drilldown"]["active_follow_ups"]) == 1
    assert "drilldown" not in payload
    assert filtered["writes_m4_evidence"] is False
    assert filtered["creates_review_events"] is False


def test_inspector_refuses_invalid_v3_before_reading_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = tmp_path / "handoff-v3.zip"
    bundle.write_bytes(b"not trusted")
    monkeypatch.setattr(
        inspector,
        "verify_daily_handoff_bundle_v3",
        lambda path: SimpleNamespace(
            status="invalid",
            schema_version=3,
            file_count=0,
            errors=("member_hash_mismatch:x",),
            warnings=(),
        ),
    )

    with pytest.raises(RuntimeError, match="handoff_v3_invalid"):
        inspector.build_handoff_v3_inspection(bundle)


def test_portable_html_contains_embedded_workspace_and_no_write_actions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = tmp_path / "handoff-v3.zip"
    _build_bundle(bundle)
    monkeypatch.setattr(
        inspector,
        "verify_daily_handoff_bundle_v3",
        lambda path: _valid_verification(Path(path)),
    )
    payload = inspector.build_handoff_v3_inspection(bundle)

    html = inspector.build_portable_review_html(payload)

    assert "HT-CN Handoff v3 便携复盘工作区" in html
    assert "SSE.688256" in html
    assert "继续观察下一关键价" in html
    assert "不导入 Queue/History/Review Journal" in html
    assert "review-session/event" not in html
    assert "fetch(" not in html


def test_workspace_writer_outputs_json_and_single_file_html(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = tmp_path / "handoff-v3.zip"
    _build_bundle(bundle)
    monkeypatch.setattr(
        inspector,
        "verify_daily_handoff_bundle_v3",
        lambda path: _valid_verification(Path(path)),
    )
    json_output = tmp_path / "out" / "inspection.json"
    html_output = tmp_path / "out" / "workspace.html"

    result = inspector.write_portable_review_workspace(
        bundle_path=bundle,
        json_output=json_output,
        html_output=html_output,
    )

    assert result["status"] == "ready"
    assert json_output.is_file()
    assert html_output.is_file()
    stored = json.loads(json_output.read_text(encoding="utf-8"))
    assert stored["summary"]["candidate_count"] == 1
    assert "SSE.688256" in html_output.read_text(encoding="utf-8")
