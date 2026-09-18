from __future__ import annotations

from pathlib import Path
import json
import zipfile

from htcn.app.evidence_identity import read_code_identity
from htcn.research.capture_transaction import (
    build_committed_capture,
    commit_capture_transaction,
    freeze_legacy_baseline,
)
from htcn.research.evidence_intake import audit_evidence_bundle
from htcn.research.methodology_identity import build_methodology_identity
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
