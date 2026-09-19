from __future__ import annotations

import json
from pathlib import Path
import zipfile

import pytest

from htcn.app.daily_handoff_v3 import (
    build_daily_handoff_bundle_v3,
    verify_daily_handoff_bundle_v3,
)
from htcn.app.daily_review_digest import build_latest_daily_review_digest
from htcn.app.operator_history import append_operator_history
from htcn.app.operator_snapshot import OPERATOR_SNAPSHOT_CONTRACT_VERSION
from htcn.app.review_followup_journal import append_review_event


FP = "a" * 64
KEY = "SSE.688256:bat:XABCD:bullish:S5:2026-09-01"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _identity() -> dict:
    return {
        "contract_version": 1,
        "fingerprint": FP,
        "data": {
            "contract_version": 1,
            "fingerprint": "c" * 64,
            "component_count": 1,
            "manifest_mode": "relative_path_size_mtime_ns",
        },
        "analysis_code": {
            "contract_version": 1,
            "fingerprint": "d" * 64,
            "component_count": 1,
            "manifest_mode": "relative_path_content_sha256",
        },
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "methodology_identity": False,
    }


def _queue_contract() -> dict:
    return {
        "version": 1,
        "source_of_truth": "existing_source_lifecycle_and_decision_narrative",
        "ranking_mode": "workflow_bucket_only",
        "predictive_score_used": False,
        "historical_outcome_used": False,
        "alpha_inference_allowed": False,
        "is_trade_instruction": False,
        "mutates_harmonic_identity": False,
        "mutates_source_raw_prz": False,
        "owns_lifecycle": False,
    }


def _item(
    *,
    action: str,
    lifecycle: str,
    next_key: float,
) -> dict:
    return {
        "display_key": KEY,
        "instrument_id": "SSE.688256",
        "pattern_id": "bat",
        "schema": "XABCD",
        "direction": "bullish",
        "scale": 5,
        "pattern_state": "forming",
        "action_state": action,
        "lifecycle_state": lifecycle,
        "next_key_price": next_key,
        "next_key_price_role": "source_prz_entry_edge",
        "execution_context_gate": "tradable",
        "context_cautions": [],
        "current_position": "position",
        "first_watch": "watch",
        "upgrade_blocker": "blocker",
    }


def _queue(
    trade_date: str,
    *,
    action: str,
    lifecycle: str,
    next_key: float,
) -> dict:
    return {
        "schema_version": 2,
        "as_of_trade_date": trade_date,
        "observed_trade_dates": [trade_date],
        "observation_integrity": "single_as_of",
        "contract": _queue_contract(),
        "instrument_count": 1,
        "analyzed_instrument_count": 1,
        "failed_instrument_count": 0,
        "candidate_count": 1,
        "candidate_instrument_count": 1,
        "action_state_counts": {action: 1},
        "lifecycle_state_counts": {lifecycle: 1},
        "items": [
            _item(
                action=action,
                lifecycle=lifecycle,
                next_key=next_key,
            )
        ],
        "errors": [],
    }


def _write_product(
    root: Path,
    trade_date: str,
    *,
    action: str,
    lifecycle: str,
    next_key: float,
    generated_hour: int,
) -> Path:
    identity = _identity()
    queue = _queue(
        trade_date,
        action=action,
        lifecycle=lifecycle,
        next_key=next_key,
    )
    snapshot = (
        root
        / "data"
        / "product"
        / "m5"
        / "operator_queue"
        / f"{trade_date}__b420__s3-5-8-13.json"
    )
    _write_json(
        snapshot,
        {
            "schema_version": 1,
            "contract_version": OPERATOR_SNAPSHOT_CONTRACT_VERSION,
            "generated_at_utc": (
                f"{trade_date}T{generated_hour:02d}:00:00+00:00"
            ),
            "expected_trade_date": trade_date,
            "bars": 420,
            "scales": [3, 5, 8, 13],
            "universe_hash": "u",
            "instrument_count": 1,
            "input_identity": identity,
            "queue": queue,
            "authoritative_evidence": False,
            "writes_m4_evidence": False,
        },
    )
    report = root / "artifacts" / "reports" / "m5-operator-snapshot.json"
    _write_json(
        report,
        {
            "schema_version": 2,
            "status": "ready",
            "product_ready": True,
            "instrument_count": 1,
            "analyzed_instrument_count": 1,
            "failed_instrument_count": 0,
            "as_of_trade_date": trade_date,
            "observation_integrity": "single_as_of",
            "product_cache": {
                "schema_version": 1,
                "contract_version": OPERATOR_SNAPSHOT_CONTRACT_VERSION,
                "status": "hit",
                "expected_local_trade_date": trade_date,
                "queue_as_of_trade_date": trade_date,
                "freshness": "current",
                "cache_path": str(snapshot.resolve()),
                "input_identity_contract_version": 1,
                "input_identity_fingerprint": FP,
                "input_identity_stable_during_build": True,
            },
            "input_identity": identity,
            "authoritative_evidence": False,
            "writes_m4_evidence": False,
            "is_trade_instruction": False,
            "alpha_inference_allowed": False,
        },
    )
    return report


