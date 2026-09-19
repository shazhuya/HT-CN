from __future__ import annotations

import json
import warnings
import zipfile
from hashlib import sha256
from pathlib import Path

from htcn.app.private_m1_closeout import (
    PrivateM1CloseoutContract,
    build_private_m1_evidence_bundle,
    verify_private_m1_closeout,
    verify_private_m1_evidence_bundle,
)

HEAD = "a" * 40
TRADE_DATE = "2026-09-19"
IDENTITY = "b" * 64


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _build_ready_fixture(root: Path, *, warnings: list[str] | None = None) -> dict:
    reports = root / "artifacts" / "reports"
    playwright = reports / "playwright"
    screenshots = root / "artifacts" / "screenshots"
    archive = (
        root
        / "artifacts"
        / "deliveries"
        / "m5"
        / TRADE_DATE
        / "fixture-identity"
    )
    for path in (reports, playwright, screenshots, archive):
        path.mkdir(parents=True, exist_ok=True)

    _write_json(
        root / "governance" / "PROJECT_STATE.json",
        {
            "schema": 2,
            "current": {
                "phase": "M6.2",
                "status": "implementing",
                "active_change": "CR-0066",
            },
        },
    )
    _write_json(
        reports / "m5-real-closeout-preflight.json",
        {
            "schema_version": 1,
            "status": "ready_with_warnings" if warnings else "ready",
            "head": HEAD,
            "warnings": list(warnings or []),
            "next_action": "daily_close_and_phase19_may_start",
        },
    )

    pipeline = reports / "m5-daily-close-pipeline.json"
    _write_json(pipeline, {"schema_version": 1, "m5_product_ready": True})
    pipeline_sha = _sha(pipeline)

    portable = archive / "htcn-daily-portable-delivery-v1.zip"
    v4 = archive / "htcn-daily-handoff-v4.zip"
    inspector_archive = archive / "m5-handoff-v4-inspector.json"
    workspace_archive = archive / "m5-handoff-v4-pattern-workspace.html"
    portable.write_bytes(b"PORTABLE" * 300)
    v4.write_bytes(b"V4" * 500)
    inspector_archive.write_text('{"fixture":true}\n', encoding="utf-8")
    workspace_archive.write_text("<html>fixture</html>\n", encoding="utf-8")
    bundle_sha = _sha(portable)

    inspector_alias = reports / "m5-daily-portable-inspector.json"
    workspace_alias = reports / "m5-daily-portable-workspace.html"
    inspector_alias.write_bytes(inspector_archive.read_bytes())
    workspace_alias.write_bytes(workspace_archive.read_bytes())

    archive_manifest = {
        "schema_version": 1,
        "trade_date": TRADE_DATE,
        "bundle_sha256": bundle_sha,
        "input_identity_fingerprint": IDENTITY,
        "pipeline_report_sha256": pipeline_sha,
        "files": {
            "portable_delivery": {
                "path": str(portable.relative_to(root)),
                "sha256": _sha(portable),
            },
            "handoff_v4": {
                "path": str(v4.relative_to(root)),
                "sha256": _sha(v4),
            },
            "inspector_json": {
                "path": str(inspector_archive.relative_to(root)),
                "sha256": _sha(inspector_archive),
            },
            "workspace_html": {
                "path": str(workspace_archive.relative_to(root)),
                "sha256": _sha(workspace_archive),
            },
        },
    }
    _write_json(archive / "m5-portable-delivery-archive.json", archive_manifest)

    _write_json(
        reports / "m5-daily-portable-delivery-run.json",
        {
            "schema_version": 1,
            "status": "complete_portable_delivery",
            "exit_code": 0,
            "pipeline_report_unchanged": True,
        },
    )
    _write_json(
        reports / "m5-daily-portable-delivery-latest.json",
        {
            "schema_version": 1,
            "status": "complete_portable_delivery",
            "trade_date": TRADE_DATE,
            "input_identity_fingerprint": IDENTITY,
            "pipeline_report_sha256": pipeline_sha,
            "bundle_sha256": bundle_sha,
            "archive_dir": str(archive.relative_to(root)),
            "portable_delivery": str(portable.relative_to(root)),
            "inspector_json": str(inspector_alias.relative_to(root)),
            "workspace_html": str(workspace_alias.relative_to(root)),
        },
    )

    structural = reports / "m5-main-real-closeout.json"
    _write_json(
        structural,
        {
            "schema_version": 1,
            "status": "ready_with_warnings" if warnings else "ready",
            "trade_date": TRADE_DATE,
            "current_head": HEAD,
            "bundle_sha256": bundle_sha,
            "warnings": list(warnings or []),
        },
    )

    _write_json(
        playwright / "phase21-real-delivery-browser-source.json",
        {
            "schema_version": 1,
            "mode": "phase19_latest",
            "trade_date": TRADE_DATE,
            "source_identity": bundle_sha,
            "workspace_source_sha256": _sha(workspace_alias),
            "inspection_source_sha256": _sha(inspector_alias),
            "structural_closeout_report_sha256": _sha(structural),
        },
    )

    screenshot = screenshots / "m6-overview.png"
    screenshot.write_bytes(b"SCREENSHOT" * 1500)
    _write_json(
        playwright / "phase21-real-delivery-browser-evidence.json",
        {
            "schema_version": 1,
            "phase": "M5 Phase 21",
            "browser": "chromium",
            "trade_date": TRADE_DATE,
            "source_identity": bundle_sha,
            "screenshots": [
                {
                    "file": "../../artifacts/screenshots/m6-overview.png",
                    "size_bytes": screenshot.stat().st_size,
                    "sha256": _sha(screenshot),
                }
            ],
        },
    )
    _write_json(
        playwright / "phase21-real-delivery-browser-verification.json",
        {
            "schema_version": 1,
            "status": "valid",
            "trade_date": TRADE_DATE,
            "source_identity": bundle_sha,
            "screenshot_count": 1,
        },
    )
    _write_json(
        reports / "m5-main-real-closeout-final.json",
        {
            "schema_version": 1,
            "status": "ready_with_warnings" if warnings else "ready",
            "full_closeout_ready": True,
            "trade_date": TRADE_DATE,
            "main_head": HEAD,
            "bundle_sha256": bundle_sha,
            "warnings": list(warnings or []),
        },
    )
    return {
        "bundle_sha": bundle_sha,
        "pipeline_sha": pipeline_sha,
        "archive": archive,
        "screenshot": screenshot,
    }


