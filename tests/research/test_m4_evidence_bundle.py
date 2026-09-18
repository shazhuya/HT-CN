from __future__ import annotations

import json
from pathlib import Path
import zipfile

from scripts.m4_export_evidence_bundle import build_bundle


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
    with zipfile.ZipFile(output) as archive:
        assert (
            "authoritative/captures/2026-09-18__broken.json"
            in archive.namelist()
        )
