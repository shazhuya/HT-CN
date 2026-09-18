from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import zipfile

from htcn.research.evidence_bundle import verify_evidence_bundle
from htcn.research.evidence_intake import audit_evidence_bundle
from htcn.research.capture_transaction import (\n    build_committed_capture,\n    commit_capture_transaction,\n    freeze_legacy_baseline,\n)\nfrom scripts.m4_export_evidence_bundle import build_bundle


def _bundle(tmp_path: Path):
    transaction_root = tmp_path / "captures"
    transaction_root.mkdir()
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "m4-m1-update.log").write_text(
        "[HT-CN M1 DAILY] test log\n",
        encoding="utf-8",
    )
    (reports / "m4-lifecycle-snapshot.json").write_text(
        json.dumps({"status": "diagnostic"}),
        encoding="utf-8",
    )
    output = reports / "bundle.zip"
    payload = build_bundle(
        transaction_root=transaction_root,
        journal_path=tmp_path / "journal.jsonl",
        manifest_path=tmp_path / "manifest.jsonl",
        reports_root=reports,
        output=output,
    )
    return output, payload


def test_transport_bundle_contains_manifest_and_available_reports(tmp_path) -> None:
    output, payload = _bundle(tmp_path)
    assert output.is_file()
    assert payload["alpha_inference_allowed"] is False
    assert payload["authoritative_evidence_modified"] is False
    assert payload["transport_verification"]["status"] == "valid"

    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert "bundle-manifest.json" in names
        assert "reports/m4-m1-update.log" in names
        assert "reports/m4-lifecycle-snapshot.json" in names
        manifest = json.loads(
            archive.read("bundle-manifest.json").decode("utf-8")
        )
    assert manifest["interpretation"].startswith(
        "This ZIP is a transport bundle only."
    )


def test_transport_bundle_preserves_corrupt_capture_for_diagnosis(tmp_path) -> None:
    transaction_root = tmp_path / "captures"
    transaction_root.mkdir()
    broken = transaction_root / "2026-09-18__broken.json"
    broken.write_text("{broken", encoding="utf-8")

    reports = tmp_path / "reports"
    reports.mkdir()
    output = reports / "bundle.zip"
    payload = build_bundle(
        transaction_root=transaction_root,
        journal_path=tmp_path / "journal.jsonl",
        manifest_path=tmp_path / "manifest.jsonl",
        reports_root=reports,
        output=output,
    )

    assert payload["status"] == "evidence_health_blocked"
    assert payload["committed_capture_read_error"] is not None
    assert payload["transport_verification"]["status"] == "valid"
    with zipfile.ZipFile(output) as archive:
        assert (
            "authoritative/captures/2026-09-18__broken.json"
            in archive.namelist()
        )


def _write_verifier_bundle(
    path: Path,
    *,
    payloads: dict[str, bytes] | None = None,
    status: str = "transport_bundle_ready",
    blocker_count: int = 0,
    mutate_record_sha: bool = False,
    extra_member: tuple[str, bytes] | None = None,
) -> None:
    payloads = payloads or {
        "authoritative/legacy_baseline.json": b"{}\n",
        "reports/m4-evidence-health.json": b"{}\n",
    }
    files = []
    for name, payload in payloads.items():
        digest = sha256(payload).hexdigest()
        if mutate_record_sha and not files:
            digest = "0" * 64
        files.append(
            {
                "arcname": name,
                "size_bytes": len(payload),
                "sha256": digest,
                "required": name.startswith("authoritative/"),
            }
        )

    manifest = {
        "schema_version": 1,
        "status": status,
        "methodology_contract_version": 1,
        "methodology_fingerprint": "1" * 64,
        "committed_capture_count": 0,
        "latest_committed_capture_date": None,
        "latest_capture_transaction_id": None,
        "evidence_health_blocker_count": blocker_count,
        "committed_capture_read_error": None,
        "alpha_inference_allowed": False,
        "is_trade_instruction": False,
        "authoritative_evidence_modified": False,
        "files": files,
    }

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "bundle-manifest.json",
            json.dumps(manifest, ensure_ascii=False, sort_keys=True),
        )
        for name, payload in payloads.items():
            archive.writestr(name, payload)
        if extra_member is not None:
            archive.writestr(extra_member[0], extra_member[1])


