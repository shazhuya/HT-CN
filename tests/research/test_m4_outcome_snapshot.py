from __future__ import annotations

from copy import deepcopy

import pytest

from htcn.research.outcome_snapshot import (
    build_outcome_snapshot,
    commit_outcome_snapshot,
    read_outcome_snapshots,
)


PROTOCOL = "b" * 64
METHOD = "a" * 64


def _result(
    *,
    candidate: str = "candidate-a",
    as_of: str = "2026-09-28",
    path_hash: str = "c" * 64,
) -> dict:
    return {
        "schema_version": 1,
        "candidate_key": candidate,
        "instrument_id": "SSE.600000",
        "outcome_enrollment_trade_date": "2026-09-17",
        "outcome_as_of_trade_date": as_of,
        "capture_methodology_fingerprint": METHOD,
        "outcome_protocol_id": "m4-outcome-v1",
        "outcome_protocol_fingerprint": PROTOCOL,
        "market_path_sha256": path_hash,
        "status": "right_censored_ongoing",
        "source_events": {},
        "descriptive_path_windows": {},
        "interpretation": {
            "evidence_only": True,
            "is_trade_instruction": False,
            "alpha_inference_allowed": False,
        },
    }


def _snapshot(*results: dict):
    return build_outcome_snapshot(
        outcome_as_of_trade_date="2026-09-28",
        outcome_protocol_id="m4-outcome-v1",
        outcome_protocol_fingerprint=PROTOCOL,
        capture_methodology_fingerprint=METHOD,
        results=results,
    )


def test_outcome_snapshot_is_deterministic_under_candidate_order() -> None:
    first = _snapshot(
        _result(candidate="b", path_hash="d" * 64),
        _result(candidate="a", path_hash="e" * 64),
    )
    second = _snapshot(
        _result(candidate="a", path_hash="e" * 64),
        _result(candidate="b", path_hash="d" * 64),
    )
    assert first.snapshot_id == second.snapshot_id


def test_outcome_snapshot_commit_is_atomic_and_idempotent(tmp_path) -> None:
    snapshot = _snapshot(_result())
    first = commit_outcome_snapshot(tmp_path, snapshot)
    second = commit_outcome_snapshot(tmp_path, snapshot)
    assert first["status"] == "committed"
    assert second["status"] == "already_committed"
    stored = read_outcome_snapshots(tmp_path)
    assert len(stored) == 1
    assert stored[0]["snapshot_id"] == snapshot.snapshot_id


def test_same_as_of_changed_market_path_fails_closed(tmp_path) -> None:
    first = _snapshot(_result(path_hash="c" * 64))
    commit_outcome_snapshot(tmp_path, first)

    changed = _snapshot(_result(path_hash="d" * 64))
    with pytest.raises(ValueError, match="outcome data drift"):
        commit_outcome_snapshot(tmp_path, changed)

    stored = read_outcome_snapshots(tmp_path)
    assert len(stored) == 1
    assert stored[0]["snapshot_id"] == first.snapshot_id


def test_duplicate_candidate_in_one_snapshot_fails_closed() -> None:
    with pytest.raises(ValueError, match="duplicate outcome candidate"):
        _snapshot(_result(), _result())


def test_outcome_snapshot_rejects_prohibited_v1_fields() -> None:
    result = _result()
    result["win_rate"] = 0.8
    with pytest.raises(ValueError, match="prohibited outcome-v1"):
        _snapshot(result)


def test_outcome_snapshot_rejects_alpha_boundary_crossing() -> None:
    result = _result()
    result["interpretation"]["alpha_inference_allowed"] = True
    with pytest.raises(ValueError, match="alpha boundary"):
        _snapshot(result)


def test_tampered_snapshot_id_is_detected(tmp_path) -> None:
    import json

    snapshot = _snapshot(_result())
    committed = commit_outcome_snapshot(tmp_path, snapshot)
    path = tmp_path / committed["path"].split("/")[-1]
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["results"][0]["market_path_sha256"] = "f" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="snapshot id mismatch"):
        read_outcome_snapshots(tmp_path)


def test_result_as_of_drift_fails_closed() -> None:
    result = deepcopy(_result())
    result["outcome_as_of_trade_date"] = "2026-09-29"
    with pytest.raises(ValueError, match="as-of drift"):
        _snapshot(result)
