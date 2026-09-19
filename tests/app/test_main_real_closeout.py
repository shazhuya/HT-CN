from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from htcn.app import main_real_browser_audit as browser
from htcn.app import main_real_closeout as closeout


HEAD = "1" * 40
IDENTITY = "2" * 64
TRADE_DATE = "2026-09-19"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _build_structural_repo(
    root: Path,
    *,
    current_head: str = HEAD,
    pipeline_head: str | None = None,
    pipeline_branch: str = "main",
    pipeline_clean: bool = True,
    context_ready: bool = True,
    history_ready: bool = True,
    digest_ready: bool = True,
    m4_ready: bool = True,
    detail_errors: int = 0,
    run_success: bool = True,
) -> dict[str, Path | str]:
    reports = root / "artifacts" / "reports"
    reports.mkdir(parents=True, exist_ok=True)

    pipeline_path = reports / "m5-daily-close-pipeline.json"
    pipeline = {
        "schema_version": 2,
        "m5_product_ready": True,
        "m5_context_refresh_ready": context_ready,
        "m5_history_ready": history_ready,
        "m5_review_digest_ready": digest_ready,
        "m4_research_ready": m4_ready,
        "preflight": {
            "branch": pipeline_branch,
            "head": pipeline_head if pipeline_head is not None else current_head,
            "worktree_clean": pipeline_clean,
        },
    }
    _write_json(pipeline_path, pipeline)
    pipeline_hash = _sha(pipeline_path)

    delivery = reports / "htcn-daily-portable-delivery-v1.zip"
    v4 = reports / "m5-daily-portable-v4.zip"
    inspector = reports / "m5-daily-portable-inspector.json"
    workspace = reports / "m5-daily-portable-workspace.html"
    delivery.write_bytes(b"portable-delivery-phase21-fixture")
    v4.write_bytes(b"handoff-v4-phase21-fixture")
    inspector.write_text('{"schema_version":2}\n', encoding="utf-8")
    workspace.write_text(
        "<html><body>HT-CN v4 便携图形复盘 Visual Semantics v2 Source Raw PRZ 不是预测腿</body></html>",
        encoding="utf-8",
    )

    bundle_sha = _sha(delivery)
    archive_dir = (
        root
        / "artifacts"
        / "deliveries"
        / "m5"
        / TRADE_DATE
        / bundle_sha[:16]
    )
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_delivery = archive_dir / "htcn-daily-portable-delivery-v1.zip"
    archive_v4 = archive_dir / "htcn-daily-handoff-v4.zip"
    archive_inspector = archive_dir / "m5-handoff-v4-inspector.json"
    archive_workspace = archive_dir / "m5-handoff-v4-pattern-workspace.html"
    archive_delivery.write_bytes(delivery.read_bytes())
    archive_v4.write_bytes(v4.read_bytes())
    archive_inspector.write_bytes(inspector.read_bytes())
    archive_workspace.write_bytes(workspace.read_bytes())

    archive_manifest = {
        "schema_version": 1,
        "trade_date": TRADE_DATE,
        "bundle_sha256": bundle_sha,
        "input_identity_fingerprint": IDENTITY,
        "pipeline_report_sha256": pipeline_hash,
        "files": {
            "portable_delivery": {
                "path": str(archive_delivery.relative_to(root)),
                "sha256": _sha(archive_delivery),
            },
            "handoff_v4": {
                "path": str(archive_v4.relative_to(root)),
                "sha256": _sha(archive_v4),
            },
            "inspector_json": {
                "path": str(archive_inspector.relative_to(root)),
                "sha256": _sha(archive_inspector),
            },
            "workspace_html": {
                "path": str(archive_workspace.relative_to(root)),
                "sha256": _sha(archive_workspace),
            },
        },
    }
    _write_json(
        archive_dir / "m5-portable-delivery-archive.json",
        archive_manifest,
    )

    status = (
        "detail_degraded_portable_delivery"
        if detail_errors
        else "complete_portable_delivery"
    )
    pointer = {
        "schema_version": 1,
        "status": status,
        "trade_date": TRADE_DATE,
        "input_identity_fingerprint": IDENTITY,
        "pipeline_report_sha256": pipeline_hash,
        "bundle_sha256": bundle_sha,
        "archive_dir": str(archive_dir.relative_to(root)),
        "portable_delivery": str(delivery.relative_to(root)),
        "handoff_v4": str(v4.relative_to(root)),
        "inspector_json": str(inspector.relative_to(root)),
        "workspace_html": str(workspace.relative_to(root)),
        "detail_display_key_count": 3 - detail_errors,
        "error_display_key_count": detail_errors,
    }
    _write_json(
        reports / "m5-daily-portable-delivery-latest.json",
        pointer,
    )

    run_report = {
        "schema_version": 1,
        "status": status if run_success else "failed",
        "exit_code": 0 if run_success else 2,
        "pipeline_report_unchanged": True,
        "current_input_identity_fingerprint": IDENTITY,
        "bundle": {
            "bundle_sha256": bundle_sha if run_success else "9" * 64,
        },
    }
    _write_json(
        reports / "m5-daily-portable-delivery-run.json",
        run_report,
    )
    return {
        "pipeline": pipeline_path,
        "delivery": delivery,
        "v4": v4,
        "inspector": inspector,
        "workspace": workspace,
        "archive": archive_dir,
        "bundle_sha": bundle_sha,
        "pipeline_hash": pipeline_hash,
    }