def _write_digest(root: Path) -> dict:
    digest = build_latest_daily_review_digest(
        history_root=str(
            root / "data" / "product" / "m5" / "operator_history"
        )
    )
    payload = {
        **digest,
        "generated_at_utc": "2026-09-19T09:10:00+00:00",
        "history_root": "data/product/m5/operator_history",
        "report_path": "artifacts/reports/m5-daily-review-digest.json",
    }
    _write_json(
        root / "artifacts" / "reports" / "m5-daily-review-digest.json",
        payload,
    )
    return payload


def _pipeline(
    root: Path,
    *,
    history_ready: bool = True,
    digest_ready: bool = True,
) -> dict:
    payload = {
        "schema_version": 2,
        "generated_at_utc": "2026-09-19T09:20:00+00:00",
        "overall_status": "product_ready_research_degraded",
        "exit_code": 0,
        "market_data_ready": True,
        "m5_product_ready": True,
        "m5_initial_product_ready": True,
        "m5_final_cache_revalidated_after_research_lane": True,
        "m5_context_refresh_ready": True,
        "m5_history_ready": history_ready,
        "m5_history_degraded_but_product_allowed": not history_ready,
        "m5_review_digest_ready": digest_ready,
        "m5_review_digest_degraded_but_product_allowed": not digest_ready,
        "m4_research_ready": False,
        "steps": {},
        "artifacts": {
            "pipeline_report": (
                "artifacts/reports/m5-daily-close-pipeline.json"
            ),
            "m5_operator_snapshot_report": (
                "artifacts/reports/m5-operator-snapshot.json"
            ),
            "m4_evidence_bundle": (
                "artifacts/reports/m4-evidence-bundle.zip"
            ),
        },
    }
    _write_json(
        root / "artifacts" / "reports" / "m5-daily-close-pipeline.json",
        payload,
    )
    return payload


def _prepare_full(
    root: Path,
    *,
    with_follow_up: bool = True,
) -> tuple[dict, str]:
    report = _write_product(
        root,
        "2026-09-18",
        action="waiting",
        lifecycle="waiting_terminal",
        next_key=100.0,
        generated_hour=8,
    )
    append_operator_history(
        root=root,
        report_path=report,
    )

    report = _write_product(
        root,
        "2026-09-19",
        action="reaction_observation",
        lifecycle="t_plus_1",
        next_key=112.5,
        generated_hour=8,
    )
    current = append_operator_history(
        root=root,
        report_path=report,
    )
    _write_digest(root)

    if with_follow_up:
        append_review_event(
            history_root=(
                root / "data" / "product" / "m5" / "operator_history"
            ),
            journal_root=(
                root / "data" / "product" / "m5" / "review_journal"
            ),
            source_observation_id=str(current["observation_id"]),
            display_key=KEY,
            review_state="follow_up",
            note="继续观察下一关键价",
            client_request_id="handoff-v3-test-follow",
        )

    pipeline = _pipeline(root)
    return pipeline, str(current["observation_id"])


def test_v3_transports_exact_history_digest_session_and_event_chain(
    tmp_path: Path,
) -> None:
    pipeline, observation_id = _prepare_full(tmp_path)
    output = tmp_path / "artifacts" / "reports" / "handoff-v3.zip"

    payload = build_daily_handoff_bundle_v3(
        root=tmp_path,
        pipeline_summary=pipeline,
        output=output,
    )

    assert payload["status"] == "complete_review_transport"
    assert payload["verification"]["status"] == "valid"
    assert payload["history_binding"]["observation_id"] == observation_id
    assert payload["digest_binding"]["source_observation_id"] == observation_id
    assert payload["review_session_binding"]["source_observation_id"] == (
        observation_id
    )
    assert payload["review_session_binding"]["journal_event_count"] == 1
    assert payload["review_session_binding"]["active_follow_up_count"] == 1
    assert payload["phase10_handoff_v2_is_nested_and_unmodified"] is True
    assert not (
        tmp_path
        / "artifacts"
        / "reports"
        / "htcn-daily-handoff-v2.zip"
    ).exists()

    checked = verify_daily_handoff_bundle_v3(output)
    assert checked.status == "valid"

    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert "base/htcn-daily-handoff-v2.zip" in names
        assert "m5/review/m5-daily-review-digest.json" in names
        assert "m5/review/m5-review-session-snapshot.json" in names
        assert any(
            name.startswith("m5/history/current/2026-09-19/")
            for name in names
        )
        assert any(
            name.startswith("m5/history/previous/2026-09-18/")
            for name in names
        )
        assert any(name.startswith("m5/review_journal/") for name in names)