def test_bundle_verifier_accepts_valid_transport_bundle(tmp_path: Path) -> None:
    path = tmp_path / "evidence.zip"
    _write_verifier_bundle(path)
    result = verify_evidence_bundle(path)
    assert result.status == "valid"
    assert result.error_count == 0


def test_bundle_verifier_rejects_tampered_member_hash(tmp_path: Path) -> None:
    path = tmp_path / "evidence.zip"
    _write_verifier_bundle(path, mutate_record_sha=True)
    result = verify_evidence_bundle(path)
    assert result.status == "invalid"
    assert any(item.startswith("sha256_mismatch:") for item in result.errors)


def test_bundle_verifier_rejects_unlisted_member(tmp_path: Path) -> None:
    path = tmp_path / "evidence.zip"
    _write_verifier_bundle(
        path,
        extra_member=("reports/unlisted.json", b"{}\n"),
    )
    result = verify_evidence_bundle(path)
    assert result.status == "invalid"
    assert any(item.startswith("unlisted_archive_member:") for item in result.errors)


def test_bundle_verifier_rejects_path_traversal_member(tmp_path: Path) -> None:
    path = tmp_path / "evidence.zip"
    _write_verifier_bundle(path, extra_member=("../escape.txt", b"x"))
    result = verify_evidence_bundle(path)
    assert result.status == "invalid"
    assert any(item.startswith("unsafe_archive_member:") for item in result.errors)


def test_blocked_bundle_can_be_transport_valid_with_warning(tmp_path: Path) -> None:
    path = tmp_path / "evidence.zip"
    _write_verifier_bundle(
        path,
        status="evidence_health_blocked",
        blocker_count=2,
    )
    result = verify_evidence_bundle(path)
    assert result.status == "valid"
    assert "bundle_reports_evidence_health_blocked" in result.warnings


def test_ready_bundle_cannot_claim_health_blockers(tmp_path: Path) -> None:
    path = tmp_path / "evidence.zip"
    _write_verifier_bundle(
        path,
        status="transport_bundle_ready",
        blocker_count=1,
    )
    result = verify_evidence_bundle(path)
    assert result.status == "invalid"
    assert "ready_bundle_has_health_blockers" in result.errors