def _patch_delivery_verifier(
    monkeypatch: pytest.MonkeyPatch,
    *,
    root: Path,
    bundle_sha: str,
) -> None:
    pipeline_hash = _sha(
        root / "artifacts" / "reports" / "m5-daily-close-pipeline.json"
    )
    monkeypatch.setattr(
        closeout,
        "verify_daily_portable_delivery_bundle",
        lambda path: SimpleNamespace(
            status="valid",
            errors=(),
            manifest={
                "trade_date": TRADE_DATE,
                "input_identity_fingerprint": IDENTITY,
                "pipeline_report_sha256": pipeline_hash,
                "bundle_sha256": bundle_sha,
            },
        ),
    )


def test_structural_closeout_ready_on_current_clean_main(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    built = _build_structural_repo(tmp_path)
    _patch_delivery_verifier(
        monkeypatch,
        root=tmp_path,
        bundle_sha=str(built["bundle_sha"]),
    )

    checked = closeout.verify_main_real_closeout(
        root=tmp_path,
        current_branch="main",
        current_head=HEAD,
        worktree_clean=True,
    )

    assert checked.status == "ready"
    assert checked.error_count == 0
    assert checked.warning_count == 0
    assert checked.trade_date == TRADE_DATE
    assert checked.bundle_sha256 == built["bundle_sha"]
    assert checked.checks["pipeline_head_matches_current"] is True
    assert checked.checks["portable_delivery_bundle_valid"] is True


@pytest.mark.parametrize(
    ("branch", "head", "pipeline_head", "expected_error"),
    [
        ("feature", HEAD, HEAD, "current_branch_not_main"),
        ("main", HEAD, "3" * 40, "pipeline_head_not_current_main_head"),
    ],
)
def test_structural_closeout_rejects_wrong_main_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    branch: str,
    head: str,
    pipeline_head: str,
    expected_error: str,
) -> None:
    built = _build_structural_repo(
        tmp_path,
        current_head=head,
        pipeline_head=pipeline_head,
    )
    _patch_delivery_verifier(
        monkeypatch,
        root=tmp_path,
        bundle_sha=str(built["bundle_sha"]),
    )

    checked = closeout.verify_main_real_closeout(
        root=tmp_path,
        current_branch=branch,
        current_head=head,
        worktree_clean=True,
    )

    assert checked.status == "invalid"
    assert expected_error in checked.errors


def test_structural_closeout_rejects_stale_pointer_pipeline_hash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    built = _build_structural_repo(tmp_path)
    pointer_path = (
        tmp_path
        / "artifacts"
        / "reports"
        / "m5-daily-portable-delivery-latest.json"
    )
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    pointer["pipeline_report_sha256"] = "4" * 64
    _write_json(pointer_path, pointer)
    _patch_delivery_verifier(
        monkeypatch,
        root=tmp_path,
        bundle_sha=str(built["bundle_sha"]),
    )

    checked = closeout.verify_main_real_closeout(
        root=tmp_path,
        current_branch="main",
        current_head=HEAD,
        worktree_clean=True,
    )

    assert checked.status == "invalid"
    assert "latest_pointer_pipeline_hash_mismatch" in checked.errors