def _verify(root: Path, *, remote: str = HEAD):
    return verify_private_m1_closeout(
        root=root,
        current_branch="main",
        current_head=HEAD,
        worktree_clean=True,
        remote_main_head=remote,
    )


def test_ready_fixture_converges_every_identity(tmp_path: Path) -> None:
    fixture = _build_ready_fixture(tmp_path)
    checked = _verify(tmp_path)

    assert checked.status == "ready"
    assert checked.full_closeout_ready is True
    assert checked.trade_date == TRADE_DATE
    assert checked.main_head == HEAD
    assert checked.remote_main_head == HEAD
    assert checked.delivery_bundle_sha256 == fixture["bundle_sha"]
    assert checked.pipeline_report_sha256 == fixture["pipeline_sha"]
    assert checked.input_identity_fingerprint == IDENTITY
    assert checked.error_count == 0
    assert checked.checks["remote_main_end_matches_head"] is True
    assert checked.checks["delivery_bundle_identity_converged"] is True
    assert checked.checks["browser_screenshot_hashes"] is True


def test_remote_main_move_at_end_fails_closed(tmp_path: Path) -> None:
    _build_ready_fixture(tmp_path)
    checked = _verify(tmp_path, remote="c" * 40)

    assert checked.status == "invalid"
    assert checked.full_closeout_ready is False
    assert "remote_main_moved_during_closeout" in checked.errors


def test_wrong_project_phase_or_change_fails_closed(tmp_path: Path) -> None:
    _build_ready_fixture(tmp_path)
    state = tmp_path / "governance" / "PROJECT_STATE.json"
    payload = json.loads(state.read_text(encoding="utf-8"))
    payload["current"]["phase"] = "M6.3"
    payload["current"]["active_change"] = "CR-9999"
    _write_json(state, payload)

    checked = _verify(tmp_path)
    assert "project_state_phase_not_m6_2" in checked.errors
    assert "project_state_active_change_not_cr_0066" in checked.errors


