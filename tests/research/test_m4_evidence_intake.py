from __future__ import annotations

from pathlib import Path
import json
import zipfile

import pandas as pd

from htcn.app.evidence_identity import read_code_identity
from htcn.research.capture_transaction import (
    build_committed_capture,
    commit_capture_transaction,
    committed_capture_view,
    freeze_legacy_baseline,
    read_committed_captures,
)
from htcn.research.evidence_intake import audit_evidence_bundle
from htcn.research.methodology_identity import build_methodology_identity
from htcn.research.outcome_evaluator import evaluate_candidate_outcome
from htcn.research.outcome_protocol import load_outcome_protocol_v1
from htcn.research.outcome_snapshot import (
    build_outcome_snapshot,
    commit_outcome_snapshot,
)
from htcn.research.prospective_observations import (
    build_prospective_observation_report,
)
from scripts.m4_export_evidence_bundle import build_bundle


def _write_bundle(
    path: Path,
    *,
    manifest_status: str = "transport_bundle_ready",
    health_blockers: int = 0,
) -> None:
    baseline = {
        "schema_version": 1,
        "status": "frozen_legacy_baseline",
        "baseline_id": "placeholder",
        "baseline_through_trade_date": "2026-09-17",
        "row_count": 0,
        "journal_rows": [],
        "alpha_inference_allowed": False,
        "is_trade_instruction": False,
    }
    # Intentionally minimal/invalid authoritative baseline is sufficient for
    # intake fail-closed tests. Transport integrity remains independently valid.
    baseline_bytes = (json.dumps(baseline, sort_keys=True) + "\n").encode()

    health = {
        "status": "ready" if health_blockers == 0 else "not_ready",
        "blocker_count": health_blockers,
        "transition_evidence_chain_ready": health_blockers == 0,
        "latest_committed_capture_date": None,
        "authoritative_methodology_fingerprint": None,
        "authoritative_methodology_contract_version": None,
    }
    health_bytes = (json.dumps(health, sort_keys=True) + "\n").encode()

    import hashlib
    records = []
    for name, payload in (
        ("authoritative/legacy_baseline.json", baseline_bytes),
        ("reports/m4-evidence-health.json", health_bytes),
    ):
        records.append({
            "arcname": name,
            "size_bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "required": name.startswith("authoritative/"),
        })

    manifest = {
        "schema_version": 1,
        "status": manifest_status,
        "code_head": "test-head",
        "worktree_clean": True,
        "methodology_contract_version": 1,
        "methodology_fingerprint": "1" * 64,
        "committed_capture_count": 0,
        "latest_committed_capture_date": None,
        "latest_capture_transaction_id": None,
        "evidence_health_status": health["status"],
        "evidence_health_blocker_count": health_blockers,
        "committed_capture_read_error": None,
        "alpha_inference_allowed": False,
        "is_trade_instruction": False,
        "authoritative_evidence_modified": False,
        "files": records,
    }

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("bundle-manifest.json", json.dumps(manifest, sort_keys=True))
        archive.writestr("authoritative/legacy_baseline.json", baseline_bytes)
        archive.writestr("reports/m4-evidence-health.json", health_bytes)


def test_intake_rejects_missing_bundle(tmp_path: Path) -> None:
    result = audit_evidence_bundle(tmp_path / "missing.zip")
    assert result.status == "not_ready"
    assert "transport_integrity_invalid" in result.blockers


def test_intake_blocks_health_blocked_bundle(tmp_path: Path) -> None:
    path = tmp_path / "blocked.zip"
    _write_bundle(
        path,
        manifest_status="evidence_health_blocked",
        health_blockers=2,
    )
    result = audit_evidence_bundle(
        path,
        expected_baseline_trade_date="2026-09-17",
    )
    assert result.status == "not_ready"
    assert "bundle_evidence_health_blocked" in result.blockers


def test_intake_fails_closed_on_invalid_authoritative_baseline(tmp_path: Path) -> None:
    path = tmp_path / "invalid-baseline.zip"
    _write_bundle(path)
    result = audit_evidence_bundle(
        path,
        expected_baseline_trade_date="2026-09-17",
    )
    assert result.status == "not_ready"
    assert any(
        item.startswith("authoritative_intake_error:")
        for item in result.blockers
    )


