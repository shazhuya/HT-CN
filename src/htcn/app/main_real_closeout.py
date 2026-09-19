from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from htcn.app.daily_portable_delivery import (
    verify_daily_portable_delivery_bundle,
)


MAIN_REAL_CLOSEOUT_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class MainRealCloseoutContract:
    version: int = 1
    semantics: str = "real_m1_latest_phase19_delivery_acceptance"
    expected_branch: str = "main"
    requires_clean_worktree: bool = True
    requires_current_head_pipeline_binding: bool = True
    latest_pointer_is_phase19_authority: bool = True
    requires_browser_for_full_closeout: bool = True
    browser_evidence_is_product_qa_not_m4_evidence: bool = True
    m4_research_degradation_blocks_product_closeout: bool = False
    context_degradation_blocks_product_closeout: bool = False
    detail_degradation_blocks_transport_closeout: bool = False
    authoritative_evidence: bool = False
    writes_m4_evidence: bool = False
    mutates_harmonic_identity: bool = False
    mutates_source_raw_prz: bool = False
    mutates_source_lifecycle: bool = False
    predictive_score_used: bool = False
    historical_outcome_used_for_ranking: bool = False
    alpha_inference_allowed: bool = False
    is_trade_instruction: bool = False

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MainRealCloseoutVerification:
    status: str
    trade_date: str | None
    current_head: str | None
    bundle_sha256: str | None
    error_count: int
    warning_count: int
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    checks: dict[str, bool]
    contract: dict[str, object]

    def as_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["errors"] = list(self.errors)
        payload["warnings"] = list(self.warnings)
        return payload


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{label}_unreadable:{type(exc).__name__}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{label}_not_object")
    return value