def test_structural_closeout_rejects_latest_alias_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    built = _build_structural_repo(tmp_path)
    Path(built["workspace"]).write_text("tampered", encoding="utf-8")
    _patch_delivery_verifier(
        monkeypatch,
        root=tmp_path,
        bundle_sha=str(built["bundle_sha"]),
    )

    checked = closeout.verify_main_real_closeout(
        root=tmp_path,
        current_branch="main",
        current_head=HEAD,
        worktree_clean=True,
    )

    assert checked.status == "invalid"
    assert "latest_alias_hash_mismatch:workspace_html" in checked.errors


def test_structural_closeout_rejects_failed_latest_run_even_if_old_pointer_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    built = _build_structural_repo(tmp_path, run_success=False)
    _patch_delivery_verifier(
        monkeypatch,
        root=tmp_path,
        bundle_sha=str(built["bundle_sha"]),
    )

    checked = closeout.verify_main_real_closeout(
        root=tmp_path,
        current_branch="main",
        current_head=HEAD,
        worktree_clean=True,
    )

    assert checked.status == "invalid"
    assert "phase19_latest_run_not_successful" in checked.errors
    assert "run_bundle_sha_pointer_mismatch" in checked.errors


def test_explicit_product_degradation_is_warning_not_fake_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    built = _build_structural_repo(
        tmp_path,
        context_ready=False,
        history_ready=False,
        digest_ready=False,
        m4_ready=False,
        detail_errors=1,
    )
    _patch_delivery_verifier(
        monkeypatch,
        root=tmp_path,
        bundle_sha=str(built["bundle_sha"]),
    )

    checked = closeout.verify_main_real_closeout(
        root=tmp_path,
        current_branch="main",
        current_head=HEAD,
        worktree_clean=True,
    )

    assert checked.status == "ready_with_warnings"
    assert checked.error_count == 0
    assert "pipeline_context_refresh_degraded" in checked.warnings
    assert "pipeline_m4_research_degraded" in checked.warnings
    assert "portable_detail_degraded_explicit_errors_present" in checked.warnings


def _minimal_inspection() -> dict:
    return {
        "schema_version": 2,
        "contract": {
            "visual_semantics_version": 2,
        },
        "summary": {
            "status": "complete_detail_transport",
        },
        "portable_items": [
            {
                "display_key": "one",
                "detail_available": True,
            },
            {
                "display_key": "two",
                "detail_available": False,
            },
        ],
        "details_by_display_key": {
            "one": {
                "visual_semantics": {
                    "schema": "XABCD",
                },
            },
        },
    }