def test_intake_keeps_alpha_and_trade_boundaries_false(tmp_path: Path) -> None:
    path = tmp_path / "boundary.zip"
    _write_bundle(path)
    result = audit_evidence_bundle(path)
    assert result.summary["alpha_inference_allowed"] is False
    assert result.summary["is_trade_instruction"] is False
    assert result.summary["authoritative_evidence_modified"] is False


def test_intake_accepts_valid_post_t0_zero_candidate_capture(tmp_path: Path) -> None:
    transaction_root = tmp_path / "captures"
    journal_path = tmp_path / "journal.jsonl"
    manifest_path = tmp_path / "manifest.jsonl"
    reports_root = tmp_path / "reports"
    reports_root.mkdir()

    freeze_legacy_baseline(
        transaction_root,
        [],
        baseline_through_trade_date="2026-09-17",
    )

    identity = read_code_identity()
    methodology = build_methodology_identity()
    capture = build_committed_capture(
        code_head=identity.head,
        as_of_trade_date="2026-09-18",
        captured_at_utc="2026-09-18T08:00:00+00:00",
        instrument_count=1,
        successful_instruments=1,
        failed_instruments=0,
        worktree_clean=True,
        methodology_contract_version=methodology.contract_version,
        methodology_fingerprint=methodology.fingerprint,
        journal_rows=[],
    )
    commit_capture_transaction(transaction_root, capture)

    output = reports_root / "bundle.zip"
    build_bundle(
        transaction_root=transaction_root,
        journal_path=journal_path,
        manifest_path=manifest_path,
        reports_root=reports_root,
        output=output,
    )

    result = audit_evidence_bundle(
        output,
        expected_baseline_trade_date="2026-09-17",
    )
    assert result.blocker_count == 0
    assert result.status in {"ready", "ready_with_warnings"}
    assert result.summary["committed_capture_count"] == 1
    assert result.summary["latest_committed_capture_date"] == "2026-09-18"
    assert result.summary["prospective_new_candidate_count"] == 0
    assert result.summary["prospective_outcome_eligible_candidate_count"] == 0



FORMAL_BASIS = "qfq:" + "1" * 64


def _formal_outcome_candidate_row(*, code_head: str) -> dict:
    return {
        "code_head": code_head,
        "instrument_id": "SSE.600000",
        "as_of_trade_date": "2026-09-18",
        "candidate_key": "candidate-a",
        "pattern_id": "abcd",
        "schema": "ABCD",
        "direction": "bullish",
        "scale": 5,
        "pattern_state": "forming",
        "source_lifecycle_state": "approaching_source_prz",
        "action_state": "waiting",
        "next_key_price": 97.0,
        "next_key_price_role": "source_prz_entry_edge",
        "execution_context_gate": "tradable",
        "context_integrity_summary": "complete",
        "price_mode": "qfq",
        "price_basis_id": FORMAL_BASIS,
        "source_prz_low": 95.0,
        "source_prz_high": 97.0,
        "source_terminal_trade_date": None,
        "eligible_for_validation": True,
        "source_signal_trade_date": "2026-09-17",
        "source_signal_clock_basis": (
            "last_frontier_pivot_confirmed_at=index+scale"
        ),
        "source_reaction_anchor_label": "A",
        "source_reaction_anchor_price": 110.0,
        "underlying_last_trade_date": "2026-09-18",
        "market_observation_status": "traded",
        "as_of_open": 100.0,
        "as_of_high": 102.0,
        "as_of_low": 98.0,
        "as_of_close": 99.0,
        "as_of_volume": 1000.0,
        "evidence_only": True,
        "is_trade_instruction": False,
        "alpha_inference_allowed": False,
    }