def _sha256_path(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_repo_path(repo: Path, raw: object, *, label: str) -> Path:
    value = str(raw or "").strip()
    if not value:
        raise RuntimeError(f"{label}_path_missing")
    path = Path(value)
    if not path.is_absolute():
        path = repo / path
    resolved = path.resolve()
    try:
        resolved.relative_to(repo)
    except ValueError as exc:
        raise RuntimeError(f"{label}_outside_repo") from exc
    return resolved


def _hash_matches(path: Path, expected: object) -> bool:
    value = str(expected or "")
    return path.is_file() and len(value) == 64 and _sha256_path(path) == value


def verify_main_real_closeout(
    *,
    root: str | Path,
    current_branch: str | None,
    current_head: str | None,
    worktree_clean: bool,
    pipeline_report: str | Path = "artifacts/reports/m5-daily-close-pipeline.json",
    run_report: str | Path = "artifacts/reports/m5-daily-portable-delivery-run.json",
    latest_pointer: str | Path = "artifacts/reports/m5-daily-portable-delivery-latest.json",
) -> MainRealCloseoutVerification:
    repo = Path(root).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, bool] = {}
    trade_date: str | None = None
    bundle_sha: str | None = None

    contract = MainRealCloseoutContract().as_payload()

    checks["branch_is_main"] = current_branch == "main"
    if not checks["branch_is_main"]:
        errors.append("current_branch_not_main")

    head = str(current_head or "").strip()
    checks["current_head_resolved"] = len(head) == 40
    if not checks["current_head_resolved"]:
        errors.append("current_head_invalid")

    checks["worktree_clean"] = bool(worktree_clean)
    if not checks["worktree_clean"]:
        errors.append("worktree_not_clean")

    pipeline_path = _resolve_repo_path(repo, pipeline_report, label="pipeline_report")
    run_path = _resolve_repo_path(repo, run_report, label="run_report")
    pointer_path = _resolve_repo_path(repo, latest_pointer, label="latest_pointer")

    pipeline: dict[str, Any] | None = None
    run: dict[str, Any] | None = None
    pointer: dict[str, Any] | None = None

    try:
        pipeline = _read_json_object(pipeline_path, label="pipeline_report")
    except RuntimeError as exc:
        errors.append(str(exc))
    try:
        run = _read_json_object(run_path, label="portable_run_report")
    except RuntimeError as exc:
        errors.append(str(exc))
    try:
        pointer = _read_json_object(pointer_path, label="latest_pointer")
    except RuntimeError as exc:
        errors.append(str(exc))

    pipeline_hash: str | None = None
    if pipeline is not None:
        pipeline_hash = _sha256_path(pipeline_path)
        checks["pipeline_product_ready"] = pipeline.get("m5_product_ready") is True
        if not checks["pipeline_product_ready"]:
            errors.append("pipeline_m5_product_not_ready")

        preflight = pipeline.get("preflight")
        if not isinstance(preflight, dict):
            errors.append("pipeline_preflight_missing")
            checks["pipeline_head_matches_current"] = False
            checks["pipeline_branch_is_main"] = False
            checks["pipeline_preflight_clean"] = False
        else:
            checks["pipeline_head_matches_current"] = (
                head != "" and str(preflight.get("head") or "") == head
            )
            checks["pipeline_branch_is_main"] = (
                str(preflight.get("branch") or "") == "main"
            )
            checks["pipeline_preflight_clean"] = (
                preflight.get("worktree_clean") is True
            )
            if not checks["pipeline_head_matches_current"]:
                errors.append("pipeline_head_not_current_main_head")
            if not checks["pipeline_branch_is_main"]:
                errors.append("pipeline_preflight_branch_not_main")
            if not checks["pipeline_preflight_clean"]:
                errors.append("pipeline_preflight_worktree_not_clean")

        if pipeline.get("m5_context_refresh_ready") is not True:
            warnings.append("pipeline_context_refresh_degraded")
        if pipeline.get("m5_history_ready") is not True:
            warnings.append("pipeline_operator_history_degraded")
        if pipeline.get("m5_review_digest_ready") is not True:
            warnings.append("pipeline_review_digest_degraded")
        if pipeline.get("m4_research_ready") is not True:
            warnings.append("pipeline_m4_research_degraded")

    if run is not None:
        checks["phase19_latest_run_success"] = (
            int(run.get("exit_code") or -1) == 0
            and str(run.get("status") or "") in (
                "complete_portable_delivery",
                "detail_degraded_portable_delivery",
            )
        )
        if not checks["phase19_latest_run_success"]:
            errors.append("phase19_latest_run_not_successful")
        checks["phase19_pipeline_unchanged"] = (
            run.get("pipeline_report_unchanged") is True
        )
        if not checks["phase19_pipeline_unchanged"]:
            errors.append("phase19_pipeline_report_not_stable")

    if pointer is not None:
        if int(pointer.get("schema_version") or 0) != 1:
            errors.append("latest_pointer_schema_invalid")
        trade_date = str(pointer.get("trade_date") or "") or None
        bundle_sha = str(pointer.get("bundle_sha256") or "") or None
        identity = str(pointer.get("input_identity_fingerprint") or "")
        if trade_date is None:
            errors.append("latest_pointer_trade_date_missing")
        if bundle_sha is None or len(bundle_sha) != 64:
            errors.append("latest_pointer_bundle_sha_invalid")
        if len(identity) != 64:
            errors.append("latest_pointer_input_identity_invalid")

        checks["pointer_pipeline_hash_matches_current"] = (
            pipeline_hash is not None
            and str(pointer.get("pipeline_report_sha256") or "") == pipeline_hash
        )
        if not checks["pointer_pipeline_hash_matches_current"]:
            errors.append("latest_pointer_pipeline_hash_mismatch")

        try:
            delivery_path = _resolve_repo_path(
                repo,
                pointer.get("portable_delivery"),
                label="portable_delivery",
            )
            v4_alias = _resolve_repo_path(
                repo,
                pointer.get("handoff_v4"),
                label="handoff_v4_alias",
            )
            inspector_alias = _resolve_repo_path(
                repo,
                pointer.get("inspector_json"),
                label="inspector_alias",
            )
            workspace_alias = _resolve_repo_path(
                repo,
                pointer.get("workspace_html"),
                label="workspace_alias",
            )
            archive_dir = _resolve_repo_path(
                repo,
                pointer.get("archive_dir"),
                label="archive_dir",
            )
        except RuntimeError as exc:
            errors.append(str(exc))
        else:
            checks["portable_delivery_alias_hash_matches_pointer"] = (
                bundle_sha is not None
                and _hash_matches(delivery_path, bundle_sha)
            )
            if not checks["portable_delivery_alias_hash_matches_pointer"]:
                errors.append("portable_delivery_alias_hash_mismatch")

            checked = verify_daily_portable_delivery_bundle(delivery_path)
            checks["portable_delivery_bundle_valid"] = checked.status == "valid"
            if not checks["portable_delivery_bundle_valid"]:
                errors.append(
                    "portable_delivery_bundle_invalid:"
                    + ",".join(checked.errors)
                )
            else:
                manifest = checked.manifest or {}
                checks["bundle_trade_date_matches_pointer"] = (
                    str(manifest.get("trade_date") or "") == (trade_date or "")
                )
                checks["bundle_identity_matches_pointer"] = (
                    str(manifest.get("input_identity_fingerprint") or "")
                    == identity
                )
                checks["bundle_pipeline_hash_matches_pointer"] = (
                    str(manifest.get("pipeline_report_sha256") or "")
                    == str(pointer.get("pipeline_report_sha256") or "")
                )
                for key, ok, error in (
                    (
                        "bundle_trade_date_matches_pointer",
                        checks["bundle_trade_date_matches_pointer"],
                        "bundle_trade_date_pointer_mismatch",
                    ),
                    (
                        "bundle_identity_matches_pointer",
                        checks["bundle_identity_matches_pointer"],
                        "bundle_identity_pointer_mismatch",
                    ),
                    (
                        "bundle_pipeline_hash_matches_pointer",
                        checks["bundle_pipeline_hash_matches_pointer"],
                        "bundle_pipeline_hash_pointer_mismatch",
                    ),
                ):
                    if not ok:
                        errors.append(error)

            archive_manifest_path = (
                archive_dir / "m5-portable-delivery-archive.json"
            )
            if not archive_manifest_path.is_file():
                errors.append("archive_manifest_missing")
            else:
                try:
                    archive = _read_json_object(
                        archive_manifest_path,
                        label="archive_manifest",
                    )
                except RuntimeError as exc:
                    errors.append(str(exc))
                else:
                    checks["archive_bundle_sha_matches_pointer"] = (
                        str(archive.get("bundle_sha256") or "")
                        == (bundle_sha or "")
                    )
                    checks["archive_trade_date_matches_pointer"] = (
                        str(archive.get("trade_date") or "")
                        == (trade_date or "")
                    )
                    checks["archive_identity_matches_pointer"] = (
                        str(archive.get("input_identity_fingerprint") or "")
                        == identity
                    )
                    checks["archive_pipeline_hash_matches_pointer"] = (
                        str(archive.get("pipeline_report_sha256") or "")
                        == str(pointer.get("pipeline_report_sha256") or "")
                    )
                    for key, error in (
                        (
                            "archive_bundle_sha_matches_pointer",
                            "archive_bundle_sha_mismatch",
                        ),
                        (
                            "archive_trade_date_matches_pointer",
                            "archive_trade_date_mismatch",
                        ),
                        (
                            "archive_identity_matches_pointer",
                            "archive_identity_mismatch",
                        ),
                        (
                            "archive_pipeline_hash_matches_pointer",
                            "archive_pipeline_hash_mismatch",
                        ),
                    ):
                        if not checks[key]:
                            errors.append(error)

                    files = archive.get("files")
                    if not isinstance(files, dict):
                        errors.append("archive_files_missing")
                    else:
                        alias_map = {
                            "portable_delivery": delivery_path,
                            "handoff_v4": v4_alias,
                            "inspector_json": inspector_alias,
                            "workspace_html": workspace_alias,
                        }
                        for role, alias in alias_map.items():
                            record = files.get(role)
                            if not isinstance(record, dict):
                                errors.append(f"archive_role_missing:{role}")
                                continue
                            try:
                                archive_file = _resolve_repo_path(
                                    repo,
                                    record.get("path"),
                                    label=f"archive_{role}",
                                )
                            except RuntimeError as exc:
                                errors.append(str(exc))
                                continue
                            expected_sha = str(record.get("sha256") or "")
                            if not _hash_matches(archive_file, expected_sha):
                                errors.append(
                                    f"archive_file_hash_mismatch:{role}"
                                )
                            if not _hash_matches(alias, expected_sha):
                                errors.append(
                                    f"latest_alias_hash_mismatch:{role}"
                                )

        if int(pointer.get("error_display_key_count") or 0) > 0:
            warnings.append("portable_detail_degraded_explicit_errors_present")
        if str(pointer.get("status") or "") == "detail_degraded_portable_delivery":
            warnings.append("portable_delivery_detail_degraded")

    if run is not None and pointer is not None:
        run_bundle = run.get("bundle")
        run_bundle = run_bundle if isinstance(run_bundle, dict) else {}
        checks["run_bundle_sha_matches_pointer"] = (
            str(run_bundle.get("bundle_sha256") or "")
            == str(pointer.get("bundle_sha256") or "")
        )
        if not checks["run_bundle_sha_matches_pointer"]:
            errors.append("run_bundle_sha_pointer_mismatch")
        checks["run_identity_matches_pointer"] = (
            str(run.get("current_input_identity_fingerprint") or "")
            == str(pointer.get("input_identity_fingerprint") or "")
        )
        if not checks["run_identity_matches_pointer"]:
            errors.append("run_identity_pointer_mismatch")

    unique_warnings = tuple(dict.fromkeys(warnings))
    unique_errors = tuple(dict.fromkeys(errors))
    status = (
        "invalid"
        if unique_errors
        else "ready_with_warnings"
        if unique_warnings
        else "ready"
    )
    return MainRealCloseoutVerification(
        status=status,
        trade_date=trade_date,
        current_head=head or None,
        bundle_sha256=bundle_sha,
        error_count=len(unique_errors),
        warning_count=len(unique_warnings),
        errors=unique_errors,
        warnings=unique_warnings,
        checks=checks,
        contract=contract,
    )


def write_main_real_closeout_report(
    *,
    output: str | Path,
    verification: MainRealCloseoutVerification,
) -> None:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(
        json.dumps(
            verification.as_payload(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)