def test_prepare_browser_source_binds_real_workspace_and_counts(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace.html"
    inspection = tmp_path / "inspection.json"
    output = tmp_path / "public" / "latest.html"
    report = tmp_path / "reports" / "source.json"
    workspace.write_text("<html>workspace</html>", encoding="utf-8")
    _write_json(inspection, _minimal_inspection())

    payload = browser.prepare_main_real_browser_source(
        root=tmp_path,
        workspace_source=workspace,
        inspection_source=inspection,
        output_html=output,
        source_report=report,
        mode="phase19_latest",
        trade_date=TRADE_DATE,
        source_identity="5" * 64,
        structural_closeout_status="ready_with_warnings",
        structural_closeout_report_sha256="6" * 64,
    )

    assert payload["candidate_count"] == 2
    assert payload["detail_available_count"] == 1
    assert payload["detail_error_count"] == 1
    assert payload["schema_counts"] == {"XABCD": 1}
    assert output.read_bytes() == workspace.read_bytes()
    assert payload["browser_workspace_sha256"] == _sha(output)


def test_prepare_browser_source_rejects_real_mode_without_structural_ready(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace.html"
    inspection = tmp_path / "inspection.json"
    workspace.write_text("<html/>", encoding="utf-8")
    _write_json(inspection, _minimal_inspection())

    with pytest.raises(RuntimeError, match="structural_closeout_not_ready"):
        browser.prepare_main_real_browser_source(
            root=tmp_path,
            workspace_source=workspace,
            inspection_source=inspection,
            output_html=tmp_path / "out.html",
            source_report=tmp_path / "source.json",
            mode="phase19_latest",
            trade_date=TRADE_DATE,
            source_identity="5" * 64,
            structural_closeout_status="invalid",
        )


def _browser_source_and_evidence(tmp_path: Path) -> tuple[Path, Path]:
    screenshot = tmp_path / "artifacts" / "screenshots" / "real.png"
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    screenshot.write_bytes(b"P" * 12_500)
    source = tmp_path / "source.json"
    evidence = tmp_path / "evidence.json"
    _write_json(
        source,
        {
            "schema_version": 1,
            "mode": "phase19_latest",
            "trade_date": TRADE_DATE,
            "source_identity": "7" * 64,
            "candidate_count": 2,
            "detail_available_count": 1,
            "detail_error_count": 1,
            "schema_counts": {"XABCD": 1},
        },
    )
    _write_json(
        evidence,
        {
            "schema_version": 1,
            "phase": "M5 Phase 21",
            "browser": "chromium",
            "trade_date": TRADE_DATE,
            "source_identity": "7" * 64,
            "candidate_count": 2,
            "detail_available_count": 1,
            "detail_error_count": 1,
            "audited_detail_count": 1,
            "explicit_error_count": 1,
            "schema_counts": {"XABCD": 1},
            "future_point_violation_count": 0,
            "page_error_count": 0,
            "console_error_count": 0,
            "all_detail_geometry_matches_semantics": True,
            "all_explicit_errors_rendered": True,
            "layer_toggle_check_passed": True,
            "no_network_fetch_observed": True,
            "screenshots": [
                {
                    "file": str(screenshot.relative_to(tmp_path)),
                    "size_bytes": screenshot.stat().st_size,
                    "sha256": _sha(screenshot),
                }
            ],
            "writes_m4_evidence": False,
            "mutates_product_state": False,
            "mutates_harmonic_identity": False,
            "mutates_source_raw_prz": False,
            "mutates_source_lifecycle": False,
            "is_trade_instruction": False,
        },
    )
    return source, evidence


def test_browser_evidence_verifier_accepts_exhaustive_semantic_audit(
    tmp_path: Path,
) -> None:
    source, evidence = _browser_source_and_evidence(tmp_path)

    payload = browser.verify_main_real_browser_evidence(
        root=tmp_path,
        source_report=source,
        evidence_report=evidence,
    )

    assert payload["status"] == "valid"
    assert payload["error_count"] == 0
    assert payload["screenshot_count"] == 1


def test_browser_evidence_verifier_detects_screenshot_tamper(
    tmp_path: Path,
) -> None:
    source, evidence = _browser_source_and_evidence(tmp_path)
    screenshot = tmp_path / "artifacts" / "screenshots" / "real.png"
    screenshot.write_bytes(b"Q" * 12_500)

    payload = browser.verify_main_real_browser_evidence(
        root=tmp_path,
        source_report=source,
        evidence_report=evidence,
    )

    assert payload["status"] == "invalid"
    assert any(
        value.startswith("browser_evidence_screenshot_hash_mismatch:")
        for value in payload["errors"]
    )


def test_browser_evidence_verifier_detects_source_identity_mismatch(
    tmp_path: Path,
) -> None:
    source, evidence = _browser_source_and_evidence(tmp_path)
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    payload["source_identity"] = "8" * 64
    _write_json(evidence, payload)

    checked = browser.verify_main_real_browser_evidence(
        root=tmp_path,
        source_report=source,
        evidence_report=evidence,
    )

    assert checked["status"] == "invalid"
    assert (
        "browser_evidence_source_mismatch:source_identity"
        in checked["errors"]
    )


def test_finalize_closeout_requires_structural_and_browser_same_identity() -> None:
    structural = {
        "status": "ready_with_warnings",
        "trade_date": TRADE_DATE,
        "current_head": HEAD,
        "bundle_sha256": "7" * 64,
        "warnings": ["pipeline_m4_research_degraded"],
    }
    browser_ok = {
        "status": "valid",
        "trade_date": TRADE_DATE,
        "source_identity": "7" * 64,
        "screenshot_count": 2,
        "candidate_count": 2,
        "detail_available_count": 2,
        "detail_error_count": 0,
        "schema_counts": {"XABCD": 2},
    }

    ready = browser.finalize_main_real_closeout(
        structural_report=structural,
        browser_verification=browser_ok,
    )
    assert ready["full_closeout_ready"] is True
    assert ready["status"] == "ready_with_warnings"

    bad = browser.finalize_main_real_closeout(
        structural_report=structural,
        browser_verification={**browser_ok, "source_identity": "9" * 64},
    )
    assert bad["full_closeout_ready"] is False
    assert "closeout_bundle_identity_mismatch" in bad["errors"]