def _write_offline_recomputable_outcome_bundle(
    tmp_path: Path,
    *,
    tamper_source_events: bool = False,
) -> Path:
    transaction_root = tmp_path / "outcome-captures"
    outcome_root = tmp_path / "outcome-snapshots"
    reports_root = tmp_path / "outcome-reports"
    reports_root.mkdir()

    freeze_legacy_baseline(
        transaction_root,
        [],
        baseline_through_trade_date="2026-09-17",
    )
    identity = read_code_identity()
    methodology = build_methodology_identity()
    capture = build_committed_capture(
        code_head=identity.head,
        as_of_trade_date="2026-09-18",
        captured_at_utc="2026-09-18T08:00:00+00:00",
        instrument_count=1,
        successful_instruments=1,
        failed_instruments=0,
        worktree_clean=True,
        methodology_contract_version=methodology.contract_version,
        methodology_fingerprint=methodology.fingerprint,
        journal_rows=[
            _formal_outcome_candidate_row(code_head=identity.head)
        ],
    )
    commit_capture_transaction(transaction_root, capture)

    committed = read_committed_captures(transaction_root)
    rows, manifest_rows = committed_capture_view(
        legacy_journal_rows=[],
        capture_rows=committed,
    )
    panel = build_prospective_observation_report(
        rows,
        manifest_rows=manifest_rows,
        followup_rows=[],
        legacy_baseline_trade_date="2026-09-17",
    )
    assert panel["prospective_candidate_count"] == 1
    summary = panel["candidate_summaries"][0]

    market = pd.DataFrame([
        {
            "trade_date": "2026-09-17",
            "open": 104.0,
            "high": 106.0,
            "low": 103.0,
            "close": 105.0,
            "volume": 900.0,
        },
        {
            "trade_date": "2026-09-18",
            "open": 100.0,
            "high": 102.0,
            "low": 98.0,
            "close": 99.0,
            "volume": 1000.0,
        },
    ])
    protocol, protocol_identity = load_outcome_protocol_v1()
    result = evaluate_candidate_outcome(
        summary,
        market,
        outcome_as_of_trade_date="2026-09-18",
        current_price_mode="qfq",
        current_price_basis_id=FORMAL_BASIS,
        methodology_fingerprint=methodology.fingerprint,
        protocol=protocol,
    )
    assert result["status"] == "right_censored_ongoing"
    if tamper_source_events:
        result = dict(result)
        result["source_events"] = dict(result["source_events"])
        result["source_events"]["source_terminal_observed"] = True

    snapshot = build_outcome_snapshot(
        outcome_as_of_trade_date="2026-09-18",
        outcome_protocol_id=protocol_identity.protocol_id,
        outcome_protocol_fingerprint=protocol_identity.fingerprint,
        capture_methodology_fingerprint=methodology.fingerprint,
        results=[result],
    )
    commit_outcome_snapshot(outcome_root, snapshot)

    output = reports_root / "bundle.zip"
    build_bundle(
        transaction_root=transaction_root,
        journal_path=tmp_path / "journal.jsonl",
        manifest_path=tmp_path / "manifest.jsonl",
        reports_root=reports_root,
        output=output,
        outcome_root=outcome_root,
    )
    return output


def test_intake_offline_recomputes_valid_outcome_snapshot(
    tmp_path: Path,
) -> None:
    path = _write_offline_recomputable_outcome_bundle(tmp_path)
    result = audit_evidence_bundle(
        path,
        expected_baseline_trade_date="2026-09-17",
    )
    assert result.blocker_count == 0
    assert result.status in {"ready", "ready_with_warnings"}
    assert result.summary["outcome_snapshot_count"] == 1
    assert result.summary["outcome_result_count"] == 1
    assert result.summary["outcome_status_counts"] == {
        "right_censored_ongoing": 1
    }


def test_intake_detects_semantic_outcome_tamper_even_when_snapshot_is_rehashed(
    tmp_path: Path,
) -> None:
    path = _write_offline_recomputable_outcome_bundle(
        tmp_path,
        tamper_source_events=True,
    )
    result = audit_evidence_bundle(
        path,
        expected_baseline_trade_date="2026-09-17",
    )
    assert result.status == "not_ready"
    assert "outcome_result_recompute_drift:candidate-a" in result.blockers
