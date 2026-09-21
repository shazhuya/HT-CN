from __future__ import annotations

import json
import zipfile
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import scripts.m4_export_evidence_bundle as exporter
from htcn.research.capture_transaction import (
    build_committed_capture,
    commit_capture_transaction,
    freeze_legacy_baseline,
)
from htcn.research.m7_evidence_acceptance import assess_m7_evidence_bundle


def _sha(value: bytes) -> str:
    return sha256(value).hexdigest()


def _write_acceptance_bundle(
    path: Path,
    *,
    bundle_head: str = "bundle-head",
    capture_head: str = "capture-head",
    include_explicit_capture_identity: bool = True,
    qfq_ready: bool = True,
) -> tuple[str, str]:
    root = path.parent / ("captures-" + _sha(bundle_head.encode())[:8])
    root.mkdir()
    freeze_legacy_baseline(
        root,
        [],
        baseline_through_trade_date="2026-09-17",
    )
    capture = build_committed_capture(
        code_head=capture_head,
        as_of_trade_date="2026-09-18",
        captured_at_utc="2026-09-18T08:00:00+00:00",
        instrument_count=1,
        successful_instruments=1,
        failed_instruments=0,
        worktree_clean=True,
        methodology_contract_version=4,
        methodology_fingerprint="a" * 64,
        journal_rows=[],
    )
    commit_capture_transaction(root, capture)

    baseline = (root / "legacy_baseline.json").read_bytes()
    capture_path = root / f"2026-09-18__{capture.transaction_id}.json"
    capture_bytes = capture_path.read_bytes()

    methodology_guard = json.dumps({
        "status": "frozen_match",
        "methodology_component_count": 37,
        "error_count": 0,
    }).encode()
    outcome_guard = json.dumps({
        "status": "frozen_match",
        "outcome_engine_component_count": 4,
        "error_count": 0,
    }).encode()
    qfq = json.dumps({
        "status": "formal_qfq_ready" if qfq_ready else "not_ready",
        "initialized_instruments": 1,
        "formal_ready_after": 1 if qfq_ready else 0,
        "failed_count": 0 if qfq_ready else 1,
    }).encode()
    health = json.dumps({
        "status": "ready",
        "blocker_count": 0,
        "latest_committed_capture_date": "2026-09-18",
        "authoritative_methodology_contract_version": 4,
        "authoritative_methodology_fingerprint": "a" * 64,
    }).encode()

    payloads = {
        "authoritative/legacy_baseline.json": baseline,
        f"authoritative/captures/{capture_path.name}": capture_bytes,
        "reports/m4-methodology-freeze-guard.json": methodology_guard,
        "reports/m4-outcome-engine-freeze-guard.json": outcome_guard,
        "reports/m4-qfq-readiness.json": qfq,
        "reports/m4-evidence-health.json": health,
    }
    files = [
        {
            "arcname": name,
            "size_bytes": len(payload),
            "sha256": _sha(payload),
            "required": name.startswith("authoritative/"),
        }
        for name, payload in sorted(payloads.items())
    ]
    manifest = {
        "schema_version": 1,
        "status": "transport_bundle_ready",
        "code_head": bundle_head,
        "worktree_clean": True,
        "bundle_generation_code_head": bundle_head,
        "bundle_generation_worktree_clean": True,
        "methodology_contract_version": 4,
        "methodology_fingerprint": "a" * 64,
        "committed_capture_count": 1,
        "latest_committed_capture_date": "2026-09-18",
        "latest_capture_transaction_id": capture.transaction_id,
        "evidence_health_blocker_count": 0,
        "committed_capture_read_error": None,
        "alpha_inference_allowed": False,
        "is_trade_instruction": False,
        "authoritative_evidence_modified": False,
        "files": files,
    }
    if include_explicit_capture_identity:
        manifest["latest_capture_code_head"] = capture_head
        manifest["latest_capture_worktree_clean"] = True

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "bundle-manifest.json",
            json.dumps(manifest, sort_keys=True),
        )
        for name, payload in payloads.items():
            archive.writestr(name, payload)
    return capture.transaction_id, capture_head