def _write_intake_bundle(
    path: Path,
    *,
    baseline_date: str = "2026-09-17",
    capture_date: str = "2026-09-18",
    bundle_fingerprint: str = "2" * 64,
    chain_fingerprint: str = "2" * 64,
    tamper_capture_after_commit: bool = False,
    include_drifted_transition: bool = False,
    include_health_blocker: bool = False,
) -> None:
    root = path.parent / "intake-captures"
    root.mkdir()
    freeze_legacy_baseline(
        root,
        [],
        baseline_through_trade_date=baseline_date,
    )
    capture = build_committed_capture(
        code_head="abc123",
        as_of_trade_date=capture_date,
        captured_at_utc="2026-09-18T08:00:00+00:00",
        instrument_count=1,
        successful_instruments=1,
        failed_instruments=0,
        worktree_clean=True,
        methodology_contract_version=1,
        methodology_fingerprint=chain_fingerprint,
        journal_rows=[],
    )
    commit_capture_transaction(root, capture)

    capture_path = root / f"{capture_date}__{capture.transaction_id}.json"
    if tamper_capture_after_commit:
        value = json.loads(capture_path.read_text(encoding="utf-8"))
        value["worktree_clean"] = False
        capture_path.write_text(
            json.dumps(value, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )

    payloads: dict[str, bytes] = {
        "authoritative/legacy_baseline.json": (
            root / "legacy_baseline.json"
        ).read_bytes(),
        f"authoritative/captures/{capture_path.name}": capture_path.read_bytes(),
    }
    if include_drifted_transition:
        payloads["reports/m4-lifecycle-transitions.json"] = json.dumps(
            {
                "status": "transitions_available",
                "date_count": 999,
                "baseline_trade_date": baseline_date,
                "latest_trade_date": capture_date,
            },
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    if include_health_blocker:
        payloads["reports/m4-evidence-health.json"] = json.dumps(
            {
                "blocker_count": 1,
                "latest_committed_capture_date": capture_date,
                "authoritative_methodology_fingerprint": chain_fingerprint,
            },
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")

    records = [
        {
            "arcname": name,
            "size_bytes": len(payload),
            "sha256": sha256(payload).hexdigest(),
            "required": name.startswith("authoritative/"),
        }
        for name, payload in sorted(payloads.items())
    ]
    manifest = {
        "schema_version": 1,
        "status": "transport_bundle_ready",
        "methodology_contract_version": 1,
        "methodology_fingerprint": bundle_fingerprint,
        "committed_capture_count": 1,
        "latest_committed_capture_date": capture_date,
        "latest_capture_transaction_id": capture.transaction_id,
        "evidence_health_blocker_count": 0,
        "committed_capture_read_error": None,
        "alpha_inference_allowed": False,
        "is_trade_instruction": False,
        "authoritative_evidence_modified": False,
        "files": records,
    }
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "bundle-manifest.json",
            json.dumps(manifest, ensure_ascii=False, sort_keys=True),
        )
        for name, payload in payloads.items():
            archive.writestr(name, payload)


def test_intake_recomputes_authoritative_t1_without_derived_reports(tmp_path: Path) -> None:
    path = tmp_path / "t1.zip"
    _write_intake_bundle(path)
    result = audit_evidence_bundle(
        path,
        expected_baseline_trade_date="2026-09-17",
    )
    assert result.status == "ready_with_warnings"
    assert result.blocker_count == 0
    assert result.summary["committed_capture_count"] == 1
    assert result.summary["committed_capture_dates"] == ["2026-09-18"]
    assert result.summary["capture_timeline"] == ["2026-09-17", "2026-09-18"]


def test_intake_rejects_bundle_methodology_drift(tmp_path: Path) -> None:
    path = tmp_path / "t1.zip"
    _write_intake_bundle(
        path,
        bundle_fingerprint="3" * 64,
        chain_fingerprint="2" * 64,
    )
    result = audit_evidence_bundle(path, expected_baseline_trade_date="2026-09-17")
    assert result.status == "not_ready"
    assert "bundle_methodology_differs_from_committed_chain" in result.blockers


def test_intake_rejects_wrong_frozen_baseline_date(tmp_path: Path) -> None:
    path = tmp_path / "t1.zip"
    _write_intake_bundle(path, baseline_date="2026-09-16")
    result = audit_evidence_bundle(path, expected_baseline_trade_date="2026-09-17")
    assert result.status == "not_ready"
    assert "unexpected_frozen_baseline_trade_date" in result.blockers


def test_intake_rejects_authoritative_capture_tamper_even_when_zip_hashes_match(
    tmp_path: Path,
) -> None:
    path = tmp_path / "t1.zip"
    _write_intake_bundle(path, tamper_capture_after_commit=True)
    result = audit_evidence_bundle(path, expected_baseline_trade_date="2026-09-17")
    assert result.status == "not_ready"
    assert any(
        item.startswith("authoritative_intake_error:")
        for item in result.blockers
    )


def test_intake_rejects_derived_transition_report_drift(tmp_path: Path) -> None:
    path = tmp_path / "t1.zip"
    _write_intake_bundle(path, include_drifted_transition=True)
    result = audit_evidence_bundle(path, expected_baseline_trade_date="2026-09-17")
    assert result.status == "not_ready"
    assert any(item.startswith("transition_report_drift:") for item in result.blockers)


def test_intake_rejects_included_evidence_health_blocker(tmp_path: Path) -> None:
    path = tmp_path / "t1.zip"
    _write_intake_bundle(path, include_health_blocker=True)
    result = audit_evidence_bundle(path, expected_baseline_trade_date="2026-09-17")
    assert result.status == "not_ready"
    assert "evidence_health_report_has_blockers" in result.blockers
