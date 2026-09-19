from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any
import zipfile


PRIVATE_M1_CLOSEOUT_SCHEMA_VERSION = 1
PRIVATE_M1_EVIDENCE_BUNDLE_SCHEMA_VERSION = 1

DEFAULT_PATHS = {
    "project_state": "governance/PROJECT_STATE.json",
    "preflight": "artifacts/reports/m5-real-closeout-preflight.json",
    "pipeline": "artifacts/reports/m5-daily-close-pipeline.json",
    "phase19_run": "artifacts/reports/m5-daily-portable-delivery-run.json",
    "phase19_pointer": "artifacts/reports/m5-daily-portable-delivery-latest.json",
    "phase21_structural": "artifacts/reports/m5-main-real-closeout.json",
    "browser_source": (
        "artifacts/reports/playwright/"
        "phase21-real-delivery-browser-source.json"
    ),
    "browser_evidence": (
        "artifacts/reports/playwright/"
        "phase21-real-delivery-browser-evidence.json"
    ),
    "browser_verification": (
        "artifacts/reports/playwright/"
        "phase21-real-delivery-browser-verification.json"
    ),
    "phase21_final": "artifacts/reports/m5-main-real-closeout-final.json",
}


@dataclass(frozen=True, slots=True)
class PrivateM1CloseoutContract:
    version: int = 1
    semantics: str = "m6_real_private_m1_identity_bound_closeout"
    required_branch: str = "main"
    required_project_phase: str = "M6.2"
    required_active_change: str = "CR-0066"
    requires_clean_worktree: bool = True
    requires_end_remote_main_exact_match: bool = True
    requires_phase23_preflight_ready: bool = True
    requires_phase21_full_closeout_ready: bool = True
    requires_identity_convergence: bool = True
    produces_single_portable_evidence_zip: bool = True
    evidence_is_m4_authoritative: bool = False
    writes_m4_evidence: bool = False
    mutates_m1_market_data: bool = False
    mutates_product_state: bool = False
    mutates_harmonic_identity: bool = False
    mutates_source_raw_prz: bool = False
    mutates_source_lifecycle: bool = False
    predictive_score_used: bool = False
    alpha_inference_allowed: bool = False
    is_trade_instruction: bool = False

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PrivateM1CloseoutVerification:
    status: str
    full_closeout_ready: bool
    trade_date: str | None
    main_head: str | None
    remote_main_head: str | None
    delivery_bundle_sha256: str | None
    input_identity_fingerprint: str | None
    pipeline_report_sha256: str | None
    error_count: int
    warning_count: int
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    checks: dict[str, bool]
    evidence_files: dict[str, str]
    contract: dict[str, object]

    def as_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["errors"] = list(self.errors)
        payload["warnings"] = list(self.warnings)
        return payload