def test_acceptance_allows_newer_bundle_head_without_rewriting_capture(
    tmp_path: Path,
) -> None:
    path = tmp_path / "evidence.zip"
    transaction_id, capture_head = _write_acceptance_bundle(path)

    result = assess_m7_evidence_bundle(path)

    assert result.status == "accepted"
    assert result.classification == "new_capture"
    assert "bundle_generated_after_latest_capture" in result.warnings
    assert result.summary["latest_capture_code_head"] == capture_head
    assert result.receipt is not None
    assert result.receipt["latest_capture_transaction_id"] == transaction_id
    assert result.receipt["authority_boundary"][
        "statistical_inference_allowed"
    ] is False


def test_acceptance_classifies_same_transaction_as_idempotent_rerun(
    tmp_path: Path,
) -> None:
    path = tmp_path / "evidence.zip"
    transaction_id, _ = _write_acceptance_bundle(path)
    previous = {
        "trade_date": "2026-09-18",
        "independent_inspection": {
            "capture_transaction_id": transaction_id,
            "committed_capture_count": 1,
        },
    }

    result = assess_m7_evidence_bundle(
        path,
        previous_receipt=previous,
    )

    assert result.status == "accepted"
    assert result.classification == "idempotent_rerun"
    assert result.summary["accumulation_status"] == (
        "accumulating_no_outcome_cohort"
    )


def test_acceptance_rejects_same_date_transaction_drift(
    tmp_path: Path,
) -> None:
    path = tmp_path / "evidence.zip"
    _write_acceptance_bundle(
        path,
        capture_head="different-capture-head",
    )
    previous = {
        "trade_date": "2026-09-18",
        "independent_inspection": {
            "capture_transaction_id": "older-transaction",
            "committed_capture_count": 1,
        },
    }

    result = assess_m7_evidence_bundle(
        path,
        previous_receipt=previous,
    )

    assert result.status == "not_ready"
    assert "same_date_capture_transaction_drift" in result.blockers


def test_acceptance_rejects_nonready_qfq_gate(tmp_path: Path) -> None:
    path = tmp_path / "evidence.zip"
    _write_acceptance_bundle(path, qfq_ready=False)

    result = assess_m7_evidence_bundle(path)

    assert result.status == "not_ready"
    assert "qfq_universe_not_formal_ready" in result.blockers
    assert "qfq_universe_coverage_incomplete" in result.blockers


def test_legacy_bundle_without_explicit_capture_head_keeps_old_fail_closed_rule(
    tmp_path: Path,
) -> None:
    path = tmp_path / "legacy.zip"
    _write_acceptance_bundle(
        path,
        include_explicit_capture_identity=False,
    )

    result = assess_m7_evidence_bundle(path)

    assert result.status == "not_ready"
    assert "bundle_code_head_differs_from_latest_capture" in result.blockers


def test_exporter_records_bundle_and_capture_identity_separately(
    tmp_path: Path,
    monkeypatch,
) -> None:
    transaction_root = tmp_path / "captures"
    transaction_root.mkdir()
    (transaction_root / "legacy_baseline.json").write_text(
        "{}",
        encoding="utf-8",
    )
    (transaction_root / "2026-09-21__tx.json").write_text(
        "{}",
        encoding="utf-8",
    )
    reports = tmp_path / "reports"
    reports.mkdir()

    monkeypatch.setattr(
        exporter,
        "read_code_identity",
        lambda: SimpleNamespace(
            head="bundle-head",
            worktree_clean=True,
        ),
    )
    monkeypatch.setattr(
        exporter,
        "build_methodology_identity",
        lambda: SimpleNamespace(
            contract_version=4,
            fingerprint="a" * 64,
        ),
    )
    monkeypatch.setattr(
        exporter,
        "build_outcome_engine_identity",
        lambda: SimpleNamespace(
            contract_version=1,
            fingerprint="b" * 64,
        ),
    )
    monkeypatch.setattr(
        exporter,
        "load_outcome_protocol",
        lambda: (
            None,
            SimpleNamespace(
                protocol_id="m4-outcome-v2",
                fingerprint="c" * 64,
            ),
        ),
    )
    monkeypatch.setattr(
        exporter,
        "build_evidence_chain_health",
        lambda **_: {"status": "ready", "blocker_count": 0},
    )
    monkeypatch.setattr(
        exporter,
        "read_committed_captures",
        lambda _: [{
            "as_of_trade_date": "2026-09-21",
            "transaction_id": "tx",
            "code_head": "capture-head",
            "worktree_clean": True,
        }],
    )

    payload = exporter.build_bundle(
        transaction_root=transaction_root,
        journal_path=tmp_path / "journal.jsonl",
        manifest_path=tmp_path / "manifest.jsonl",
        reports_root=reports,
        output=reports / "bundle.zip",
        outcome_root=None,
    )

    assert payload["code_head"] == "bundle-head"
    assert payload["bundle_generation_code_head"] == "bundle-head"
    assert payload["latest_capture_code_head"] == "capture-head"
    assert payload["latest_capture_worktree_clean"] is True



