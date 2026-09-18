from __future__ import annotations

from pathlib import Path
import json
import zipfile

from htcn.research.evidence_intake import audit_evidence_bundle


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