def _sha256_bytes(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{label}_unreadable:{type(exc).__name__}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{label}_not_object")
    return value


def _resolve_repo_path(repo: Path, raw: str | Path, *, label: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = repo / path
    resolved = path.resolve()
    try:
        resolved.relative_to(repo)
    except ValueError as exc:
        raise RuntimeError(f"{label}_outside_repo") from exc
    return resolved


def _resolve_browser_artifact(repo: Path, raw: object) -> Path:
    value = str(raw or "").strip()
    if not value:
        raise RuntimeError("browser_artifact_path_missing")
    path = Path(value)
    if path.is_absolute():
        candidates = [path.resolve()]
    else:
        candidates = [
            (repo / "apps" / "web" / path).resolve(),
            (repo / path).resolve(),
        ]
    for candidate in candidates:
        try:
            candidate.relative_to(repo)
        except ValueError:
            continue
        if candidate.is_file():
            return candidate
    valid = []
    for candidate in candidates:
        try:
            candidate.relative_to(repo)
        except ValueError:
            continue
        valid.append(candidate)
    if not valid:
        raise RuntimeError("browser_artifact_outside_repo")
    return valid[0]


def _is_sha(value: object) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{40}", str(value or "")))


def _is_hash64(value: object) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", str(value or "")))


def verify_private_m1_closeout(
    *,
    root: str | Path,
    current_branch: str | None,
    current_head: str | None,
    worktree_clean: bool,
    remote_main_head: str | None,
    paths: dict[str, str | Path] | None = None,
) -> PrivateM1CloseoutVerification:
    repo = Path(root).resolve()
    configured = dict(DEFAULT_PATHS)
    configured.update(paths or {})

    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, bool] = {}
    evidence_files: dict[str, str] = {}
    payloads: dict[str, dict[str, Any]] = {}

    def check(name: str, passed: bool, error: str) -> None:
        checks[name] = bool(passed)
        if not passed:
            errors.append(error)

    def required_json(role: str) -> dict[str, Any] | None:
        try:
            path = _resolve_repo_path(repo, configured[role], label=role)
        except RuntimeError as exc:
            errors.append(str(exc))
            checks[f"{role}_present"] = False
            return None
        if not path.is_file():
            errors.append(f"{role}_missing")
            checks[f"{role}_present"] = False
            return None
        try:
            payload = _read_json_object(path, label=role)
        except RuntimeError as exc:
            errors.append(str(exc))
            checks[f"{role}_present"] = False
            return None
        checks[f"{role}_present"] = True
        payloads[role] = payload
        evidence_files[role] = str(path.relative_to(repo))
        return payload

    check("branch_main", current_branch == "main", "branch_not_main")
    check("head_valid", _is_sha(current_head), "current_head_invalid")
    check("worktree_clean", worktree_clean is True, "worktree_not_clean")
    check(
        "remote_main_head_valid",
        _is_sha(remote_main_head),
        "remote_main_head_invalid",
    )
    check(
        "remote_main_end_matches_head",
        _is_sha(current_head)
        and _is_sha(remote_main_head)
        and current_head == remote_main_head,
        "remote_main_moved_during_closeout",
    )

    state = required_json("project_state")
    preflight = required_json("preflight")
    pipeline = required_json("pipeline")
    run = required_json("phase19_run")
    pointer = required_json("phase19_pointer")
    structural = required_json("phase21_structural")
    source = required_json("browser_source")
    raw_browser = required_json("browser_evidence")
    browser = required_json("browser_verification")
    final = required_json("phase21_final")

    if state is not None:
        current = state.get("current")
        current = current if isinstance(current, dict) else {}
        check(
            "project_phase_m6_2",
            current.get("phase") == "M6.2",
            "project_state_phase_not_m6_2",
        )
        check(
            "project_change_cr_0066",
            current.get("active_change") == "CR-0066",
            "project_state_active_change_not_cr_0066",
        )
        allowed = {
            "implementing",
            "validation_green",
            "ready_to_merge",
            "merged",
            "postmerge_pending",
            "awaiting_private_run",
            "real_run_in_progress",
        }
        check(
            "project_status_allows_private_run",
            current.get("status") in allowed,
            "project_state_status_disallows_private_run",
        )

    if preflight is not None:
        check(
            "preflight_ready",
            preflight.get("status") in {"ready", "ready_with_warnings"},
            "preflight_not_ready",
        )
        check(
            "preflight_head_matches",
            str(preflight.get("head") or "") == str(current_head or ""),
            "preflight_head_mismatch",
        )
        warnings.extend(str(x) for x in (preflight.get("warnings") or []))

    if run is not None:
        check(
            "phase19_run_complete",
            int(run.get("exit_code") or 0) == 0
            and run.get("status")
            in {
                "complete_portable_delivery",
                "detail_degraded_portable_delivery",
            },
            "phase19_run_not_complete",
        )
        check(
            "phase19_pipeline_unchanged",
            run.get("pipeline_report_unchanged") is True,
            "phase19_pipeline_report_changed",
        )

    if structural is not None:
        check(
            "structural_ready",
            structural.get("status") in {"ready", "ready_with_warnings"},
            "phase21_structural_not_ready",
        )
        check(
            "structural_head_matches",
            str(structural.get("current_head") or "")
            == str(current_head or ""),
            "phase21_structural_head_mismatch",
        )
        warnings.extend(str(x) for x in (structural.get("warnings") or []))

    if source is not None:
        check(
            "browser_source_real_mode",
            source.get("mode") == "phase19_latest",
            "browser_source_not_real_phase19",
        )

    if browser is not None:
        check(
            "browser_verification_valid",
            browser.get("status") == "valid",
            "browser_verification_invalid",
        )

    if final is not None:
        check(
            "phase21_full_closeout_ready",
            final.get("full_closeout_ready") is True
            and final.get("status") in {"ready", "ready_with_warnings"},
            "phase21_final_not_ready",
        )
        check(
            "phase21_final_head_matches",
            str(final.get("main_head") or "") == str(current_head or ""),
            "phase21_final_head_mismatch",
        )
        warnings.extend(str(x) for x in (final.get("warnings") or []))

    trade_date: str | None = None
    delivery_bundle_sha: str | None = None
    input_identity: str | None = None
    pipeline_sha: str | None = None

    if pointer is not None:
        trade_date = str(pointer.get("trade_date") or "") or None
        delivery_bundle_sha = str(pointer.get("bundle_sha256") or "") or None
        input_identity = (
            str(pointer.get("input_identity_fingerprint") or "") or None
        )
        pipeline_sha = str(pointer.get("pipeline_report_sha256") or "") or None
        check("pointer_trade_date", bool(trade_date), "pointer_trade_date_missing")
        check(
            "pointer_bundle_hash",
            _is_hash64(delivery_bundle_sha),
            "pointer_bundle_sha_invalid",
        )
        check(
            "pointer_input_identity",
            _is_hash64(input_identity),
            "pointer_input_identity_invalid",
        )
        check(
            "pointer_pipeline_hash",
            _is_hash64(pipeline_sha),
            "pointer_pipeline_sha_invalid",
        )

    trade_values: dict[str, str] = {}
    bundle_values: dict[str, str] = {}
    for role, field in (
        ("phase19_pointer", "trade_date"),
        ("phase21_structural", "trade_date"),
        ("browser_source", "trade_date"),
        ("browser_verification", "trade_date"),
        ("phase21_final", "trade_date"),
    ):
        payload = payloads.get(role)
        if payload is not None:
            value = str(payload.get(field) or "")
            trade_values[role] = value
    if trade_values:
        check(
            "trade_date_converged",
            len(set(trade_values.values())) == 1 and bool(next(iter(trade_values.values()))),
            "trade_date_identity_mismatch",
        )

    for role, field in (
        ("phase19_pointer", "bundle_sha256"),
        ("phase21_structural", "bundle_sha256"),
        ("browser_source", "source_identity"),
        ("browser_verification", "source_identity"),
        ("phase21_final", "bundle_sha256"),
    ):
        payload = payloads.get(role)
        if payload is not None:
            bundle_values[role] = str(payload.get(field) or "")
    if bundle_values:
        check(
            "delivery_bundle_identity_converged",
            len(set(bundle_values.values())) == 1
            and _is_hash64(next(iter(bundle_values.values()))),
            "delivery_bundle_identity_mismatch",
        )

    if pipeline is not None and pipeline_sha is not None:
        pipeline_path = _resolve_repo_path(
            repo, configured["pipeline"], label="pipeline"
        )
        check(
            "pipeline_report_hash_matches",
            _sha256_path(pipeline_path) == pipeline_sha,
            "pipeline_report_hash_mismatch",
        )

    archive_manifest: dict[str, Any] | None = None
    if pointer is not None:
        raw_archive_dir = str(pointer.get("archive_dir") or "")
        if not raw_archive_dir:
            errors.append("phase19_archive_dir_missing")
            checks["archive_manifest_present"] = False
        else:
            try:
                archive_dir = _resolve_repo_path(
                    repo, raw_archive_dir, label="phase19_archive_dir"
                )
                manifest_path = archive_dir / "m5-portable-delivery-archive.json"
                if not manifest_path.is_file():
                    raise RuntimeError("archive_manifest_missing")
                archive_manifest = _read_json_object(
                    manifest_path, label="archive_manifest"
                )
                evidence_files["archive_manifest"] = str(
                    manifest_path.relative_to(repo)
                )
                checks["archive_manifest_present"] = True
            except RuntimeError as exc:
                errors.append(str(exc))
                checks["archive_manifest_present"] = False

    if archive_manifest is not None:
        check(
            "archive_trade_date_matches",
            str(archive_manifest.get("trade_date") or "") == str(trade_date or ""),
            "archive_trade_date_mismatch",
        )
        check(
            "archive_bundle_matches",
            str(archive_manifest.get("bundle_sha256") or "")
            == str(delivery_bundle_sha or ""),
            "archive_bundle_identity_mismatch",
        )
        check(
            "archive_input_identity_matches",
            str(archive_manifest.get("input_identity_fingerprint") or "")
            == str(input_identity or ""),
            "archive_input_identity_mismatch",
        )
        check(
            "archive_pipeline_hash_matches",
            str(archive_manifest.get("pipeline_report_sha256") or "")
            == str(pipeline_sha or ""),
            "archive_pipeline_hash_mismatch",
        )
        files = archive_manifest.get("files")
        files = files if isinstance(files, dict) else {}
        required_archive_roles = {
            "portable_delivery",
            "handoff_v4",
            "inspector_json",
            "workspace_html",
        }
        check(
            "archive_roles_complete",
            required_archive_roles <= set(files),
            "archive_roles_incomplete",
        )
        for role in sorted(required_archive_roles):
            record = files.get(role)
            if not isinstance(record, dict):
                errors.append(f"archive_role_invalid:{role}")
                checks[f"archive_{role}_hash"] = False
                continue
            try:
                path = _resolve_repo_path(
                    repo, str(record.get("path") or ""), label=f"archive_{role}"
                )
            except RuntimeError as exc:
                errors.append(str(exc))
                checks[f"archive_{role}_hash"] = False
                continue
            if not path.is_file():
                errors.append(f"archive_member_missing:{role}")
                checks[f"archive_{role}_hash"] = False
                continue
            actual = _sha256_path(path)
            expected = str(record.get("sha256") or "")
            ok = actual == expected and _is_hash64(expected)
            check(
                f"archive_{role}_hash",
                ok,
                f"archive_member_hash_mismatch:{role}",
            )
            evidence_files[role] = str(path.relative_to(repo))
            if role == "portable_delivery" and delivery_bundle_sha is not None:
                check(
                    "portable_delivery_hash_is_bundle_identity",
                    actual == delivery_bundle_sha,
                    "portable_delivery_bundle_hash_mismatch",
                )

    if source is not None and structural is not None:
        structural_path = _resolve_repo_path(
            repo, configured["phase21_structural"], label="phase21_structural"
        )
        check(
            "browser_source_structural_hash_matches",
            str(source.get("structural_closeout_report_sha256") or "")
            == _sha256_path(structural_path),
            "browser_source_structural_hash_mismatch",
        )

    if source is not None and pointer is not None:
        try:
            workspace = _resolve_repo_path(
                repo, str(pointer.get("workspace_html") or ""), label="workspace"
            )
            inspection = _resolve_repo_path(
                repo, str(pointer.get("inspector_json") or ""), label="inspector"
            )
            workspace_ok = (
                workspace.is_file()
                and _sha256_path(workspace)
                == str(source.get("workspace_source_sha256") or "")
            )
            inspection_ok = (
                inspection.is_file()
                and _sha256_path(inspection)
                == str(source.get("inspection_source_sha256") or "")
            )
            check(
                "browser_workspace_source_hash_matches",
                workspace_ok,
                "browser_workspace_source_hash_mismatch",
            )
            check(
                "browser_inspection_source_hash_matches",
                inspection_ok,
                "browser_inspection_source_hash_mismatch",
            )
        except RuntimeError as exc:
            errors.append(str(exc))

    if raw_browser is not None:
        screenshots = raw_browser.get("screenshots")
        if not isinstance(screenshots, list) or not screenshots:
            errors.append("browser_screenshots_missing")
            checks["browser_screenshot_hashes"] = False
        else:
            screenshot_ok = True
            for index, record in enumerate(screenshots):
                if not isinstance(record, dict):
                    screenshot_ok = False
                    errors.append(f"browser_screenshot_record_invalid:{index}")
                    continue
                try:
                    path = _resolve_browser_artifact(repo, record.get("file"))
                except RuntimeError as exc:
                    screenshot_ok = False
                    errors.append(str(exc))
                    continue
                if not path.is_file():
                    screenshot_ok = False
                    errors.append(f"browser_screenshot_missing:{index}")
                    continue
                actual = _sha256_path(path)
                expected = str(record.get("sha256") or "")
                if actual != expected or not _is_hash64(expected):
                    screenshot_ok = False
                    errors.append(f"browser_screenshot_hash_mismatch:{index}")
                    continue
                evidence_files[f"screenshot_{index:03d}"] = str(
                    path.relative_to(repo)
                )
            checks["browser_screenshot_hashes"] = screenshot_ok

    # Deduplicate carried warnings while preserving stable order.
    warnings = list(dict.fromkeys(value for value in warnings if value))
    status = (
        "invalid"
        if errors
        else "ready_with_warnings"
        if warnings
        else "ready"
    )
    return PrivateM1CloseoutVerification(
        status=status,
        full_closeout_ready=not errors,
        trade_date=trade_date,
        main_head=current_head,
        remote_main_head=remote_main_head,
        delivery_bundle_sha256=delivery_bundle_sha,
        input_identity_fingerprint=input_identity,
        pipeline_report_sha256=pipeline_sha,
        error_count=len(errors),
        warning_count=len(warnings),
        errors=tuple(errors),
        warnings=tuple(warnings),
        checks=checks,
        evidence_files=dict(sorted(evidence_files.items())),
        contract=PrivateM1CloseoutContract().as_payload(),
    )


def build_private_m1_evidence_bundle(
    *,
    root: str | Path,
    verification_report: str | Path,
    output: str | Path,
) -> dict[str, Any]:
    repo = Path(root).resolve()
    report_path = _resolve_repo_path(
        repo, verification_report, label="m6_verification_report"
    )
    output_path = _resolve_repo_path(repo, output, label="m6_evidence_bundle")
    report = _read_json_object(report_path, label="m6_verification_report")
    if report.get("full_closeout_ready") is not True:
        raise RuntimeError("m6_verification_not_ready")

    evidence_files = report.get("evidence_files")
    if not isinstance(evidence_files, dict):
        raise RuntimeError("m6_evidence_files_invalid")

    members: list[tuple[str, str, Path]] = [
        ("m6_verification", "reports/m6-private-m1-closeout.json", report_path)
    ]
    for role, raw_path in sorted(evidence_files.items()):
        source = _resolve_repo_path(repo, str(raw_path), label=f"evidence_{role}")
        if not source.is_file():
            raise RuntimeError(f"evidence_file_missing:{role}")
        safe_role = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(role))
        arcname = f"evidence/{safe_role}/{source.name}"
        members.append((str(role), arcname, source))

    arcnames = [arcname for _, arcname, _ in members]
    if len(arcnames) != len(set(arcnames)):
        raise RuntimeError("evidence_arcname_collision")

    records = [
        {
            "role": role,
            "arcname": arcname,
            "source_path": str(source.relative_to(repo)),
            "size_bytes": source.stat().st_size,
            "sha256": _sha256_path(source),
        }
        for role, arcname, source in members
    ]
    manifest = {
        "schema_version": PRIVATE_M1_EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "status": report.get("status"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "trade_date": report.get("trade_date"),
        "main_head": report.get("main_head"),
        "remote_main_head": report.get("remote_main_head"),
        "delivery_bundle_sha256": report.get("delivery_bundle_sha256"),
        "input_identity_fingerprint": report.get(
            "input_identity_fingerprint"
        ),
        "pipeline_report_sha256": report.get("pipeline_report_sha256"),
        "warning_count": report.get("warning_count"),
        "file_count": len(records),
        "files": records,
        "contract": PrivateM1CloseoutContract().as_payload(),
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "is_trade_instruction": False,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_name(f".{output_path.name}.tmp")
    tmp.unlink(missing_ok=True)
    with zipfile.ZipFile(
        tmp,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        archive.writestr(
            "m6-private-m1-closeout-manifest.json",
            _canonical_json_bytes(manifest),
        )
        for _, arcname, source in members:
            archive.write(source, arcname)

    checked = verify_private_m1_evidence_bundle(tmp)
    if checked["status"] != "valid":
        tmp.unlink(missing_ok=True)
        raise RuntimeError(
            "m6_bundle_verification_failed:" + ",".join(checked["errors"])
        )
    tmp.replace(output_path)
    final = verify_private_m1_evidence_bundle(output_path)
    if final["status"] != "valid":
        raise RuntimeError(
            "m6_bundle_post_replace_verification_failed:"
            + ",".join(final["errors"])
        )
    return {
        **manifest,
        "output": str(output_path),
        "bundle_size_bytes": output_path.stat().st_size,
        "bundle_sha256": _sha256_path(output_path),
        "verification": final,
    }


def verify_private_m1_evidence_bundle(
    bundle: str | Path,
) -> dict[str, Any]:
    path = Path(bundle)
    errors: list[str] = []
    manifest: dict[str, Any] = {}
    required_roles = {
        "m6_verification",
        "project_state",
        "preflight",
        "pipeline",
        "phase19_run",
        "phase19_pointer",
        "phase21_structural",
        "browser_source",
        "browser_evidence",
        "browser_verification",
        "phase21_final",
        "archive_manifest",
        "portable_delivery",
        "handoff_v4",
        "inspector_json",
        "workspace_html",
    }
    raw_by_role: dict[str, bytes] = {}
    record_by_role: dict[str, dict[str, Any]] = {}

    def json_role(role: str) -> dict[str, Any] | None:
        raw = raw_by_role.get(role)
        if raw is None:
            return None
        try:
            value = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            errors.append(f"bundle_json_unreadable:{role}:{type(exc).__name__}")
            return None
        if not isinstance(value, dict):
            errors.append(f"bundle_json_not_object:{role}")
            return None
        return value

    try:
        with zipfile.ZipFile(path, "r") as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                errors.append("bundle_duplicate_members")
            manifest_name = "m6-private-m1-closeout-manifest.json"
            if names.count(manifest_name) != 1:
                errors.append("bundle_manifest_missing_or_duplicate")
            else:
                try:
                    raw = archive.read(manifest_name)
                    loaded = json.loads(raw.decode("utf-8"))
                    if isinstance(loaded, dict):
                        manifest = loaded
                    else:
                        errors.append("bundle_manifest_not_object")
                except Exception as exc:
                    errors.append(
                        f"bundle_manifest_unreadable:{type(exc).__name__}"
                    )

            if manifest:
                if int(manifest.get("schema_version") or 0) != (
                    PRIVATE_M1_EVIDENCE_BUNDLE_SCHEMA_VERSION
                ):
                    errors.append("bundle_schema_invalid")
                if manifest.get("status") not in {"ready", "ready_with_warnings"}:
                    errors.append("bundle_status_invalid")
                if str(manifest.get("main_head") or "") != str(
                    manifest.get("remote_main_head") or ""
                ):
                    errors.append("bundle_main_identity_mismatch")
                if not _is_sha(manifest.get("main_head")):
                    errors.append("bundle_main_head_invalid")
                if not _is_hash64(manifest.get("delivery_bundle_sha256")):
                    errors.append("bundle_delivery_identity_invalid")
                if not _is_hash64(manifest.get("input_identity_fingerprint")):
                    errors.append("bundle_input_identity_invalid")
                if not _is_hash64(manifest.get("pipeline_report_sha256")):
                    errors.append("bundle_pipeline_identity_invalid")

                records = manifest.get("files")
                if not isinstance(records, list):
                    errors.append("bundle_files_invalid")
                    records = []
                if int(manifest.get("file_count") or -1) != len(records):
                    errors.append("bundle_file_count_mismatch")

                roles: list[str] = []
                for record in records:
                    if not isinstance(record, dict):
                        errors.append("bundle_file_record_invalid")
                        continue
                    role = str(record.get("role") or "")
                    arcname = str(record.get("arcname") or "")
                    roles.append(role)
                    if role:
                        record_by_role[role] = record
                    if arcname not in names:
                        errors.append(f"bundle_member_missing:{role}")
                        continue
                    raw = archive.read(arcname)
                    raw_by_role[role] = raw
                    if int(record.get("size_bytes") or -1) != len(raw):
                        errors.append(f"bundle_member_size_mismatch:{role}")
                    if str(record.get("sha256") or "") != _sha256_bytes(raw):
                        errors.append(f"bundle_member_hash_mismatch:{role}")
                if len(roles) != len(set(roles)):
                    errors.append("bundle_duplicate_roles")
                missing = sorted(required_roles - set(roles))
                if missing:
                    errors.append(
                        "bundle_required_roles_missing:" + ",".join(missing)
                    )
                if not any(role.startswith("screenshot_") for role in roles):
                    errors.append("bundle_screenshot_evidence_missing")

                portable_record = record_by_role.get("portable_delivery") or {}
                if str(portable_record.get("sha256") or "") != str(
                    manifest.get("delivery_bundle_sha256") or ""
                ):
                    errors.append("bundle_portable_delivery_identity_mismatch")
                pipeline_record = record_by_role.get("pipeline") or {}
                if str(pipeline_record.get("sha256") or "") != str(
                    manifest.get("pipeline_report_sha256") or ""
                ):
                    errors.append("bundle_pipeline_report_identity_mismatch")

                m6 = json_role("m6_verification")
                project_state = json_role("project_state")
                preflight = json_role("preflight")
                phase19_run = json_role("phase19_run")
                pointer = json_role("phase19_pointer")
                structural = json_role("phase21_structural")
                browser_source = json_role("browser_source")
                archive_manifest = json_role("archive_manifest")
                browser_verification = json_role("browser_verification")
                final = json_role("phase21_final")

                if project_state is not None:
                    current = project_state.get("current")
                    current = current if isinstance(current, dict) else {}
                    if current.get("phase") != "M6.2":
                        errors.append("bundle_project_state_phase_invalid")
                    if current.get("active_change") != "CR-0066":
                        errors.append("bundle_project_state_change_invalid")

                if preflight is not None:
                    if preflight.get("status") not in {"ready", "ready_with_warnings"}:
                        errors.append("bundle_preflight_not_ready")
                    if str(preflight.get("head") or "") != str(
                        manifest.get("main_head") or ""
                    ):
                        errors.append("bundle_preflight_main_head_mismatch")

                if phase19_run is not None:
                    if phase19_run.get("status") not in {
                        "complete_portable_delivery",
                        "detail_degraded_portable_delivery",
                    }:
                        errors.append("bundle_phase19_run_not_complete")
                    if phase19_run.get("exit_code") != 0:
                        errors.append("bundle_phase19_run_exit_nonzero")
                    if phase19_run.get("pipeline_report_unchanged") is not True:
                        errors.append("bundle_phase19_pipeline_changed")

                if structural is not None:
                    if structural.get("status") not in {"ready", "ready_with_warnings"}:
                        errors.append("bundle_structural_not_ready")
                    if str(structural.get("trade_date") or "") != str(
                        manifest.get("trade_date") or ""
                    ):
                        errors.append("bundle_structural_trade_date_mismatch")
                    if str(structural.get("current_head") or "") != str(
                        manifest.get("main_head") or ""
                    ):
                        errors.append("bundle_structural_main_head_mismatch")
                    if str(structural.get("bundle_sha256") or "") != str(
                        manifest.get("delivery_bundle_sha256") or ""
                    ):
                        errors.append("bundle_structural_delivery_identity_mismatch")

                if browser_source is not None:
                    if browser_source.get("mode") != "phase19_latest":
                        errors.append("bundle_browser_source_mode_invalid")
                    if str(browser_source.get("trade_date") or "") != str(
                        manifest.get("trade_date") or ""
                    ):
                        errors.append("bundle_browser_source_trade_date_mismatch")
                    if str(browser_source.get("source_identity") or "") != str(
                        manifest.get("delivery_bundle_sha256") or ""
                    ):
                        errors.append("bundle_browser_source_identity_mismatch")

                if m6 is not None:
                    if m6.get("full_closeout_ready") is not True:
                        errors.append("bundle_m6_verification_not_ready")
                    for field in (
                        "status",
                        "trade_date",
                        "main_head",
                        "remote_main_head",
                        "delivery_bundle_sha256",
                        "input_identity_fingerprint",
                        "pipeline_report_sha256",
                    ):
                        if str(m6.get(field) or "") != str(
                            manifest.get(field) or ""
                        ):
                            errors.append(f"bundle_m6_manifest_mismatch:{field}")

                if pointer is not None:
                    for pointer_field, manifest_field in (
                        ("trade_date", "trade_date"),
                        ("bundle_sha256", "delivery_bundle_sha256"),
                        (
                            "input_identity_fingerprint",
                            "input_identity_fingerprint",
                        ),
                        ("pipeline_report_sha256", "pipeline_report_sha256"),
                    ):
                        if str(pointer.get(pointer_field) or "") != str(
                            manifest.get(manifest_field) or ""
                        ):
                            errors.append(
                                "bundle_pointer_manifest_mismatch:"
                                + pointer_field
                            )

                if archive_manifest is not None:
                    for archive_field, manifest_field in (
                        ("trade_date", "trade_date"),
                        ("bundle_sha256", "delivery_bundle_sha256"),
                        (
                            "input_identity_fingerprint",
                            "input_identity_fingerprint",
                        ),
                        ("pipeline_report_sha256", "pipeline_report_sha256"),
                    ):
                        if str(archive_manifest.get(archive_field) or "") != str(
                            manifest.get(manifest_field) or ""
                        ):
                            errors.append(
                                "bundle_archive_manifest_mismatch:"
                                + archive_field
                            )

                if browser_verification is not None:
                    if browser_verification.get("status") != "valid":
                        errors.append("bundle_browser_verification_invalid")
                    if str(browser_verification.get("trade_date") or "") != str(
                        manifest.get("trade_date") or ""
                    ):
                        errors.append("bundle_browser_trade_date_mismatch")
                    if str(
                        browser_verification.get("source_identity") or ""
                    ) != str(manifest.get("delivery_bundle_sha256") or ""):
                        errors.append("bundle_browser_identity_mismatch")

                if final is not None:
                    if final.get("full_closeout_ready") is not True:
                        errors.append("bundle_phase21_final_not_ready")
                    if str(final.get("trade_date") or "") != str(
                        manifest.get("trade_date") or ""
                    ):
                        errors.append("bundle_final_trade_date_mismatch")
                    if str(final.get("main_head") or "") != str(
                        manifest.get("main_head") or ""
                    ):
                        errors.append("bundle_final_main_head_mismatch")
                    if str(final.get("bundle_sha256") or "") != str(
                        manifest.get("delivery_bundle_sha256") or ""
                    ):
                        errors.append("bundle_final_delivery_identity_mismatch")
    except (OSError, zipfile.BadZipFile):
        errors.append("bundle_not_readable_zip")

    return {
        "schema_version": 1,
        "status": "valid" if not errors else "invalid",
        "error_count": len(errors),
        "errors": errors,
        "bundle_path": str(path),
        "bundle_sha256": _sha256_path(path) if path.is_file() else None,
        "manifest": manifest,
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "is_trade_instruction": False,
    }