def test_trade_date_mismatch_fails_closed(tmp_path: Path) -> None:
    _build_ready_fixture(tmp_path)
    path = (
        tmp_path
        / "artifacts"
        / "reports"
        / "playwright"
        / "phase21-real-delivery-browser-verification.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["trade_date"] = "2026-09-18"
    _write_json(path, payload)

    checked = _verify(tmp_path)
    assert "trade_date_identity_mismatch" in checked.errors


def test_archive_member_tamper_fails_closed(tmp_path: Path) -> None:
    fixture = _build_ready_fixture(tmp_path)
    target = fixture["archive"] / "m5-handoff-v4-inspector.json"
    target.write_text('{"tampered":true}\n', encoding="utf-8")

    checked = _verify(tmp_path)
    assert "archive_member_hash_mismatch:inspector_json" in checked.errors


def test_browser_screenshot_tamper_fails_closed(tmp_path: Path) -> None:
    fixture = _build_ready_fixture(tmp_path)
    fixture["screenshot"].write_bytes(b"TAMPER" * 3000)

    checked = _verify(tmp_path)
    assert "browser_screenshot_hash_mismatch:0" in checked.errors


def test_warning_propagates_without_becoming_blocker(tmp_path: Path) -> None:
    _build_ready_fixture(tmp_path, warnings=["m1_full_listed_coverage:55/5000"])
    checked = _verify(tmp_path)

    assert checked.status == "ready_with_warnings"
    assert checked.full_closeout_ready is True
    assert checked.warning_count == 1
    assert checked.error_count == 0


def test_evidence_bundle_is_self_verifying_and_tamper_evident(
    tmp_path: Path,
) -> None:
    _build_ready_fixture(tmp_path)
    checked = _verify(tmp_path)
    report = tmp_path / "artifacts" / "reports" / "m6-private-m1-closeout.json"
    _write_json(report, checked.as_payload())
    bundle = (
        tmp_path
        / "artifacts"
        / "reports"
        / "htcn-m6-private-m1-closeout-evidence.zip"
    )

    built = build_private_m1_evidence_bundle(
        root=tmp_path,
        verification_report=report,
        output=bundle,
    )
    assert built["verification"]["status"] == "valid"
    assert verify_private_m1_evidence_bundle(bundle)["status"] == "valid"

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(bundle, "a") as archive:
            archive.writestr(
                "evidence/project_state/PROJECT_STATE.json",
                b"tampered",
            )
    tampered = verify_private_m1_evidence_bundle(bundle)
    assert tampered["status"] == "invalid"
    assert "bundle_duplicate_members" in tampered["errors"]


def test_contract_keeps_research_and_trade_boundaries_frozen() -> None:
    contract = PrivateM1CloseoutContract().as_payload()
    assert contract["evidence_is_m4_authoritative"] is False
    assert contract["writes_m4_evidence"] is False
    assert contract["mutates_m1_market_data"] is False
    assert contract["mutates_product_state"] is False
    assert contract["mutates_harmonic_identity"] is False
    assert contract["mutates_source_raw_prz"] is False
    assert contract["mutates_source_lifecycle"] is False
    assert contract["predictive_score_used"] is False
    assert contract["alpha_inference_allowed"] is False
    assert contract["is_trade_instruction"] is False


def test_m6_bat_is_one_action_and_never_auto_repairs() -> None:
    root = Path(__file__).resolve().parents[2]
    bat = (
        root / "运行HT-CN M6.2真实Private-M1最终收口.bat"
    ).read_text(encoding="utf-8")
    lower = bat.lower()

    project_os = 'scripts\\project_state.py'
    frozen_m5 = '运行HT-CN主线真实A股最终验收.bat'
    m6 = 'scripts\\m6_private_m1_closeout.py'
    assert project_os in bat
    assert frozen_m5 in bat
    assert m6 in bat
    assert bat.index(project_os) < bat.index(frozen_m5) < bat.index(m6)
    assert "Upload ONLY this file" in bat

    for forbidden in (
        "git pull",
        "git fetch",
        "pip install",
        "npm install",
        "npm ci",
        "playwright install",
    ):
        assert forbidden not in lower

def test_bundle_semantics_reject_rehashed_pointer_identity_tamper(
    tmp_path: Path,
) -> None:
    _build_ready_fixture(tmp_path)
    checked = _verify(tmp_path)
    report = tmp_path / "artifacts" / "reports" / "m6-private-m1-closeout.json"
    _write_json(report, checked.as_payload())
    bundle = tmp_path / "artifacts" / "reports" / "evidence.zip"
    build_private_m1_evidence_bundle(
        root=tmp_path,
        verification_report=report,
        output=bundle,
    )

    rewritten = tmp_path / "artifacts" / "reports" / "rewritten.zip"
    with zipfile.ZipFile(bundle, "r") as source:
        contents = {name: source.read(name) for name in source.namelist()}
    manifest_name = "m6-private-m1-closeout-manifest.json"
    manifest = json.loads(contents[manifest_name].decode("utf-8"))
    pointer_record = next(
        item for item in manifest["files"] if item["role"] == "phase19_pointer"
    )
    pointer = json.loads(contents[pointer_record["arcname"]].decode("utf-8"))
    pointer["trade_date"] = "2026-09-18"
    raw = (
        json.dumps(pointer, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    contents[pointer_record["arcname"]] = raw
    pointer_record["size_bytes"] = len(raw)
    pointer_record["sha256"] = sha256(raw).hexdigest()
    contents[manifest_name] = (
        json.dumps(
            manifest,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")

    with zipfile.ZipFile(rewritten, "w", compression=zipfile.ZIP_DEFLATED) as out:
        for name, raw_member in contents.items():
            out.writestr(name, raw_member)

    verified = verify_private_m1_evidence_bundle(rewritten)
    assert verified["status"] == "invalid"
    assert "bundle_pointer_manifest_mismatch:trade_date" in verified["errors"]


def test_bundle_rejects_unlisted_and_unsafe_archive_members(tmp_path: Path) -> None:
    _build_ready_fixture(tmp_path)
    checked = _verify(tmp_path)
    report = tmp_path / "artifacts" / "reports" / "m6-private-m1-closeout.json"
    _write_json(report, checked.as_payload())
    bundle = tmp_path / "artifacts" / "reports" / "evidence.zip"
    build_private_m1_evidence_bundle(
        root=tmp_path,
        verification_report=report,
        output=bundle,
    )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(bundle, "a") as archive:
            archive.writestr("../unexpected.txt", b"not-listed")

    verified = verify_private_m1_evidence_bundle(bundle)
    assert verified["status"] == "invalid"
    assert any(
        error.startswith("bundle_unsafe_members:")
        for error in verified["errors"]
    )
    assert any(
        error.startswith("bundle_unlisted_members:")
        for error in verified["errors"]
    )


def test_bundle_rejects_rehashed_browser_evidence_semantic_tamper(
    tmp_path: Path,
) -> None:
    _build_ready_fixture(tmp_path)
    checked = _verify(tmp_path)
    report = tmp_path / "artifacts" / "reports" / "m6-private-m1-closeout.json"
    _write_json(report, checked.as_payload())
    bundle = tmp_path / "artifacts" / "reports" / "evidence.zip"
    build_private_m1_evidence_bundle(
        root=tmp_path,
        verification_report=report,
        output=bundle,
    )

    rewritten = tmp_path / "artifacts" / "reports" / "browser-rewritten.zip"
    with zipfile.ZipFile(bundle, "r") as source:
        contents = {name: source.read(name) for name in source.namelist()}

    manifest_name = "m6-private-m1-closeout-manifest.json"
    manifest = json.loads(contents[manifest_name].decode("utf-8"))
    record = next(
        item
        for item in manifest["files"]
        if item["role"] == "browser_evidence"
    )
    evidence = json.loads(contents[record["arcname"]].decode("utf-8"))
    evidence["source_identity"] = "c" * 64
    raw = (
        json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    contents[record["arcname"]] = raw
    record["size_bytes"] = len(raw)
    record["sha256"] = sha256(raw).hexdigest()
    contents[manifest_name] = (
        json.dumps(
            manifest,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")

    with zipfile.ZipFile(rewritten, "w", compression=zipfile.ZIP_DEFLATED) as out:
        for name, raw_member in contents.items():
            out.writestr(name, raw_member)

    verified = verify_private_m1_evidence_bundle(rewritten)
    assert verified["status"] == "invalid"
    assert "bundle_browser_evidence_identity_mismatch" in verified["errors"]


def test_bundle_rejects_rehashed_workspace_without_browser_source_update(
    tmp_path: Path,
) -> None:
    _build_ready_fixture(tmp_path)
    checked = _verify(tmp_path)
    report = tmp_path / "artifacts" / "reports" / "m6-private-m1-closeout.json"
    _write_json(report, checked.as_payload())
    bundle = tmp_path / "artifacts" / "reports" / "evidence.zip"
    build_private_m1_evidence_bundle(
        root=tmp_path,
        verification_report=report,
        output=bundle,
    )

    rewritten = tmp_path / "artifacts" / "reports" / "workspace-rewritten.zip"
    with zipfile.ZipFile(bundle, "r") as source:
        contents = {name: source.read(name) for name in source.namelist()}

    manifest_name = "m6-private-m1-closeout-manifest.json"
    manifest = json.loads(contents[manifest_name].decode("utf-8"))
    record = next(
        item
        for item in manifest["files"]
        if item["role"] == "workspace_html"
    )
    raw = b"<html>semantically-tampered-workspace</html>\n"
    contents[record["arcname"]] = raw
    record["size_bytes"] = len(raw)
    record["sha256"] = sha256(raw).hexdigest()

    archive_record = next(
        item
        for item in manifest["files"]
        if item["role"] == "archive_manifest"
    )
    archive_manifest = json.loads(
        contents[archive_record["arcname"]].decode("utf-8")
    )
    archive_manifest["files"]["workspace_html"]["sha256"] = sha256(raw).hexdigest()
    archive_raw = (
        json.dumps(
            archive_manifest,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")
    contents[archive_record["arcname"]] = archive_raw
    archive_record["size_bytes"] = len(archive_raw)
    archive_record["sha256"] = sha256(archive_raw).hexdigest()

    contents[manifest_name] = (
        json.dumps(
            manifest,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")

    with zipfile.ZipFile(rewritten, "w", compression=zipfile.ZIP_DEFLATED) as out:
        for name, raw_member in contents.items():
            out.writestr(name, raw_member)

    verified = verify_private_m1_evidence_bundle(rewritten)
    assert verified["status"] == "invalid"
    assert "bundle_browser_workspace_hash_mismatch" in verified["errors"]