def test_acceptance_allows_no_qfq_report_for_verified_idempotent_noop(
    tmp_path: Path,
) -> None:
    path = tmp_path / "noop.zip"
    transaction_id, _ = _write_acceptance_bundle(path)
    with zipfile.ZipFile(path, "r") as source:
        payloads = {
            name: source.read(name)
            for name in source.namelist()
            if name not in {
                "bundle-manifest.json",
                "reports/m4-qfq-readiness.json",
            }
        }
        manifest = json.loads(source.read("bundle-manifest.json"))
    precheck = json.dumps({
        "status": "ready",
        "action": "idempotent_noop",
        "append_required": False,
        "latest_closed_trade_date": "2026-09-18",
        "latest_committed_capture_date": "2026-09-18",
        "pending_closed_trade_count": 0,
    }).encode()
    payloads["reports/m7-append-precheck.json"] = precheck
    manifest["files"] = [
        {
            "arcname": name,
            "size_bytes": len(payload),
            "sha256": _sha(payload),
            "required": name.startswith("authoritative/"),
        }
        for name, payload in sorted(payloads.items())
    ]
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("bundle-manifest.json", json.dumps(manifest, sort_keys=True))
        for name, payload in payloads.items():
            archive.writestr(name, payload)

    result = assess_m7_evidence_bundle(path)

    assert result.status == "accepted"
    assert result.classification == "idempotent_rerun"
    assert "qfq_not_rerun_for_idempotent_noop" in result.warnings
    assert result.summary["append_action"] == "idempotent_noop"


def test_acceptance_rejects_no_qfq_when_noop_precheck_has_pending_session(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bad-noop.zip"
    _write_acceptance_bundle(path)
    with zipfile.ZipFile(path, "r") as source:
        payloads = {
            name: source.read(name)
            for name in source.namelist()
            if name not in {
                "bundle-manifest.json",
                "reports/m4-qfq-readiness.json",
            }
        }
        manifest = json.loads(source.read("bundle-manifest.json"))
    precheck = json.dumps({
        "status": "ready",
        "action": "idempotent_noop",
        "append_required": False,
        "latest_closed_trade_date": "2026-09-22",
        "latest_committed_capture_date": "2026-09-18",
        "pending_closed_trade_count": 1,
    }).encode()
    payloads["reports/m7-append-precheck.json"] = precheck
    manifest["files"] = [
        {
            "arcname": name,
            "size_bytes": len(payload),
            "sha256": _sha(payload),
            "required": name.startswith("authoritative/"),
        }
        for name, payload in sorted(payloads.items())
    ]
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("bundle-manifest.json", json.dumps(manifest, sort_keys=True))
        for name, payload in payloads.items():
            archive.writestr(name, payload)

    result = assess_m7_evidence_bundle(path)

    assert result.status == "not_ready"
    assert "idempotent_noop_market_clock_mismatch" in result.blockers
    assert "idempotent_noop_has_pending_closed_sessions" in result.blockers
