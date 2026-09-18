from __future__ import annotations

from copy import deepcopy

import pandas as pd
import pytest

from htcn.research.outcome_evaluator import canonical_market_path_hash
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
    close: float = 100.0,
) -> dict:
    rows = [{
        "trade_date": "2026-09-28",
        "open": 99.0,
        "high": 101.0,
        "low": 98.0,
        "close": close,
        "volume": 1000.0,
    }]
    path_hash = canonical_market_path_hash(
        pd.DataFrame(rows),
        price_basis_id="qfq:" + "1" * 64,
    )
    return {
        "schema_version": 1,
        "candidate_key": candidate,
        "instrument_id": "SSE.600000",
        "outcome_enrollment_trade_date": "2026-09-17",
        "outcome_as_of_trade_date": as_of,
        "capture_methodology_fingerprint": METHOD,
        "outcome_engine_contract_version": 1,
        "outcome_engine_fingerprint": "d" * 64,
        "outcome_protocol_id": "m4-outcome-v1",
        "outcome_protocol_fingerprint": PROTOCOL,
        "current_price_basis_id": "qfq:" + "1" * 64,
        "market_path_trade_dates": ["2026-09-28"],
        "market_path_traded_bar_count": 1,
        "market_path_rows": rows,
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
        _result(candidate="b", close=100.0),
        _result(candidate="a", close=101.0),
    )
    second = _snapshot(
        _result(candidate="a", close=101.0),
        _result(candidate="b", close=100.0),
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
    first = _snapshot(_result(close=100.0))
    commit_outcome_snapshot(tmp_path, first)

    changed = _snapshot(_result(close=100.5))
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
    with pytest.raises(ValueError, match="prohibited outcome result"):
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
    payload["results"][0]["market_path_rows"][0]["close"] = 100.5
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="market path hash mismatch"):
        read_outcome_snapshots(tmp_path)


def test_result_as_of_drift_fails_closed() -> None:
    result = deepcopy(_result())
    result["outcome_as_of_trade_date"] = "2026-09-29"
    with pytest.raises(ValueError, match="as-of drift"):
        _snapshot(result)



def test_outcome_snapshot_chain_rejects_engine_identity_drift(tmp_path) -> None:
    first = _snapshot(_result())
    commit_outcome_snapshot(tmp_path, first)

    changed_result = _result(as_of="2026-09-29")
    changed_result["outcome_engine_fingerprint"] = "e" * 64
    changed = build_outcome_snapshot(
        outcome_as_of_trade_date="2026-09-29",
        outcome_protocol_id="m4-outcome-v1",
        outcome_protocol_fingerprint=PROTOCOL,
        capture_methodology_fingerprint=METHOD,
        results=[changed_result],
    )
    with pytest.raises(ValueError, match="outcome chain identity drift"):
        commit_outcome_snapshot(tmp_path, changed)


def test_outcome_snapshot_chain_rejects_historical_backfill(tmp_path) -> None:
    later_result = _result(as_of="2026-09-29")
    later = build_outcome_snapshot(
        outcome_as_of_trade_date="2026-09-29",
        outcome_protocol_id="m4-outcome-v1",
        outcome_protocol_fingerprint=PROTOCOL,
        capture_methodology_fingerprint=METHOD,
        results=[later_result],
    )
    commit_outcome_snapshot(tmp_path, later)

    earlier = _snapshot(_result())
    with pytest.raises(ValueError, match="forbids historical backfill"):
        commit_outcome_snapshot(tmp_path, earlier)