def test_v3_without_review_events_is_still_complete_and_valid(
    tmp_path: Path,
) -> None:
    pipeline, _ = _prepare_full(tmp_path, with_follow_up=False)
    output = tmp_path / "handoff-v3.zip"

    payload = build_daily_handoff_bundle_v3(
        root=tmp_path,
        pipeline_summary=pipeline,
        output=output,
    )

    assert payload["verification"]["status"] == "valid"
    assert payload["review_session_binding"]["journal_event_count"] == 0
    assert payload["review_session_binding"]["root_event_ids"] == []


def test_v3_detects_history_bound_to_different_product_report(
    tmp_path: Path,
) -> None:
    pipeline, _ = _prepare_full(tmp_path)
    report = (
        tmp_path
        / "artifacts"
        / "reports"
        / "m5-operator-snapshot.json"
    )
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["transport_test_extra"] = "changes report bytes only"
    _write_json(report, payload)

    with pytest.raises(
        RuntimeError,
        match="history_product_report_hash_mismatch",
    ):
        build_daily_handoff_bundle_v3(
            root=tmp_path,
            pipeline_summary=pipeline,
            output=tmp_path / "handoff-v3.zip",
        )


def test_v3_rejects_digest_not_matching_current_history(
    tmp_path: Path,
) -> None:
    pipeline, _ = _prepare_full(tmp_path)
    digest_path = (
        tmp_path
        / "artifacts"
        / "reports"
        / "m5-daily-review-digest.json"
    )
    payload = json.loads(digest_path.read_text(encoding="utf-8"))
    payload["change_count"] = 999
    _write_json(digest_path, payload)

    with pytest.raises(
        RuntimeError,
        match="daily_review_digest_source_mismatch",
    ):
        build_daily_handoff_bundle_v3(
            root=tmp_path,
            pipeline_summary=pipeline,
            output=tmp_path / "handoff-v3.zip",
        )


def test_v3_history_degraded_keeps_valid_nested_v2_transport(
    tmp_path: Path,
) -> None:
    _write_product(
        tmp_path,
        "2026-09-19",
        action="waiting",
        lifecycle="waiting_terminal",
        next_key=100.0,
        generated_hour=8,
    )
    pipeline = _pipeline(
        tmp_path,
        history_ready=False,
        digest_ready=False,
    )
    output = tmp_path / "handoff-v3.zip"

    payload = build_daily_handoff_bundle_v3(
        root=tmp_path,
        pipeline_summary=pipeline,
        output=output,
    )

    assert payload["status"] == "product_transport_history_degraded"
    assert payload["history_binding"] is None
    assert payload["digest_binding"] is None
    assert payload["review_session_binding"] is None
    assert verify_daily_handoff_bundle_v3(output).status == "valid"


def test_v3_rejects_digest_ready_without_history_ready(
    tmp_path: Path,
) -> None:
    _write_product(
        tmp_path,
        "2026-09-19",
        action="waiting",
        lifecycle="waiting_terminal",
        next_key=100.0,
        generated_hour=8,
    )
    pipeline = _pipeline(
        tmp_path,
        history_ready=False,
        digest_ready=True,
    )

    with pytest.raises(RuntimeError, match="digest_ready_without_history"):
        build_daily_handoff_bundle_v3(
            root=tmp_path,
            pipeline_summary=pipeline,
            output=tmp_path / "handoff-v3.zip",
        )


def test_v3_verifier_detects_review_event_tamper_even_if_member_hash_updated(
    tmp_path: Path,
) -> None:
    pipeline, _ = _prepare_full(tmp_path)
    output = tmp_path / "handoff-v3.zip"
    build_daily_handoff_bundle_v3(
        root=tmp_path,
        pipeline_summary=pipeline,
        output=output,
    )

    rebuilt = tmp_path / "tampered-v3.zip"
    with zipfile.ZipFile(output, "r") as source:
        blobs = {
            info.filename: source.read(info.filename)
            for info in source.infolist()
        }

    event_name = next(
        name
        for name in blobs
        if name.startswith("m5/review_journal/")
    )
    event = json.loads(blobs[event_name].decode("utf-8"))
    event["note"] = "tampered without updating event integrity"
    blobs[event_name] = (
        json.dumps(
            event,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")

    manifest = json.loads(
        blobs["daily-handoff-v3-manifest.json"].decode("utf-8")
    )
    for record in manifest["files"]:
        if record["arcname"] == event_name:
            record["size_bytes"] = len(blobs[event_name])
            import hashlib
            record["sha256"] = hashlib.sha256(
                blobs[event_name]
            ).hexdigest()
    blobs["daily-handoff-v3-manifest.json"] = (
        json.dumps(
            manifest,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")

    with zipfile.ZipFile(
        rebuilt,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as target:
        for name, data in blobs.items():
            target.writestr(name, data)

    checked = verify_daily_handoff_bundle_v3(rebuilt)
    assert checked.status == "invalid"
    assert any(
        "transport_review_event_invalid" in error
        for error in checked.errors
    )
