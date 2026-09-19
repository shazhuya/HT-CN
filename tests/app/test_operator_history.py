from __future__ import annotations

import json
from pathlib import Path

import pytest

from htcn.app.operator_history import (
    append_operator_history,
    query_operator_history,
    verify_operator_history_record,
)
from htcn.app.operator_snapshot import OPERATOR_SNAPSHOT_CONTRACT_VERSION

FP_A = "a" * 64
FP_B = "b" * 64


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _identity(fingerprint: str) -> dict:
    return {
        "contract_version": 1,
        "fingerprint": fingerprint,
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


def _item(
    *,
    key: str = "SSE.688256:bat:XABCD:bullish:S5:2026-09-01",
    instrument_id: str = "SSE.688256",
    lifecycle: str = "approaching_source_prz",
    action: str = "waiting",
    next_key: float = 100.0,
) -> dict:
    return {
        "display_key": key,
        "instrument_id": instrument_id,
        "pattern_id": "bat",
        "schema": "XABCD",
        "direction": "bullish",
        "scale": 5,
        "pattern_state": "forming",
        "action_state": action,
        "workflow_bucket_order": 2,
        "lifecycle_state": lifecycle,
        "next_key_price": next_key,
        "next_key_price_role": "source_prz_entry_edge",
        "execution_context_gate": "tradable",
        "context_cautions": [],
        "current_position": "current",
        "first_watch": "first",
        "upgrade_blocker": "blocker",
    }


def _queue(
    trade_date: str,
    items: list[dict],
    *,
    errors: list[dict] | None = None,
) -> dict:
    return {
        "schema_version": 2,
        "contract": {
            "predictive_score_used": False,
            "historical_outcome_used": False,
            "alpha_inference_allowed": False,
            "is_trade_instruction": False,
            "mutates_harmonic_identity": False,
            "mutates_source_raw_prz": False,
            "owns_lifecycle": False,
        },
        "as_of_trade_date": trade_date,
        "observed_trade_dates": [trade_date],
        "observation_integrity": "single_as_of",
        "items": items,
        "errors": errors or [],
    }


def _prepare_source(
    root: Path,
    *,
    trade_date: str,
    generated_at: str,
    fingerprint: str,
    items: list[dict],
) -> Path:
    identity = _identity(fingerprint)
    snapshot = (
        root
        / "data"
        / "product"
        / "m5"
        / "operator_queue"
        / f"{trade_date}__b420__s3-5-8-13.json"
    )
    queue = _queue(trade_date, items)
    _write_json(
        snapshot,
        {
            "schema_version": 1,
            "contract_version": OPERATOR_SNAPSHOT_CONTRACT_VERSION,
            "generated_at_utc": generated_at,
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
                "input_identity_fingerprint": fingerprint,
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


def _history(root: Path) -> Path:
    return root / "data" / "product" / "m5" / "operator_history"


def test_first_observation_creates_baseline_record(tmp_path: Path) -> None:
    report = _prepare_source(
        tmp_path,
        trade_date="2026-09-17",
        generated_at="2026-09-17T08:00:00+00:00",
        fingerprint=FP_A,
        items=[_item()],
    )

    payload = append_operator_history(
        root=tmp_path,
        report_path=report,
    )

    assert payload["status"] == "appended_new_trade_date"
    assert payload["revision_ordinal"] == 1
    assert payload["delta"]["status"] == "baseline_no_previous_observation"
    record = tmp_path / payload["record_path"]
    checked = verify_operator_history_record(record)
    assert checked["status"] == "valid"
    stored = checked["record"]
    assert stored["contract"]["append_only"] is True
    assert stored["contract"]["authoritative_transition"] is False
    assert stored["authoritative_evidence"] is False


def test_exact_rerun_is_idempotent(tmp_path: Path) -> None:
    report = _prepare_source(
        tmp_path,
        trade_date="2026-09-17",
        generated_at="2026-09-17T08:00:00+00:00",
        fingerprint=FP_A,
        items=[_item()],
    )
    first = append_operator_history(root=tmp_path, report_path=report)
    second = append_operator_history(root=tmp_path, report_path=report)

    assert second["status"] == "idempotent_existing"
    assert second["observation_id"] == first["observation_id"]
    files = list(_history(tmp_path).glob("*/*.json"))
    assert len(files) == 1


def test_next_day_delta_uses_latest_previous_trade_date(tmp_path: Path) -> None:
    report = _prepare_source(
        tmp_path,
        trade_date="2026-09-17",
        generated_at="2026-09-17T08:00:00+00:00",
        fingerprint=FP_A,
        items=[_item()],
    )
    append_operator_history(root=tmp_path, report_path=report)

    report = _prepare_source(
        tmp_path,
        trade_date="2026-09-18",
        generated_at="2026-09-18T08:00:00+00:00",
        fingerprint=FP_B,
        items=[
            _item(
                lifecycle="t_plus_1",
                action="reaction_observation",
                next_key=110.0,
            )
        ],
    )
    current = append_operator_history(root=tmp_path, report_path=report)

    assert current["previous_recorded_trade_date"] == "2026-09-17"
    assert current["delta"]["status"] == "ready"
    change = current["delta"]["changes"][0]
    assert change["change_types"] == [
        "action_state_changed",
        "lifecycle_state_changed",
        "next_key_changed",
    ]


def test_same_day_changed_snapshot_appends_revision_without_overwrite(
    tmp_path: Path,
) -> None:
    report = _prepare_source(
        tmp_path,
        trade_date="2026-09-18",
        generated_at="2026-09-18T08:00:00+00:00",
        fingerprint=FP_A,
        items=[_item()],
    )
    first = append_operator_history(root=tmp_path, report_path=report)

    report = _prepare_source(
        tmp_path,
        trade_date="2026-09-18",
        generated_at="2026-09-18T09:00:00+00:00",
        fingerprint=FP_B,
        items=[_item(lifecycle="waiting_terminal")],
    )
    second = append_operator_history(root=tmp_path, report_path=report)

    assert first["revision_ordinal"] == 1
    assert second["status"] == "appended_revision"
    assert second["revision_ordinal"] == 2
    assert first["observation_id"] != second["observation_id"]
    assert len(list(_history(tmp_path).glob("2026-09-18/*.json"))) == 2
    second_record = json.loads(
        (tmp_path / second["record_path"]).read_text(encoding="utf-8")
    )
    assert second_record["previous_same_day_observation_id"] == first["observation_id"]
    assert len(second_record["record_integrity_sha256"]) == 64


def test_older_same_day_revision_is_rejected(tmp_path: Path) -> None:
    report = _prepare_source(
        tmp_path,
        trade_date="2026-09-18",
        generated_at="2026-09-18T09:00:00+00:00",
        fingerprint=FP_A,
        items=[_item()],
    )
    append_operator_history(root=tmp_path, report_path=report)

    report = _prepare_source(
        tmp_path,
        trade_date="2026-09-18",
        generated_at="2026-09-18T08:00:00+00:00",
        fingerprint=FP_B,
        items=[_item(lifecycle="waiting_terminal")],
    )
    with pytest.raises(RuntimeError, match="older_same_day_revision"):
        append_operator_history(root=tmp_path, report_path=report)


def test_historical_backfill_is_rejected(tmp_path: Path) -> None:
    report = _prepare_source(
        tmp_path,
        trade_date="2026-09-18",
        generated_at="2026-09-18T08:00:00+00:00",
        fingerprint=FP_A,
        items=[_item()],
    )
    append_operator_history(root=tmp_path, report_path=report)

    report = _prepare_source(
        tmp_path,
        trade_date="2026-09-17",
        generated_at="2026-09-17T08:00:00+00:00",
        fingerprint=FP_B,
        items=[_item()],
    )
    with pytest.raises(RuntimeError, match="backfill_forbidden"):
        append_operator_history(root=tmp_path, report_path=report)


def test_record_tampering_is_detected(tmp_path: Path) -> None:
    report = _prepare_source(
        tmp_path,
        trade_date="2026-09-18",
        generated_at="2026-09-18T08:00:00+00:00",
        fingerprint=FP_A,
        items=[_item()],
    )
    appended = append_operator_history(root=tmp_path, report_path=report)
    record_path = tmp_path / appended["record_path"]
    payload = json.loads(record_path.read_text(encoding="utf-8"))
    payload["queue_snapshot"]["items"][0]["lifecycle_state"] = "tampered"
    _write_json(record_path, payload)

    checked = verify_operator_history_record(record_path)
    assert checked["status"] == "invalid"
    assert "history_queue_hash_mismatch" in checked["errors"]


def test_query_defaults_to_latest_revision_per_day(tmp_path: Path) -> None:
    report = _prepare_source(
        tmp_path,
        trade_date="2026-09-17",
        generated_at="2026-09-17T08:00:00+00:00",
        fingerprint=FP_A,
        items=[_item()],
    )
    append_operator_history(root=tmp_path, report_path=report)

    report = _prepare_source(
        tmp_path,
        trade_date="2026-09-18",
        generated_at="2026-09-18T08:00:00+00:00",
        fingerprint=FP_A,
        items=[_item(lifecycle="waiting_terminal")],
    )
    append_operator_history(root=tmp_path, report_path=report)

    report = _prepare_source(
        tmp_path,
        trade_date="2026-09-18",
        generated_at="2026-09-18T09:00:00+00:00",
        fingerprint=FP_B,
        items=[_item(lifecycle="t_plus_1", action="reaction_observation")],
    )
    append_operator_history(root=tmp_path, report_path=report)

    payload = query_operator_history(
        history_root=_history(tmp_path),
        instrument_id="SSE.688256",
    )

    assert payload["observation_count"] == 2
    assert payload["observations"][0]["trade_date"] == "2026-09-18"
    assert payload["observations"][0]["revision_ordinal"] == 2
    assert payload["historical_outcome_used_for_ranking"] is False
    assert payload["alpha_inference_allowed"] is False


def test_query_can_expose_all_same_day_revisions(tmp_path: Path) -> None:
    report = _prepare_source(
        tmp_path,
        trade_date="2026-09-18",
        generated_at="2026-09-18T08:00:00+00:00",
        fingerprint=FP_A,
        items=[_item()],
    )
    append_operator_history(root=tmp_path, report_path=report)
    report = _prepare_source(
        tmp_path,
        trade_date="2026-09-18",
        generated_at="2026-09-18T09:00:00+00:00",
        fingerprint=FP_B,
        items=[_item(lifecycle="t_plus_1")],
    )
    append_operator_history(root=tmp_path, report_path=report)

    payload = query_operator_history(
        history_root=_history(tmp_path),
        latest_revision_per_day=False,
    )
    assert payload["observation_count"] == 2
    assert [x["revision_ordinal"] for x in payload["observations"]] == [2, 1]


def test_missing_same_day_revision_breaks_history_integrity(
    tmp_path: Path,
) -> None:
    report = _prepare_source(
        tmp_path,
        trade_date="2026-09-18",
        generated_at="2026-09-18T08:00:00+00:00",
        fingerprint=FP_A,
        items=[_item()],
    )
    first = append_operator_history(root=tmp_path, report_path=report)
    report = _prepare_source(
        tmp_path,
        trade_date="2026-09-18",
        generated_at="2026-09-18T09:00:00+00:00",
        fingerprint=FP_B,
        items=[_item(lifecycle="t_plus_1")],
    )
    append_operator_history(root=tmp_path, report_path=report)

    (tmp_path / first["record_path"]).unlink()

    with pytest.raises(RuntimeError, match="operator_history_integrity_failure"):
        query_operator_history(history_root=_history(tmp_path))


def test_missing_previous_trade_date_baseline_breaks_chain(
    tmp_path: Path,
) -> None:
    report = _prepare_source(
        tmp_path,
        trade_date="2026-09-17",
        generated_at="2026-09-17T08:00:00+00:00",
        fingerprint=FP_A,
        items=[_item()],
    )
    previous = append_operator_history(root=tmp_path, report_path=report)
    report = _prepare_source(
        tmp_path,
        trade_date="2026-09-18",
        generated_at="2026-09-18T08:00:00+00:00",
        fingerprint=FP_B,
        items=[_item(lifecycle="t_plus_1")],
    )
    append_operator_history(root=tmp_path, report_path=report)

    (tmp_path / previous["record_path"]).unlink()

    with pytest.raises(RuntimeError, match="previous_observation_missing"):
        query_operator_history(history_root=_history(tmp_path))


def test_history_link_tampering_is_detected_by_record_hash(
    tmp_path: Path,
) -> None:
    report = _prepare_source(
        tmp_path,
        trade_date="2026-09-18",
        generated_at="2026-09-18T08:00:00+00:00",
        fingerprint=FP_A,
        items=[_item()],
    )
    appended = append_operator_history(root=tmp_path, report_path=report)
    record_path = tmp_path / appended["record_path"]
    payload = json.loads(record_path.read_text(encoding="utf-8"))
    payload["previous_observation_id"] = "f" * 64
    _write_json(record_path, payload)

    checked = verify_operator_history_record(record_path)
    assert checked["status"] == "invalid"
    assert "history_record_integrity_mismatch" in checked["errors"]
