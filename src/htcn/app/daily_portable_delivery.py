from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any, Protocol

from htcn.app.daily_handoff_v3_runner import run_daily_handoff_bundle_v3
from htcn.app.handoff_v4_inspector import write_portable_pattern_workspace
from htcn.app.handoff_v4_portable_detail import (
    build_daily_handoff_bundle_v4,
    verify_daily_handoff_bundle_v4,
)
from htcn.app.operator_input_identity import (
    build_analysis_code_identity,
    build_operator_cache_input_identity,
)
from htcn.app.source_clock_lifecycle_service import (
    M3SourceClockHarmonicService,
)

PORTABLE_DELIVERY_SCHEMA_VERSION = 1
PORTABLE_DELIVERY_RUN_REPORT_SCHEMA_VERSION = 1


class AnalysisProvider(Protocol):
    def analyze(
        self,
        instrument_id: str,
        *,
        bars: int,
        scales: tuple[int, ...],
    ) -> dict[str, Any]: ...


RunV3 = Callable[..., tuple[dict[str, Any], int]]
BuildV4 = Callable[..., dict[str, Any]]
WriteWorkspace = Callable[..., dict[str, Any]]
IdentityFactory = Callable[[Path], str]
ProviderFactory = Callable[[Path], AnalysisProvider]


@dataclass(frozen=True, slots=True)
class PortableDeliveryContract:
    version: int = 1
    semantics: str = "verified_v4_plus_offline_workspace"
    nested_v4_unmodified: bool = True
    latest_pointer_is_authoritative_for_phase19: bool = True
    frozen_phase14_16_aliases_overwritten: bool = False
    authoritative_evidence: bool = False
    writes_m4_evidence: bool = False
    imports_product_state: bool = False
    writes_operator_queue: bool = False
    writes_operator_history: bool = False
    writes_review_journal: bool = False
    creates_review_events: bool = False
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
class PortableDeliveryVerification:
    status: str
    bundle_path: str
    schema_version: int | None
    file_count: int
    trade_date: str | None
    nested_v4_status: str | None
    detail_display_key_count: int
    error_display_key_count: int
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    manifest: dict[str, Any] | None

    def as_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["errors"] = list(self.errors)
        payload["warnings"] = list(self.warnings)
        return payload


def _canonical_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _read_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"json_not_object:{path}")
    return value


def _read_json_bytes(data: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{label}_unreadable:{type(exc).__name__}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{label}_not_object")
    return value


def _sha256_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_arcname(name: str) -> bool:
    if not name or "\\" in name:
        return False
    path = PurePosixPath(name)
    if path.is_absolute():
        return False
    return all(part not in ("", ".", "..") for part in path.parts)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_bytes(_canonical_json_bytes(payload))
    tmp.replace(path)


def _copy_atomic(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.tmp")
    tmp.unlink(missing_ok=True)
    shutil.copyfile(source, tmp)
    tmp.replace(target)


def _default_identity_factory(repo: Path) -> str:
    analysis_identity = build_analysis_code_identity(project_root=repo)
    identity = build_operator_cache_input_identity(
        data_root=repo / "data" / "market",
        project_root=repo,
        analysis_code_identity=analysis_identity,
    )
    return identity.fingerprint


def _default_provider_factory(repo: Path) -> AnalysisProvider:
    return M3SourceClockHarmonicService(repo / "data" / "market")


def _validate_inspection_payload(
    inspection: dict[str, Any],
    *,
    trade_date: str,
    input_identity_fingerprint: str,
) -> list[str]:
    errors: list[str] = []
    if int(inspection.get("schema_version") or 0) != 2:
        errors.append("inspection_schema_invalid")
    contract = inspection.get("contract")
    if not isinstance(contract, dict):
        errors.append("inspection_contract_missing")
    else:
        if int(contract.get("source_bundle_schema") or 0) != 4:
            errors.append("inspection_source_bundle_schema_invalid")
        if int(contract.get("visual_semantics_version") or 0) != 2:
            errors.append("inspection_visual_semantics_version_invalid")
        for field in (
            "requires_market_database",
            "imports_product_state",
            "writes_review_journal",
            "creates_review_events",
            "writes_m4_evidence",
            "predictive_score_used",
            "historical_outcome_used_for_ranking",
            "alpha_inference_allowed",
            "is_trade_instruction",
        ):
            if contract.get(field) is not False:
                errors.append(f"inspection_boundary_invalid:{field}")

    source = inspection.get("source")
    if not isinstance(source, dict) or source.get("verification_status") != "valid":
        errors.append("inspection_source_verification_invalid")

    summary = inspection.get("summary")
    if not isinstance(summary, dict):
        errors.append("inspection_summary_missing")
    else:
        if str(summary.get("trade_date") or "") != trade_date:
            errors.append("inspection_trade_date_mismatch")

    transport = inspection.get("transport_manifest")
    if not isinstance(transport, dict):
        errors.append("inspection_transport_manifest_missing")
    else:
        if str(transport.get("trade_date") or "") != trade_date:
            errors.append("inspection_transport_trade_date_mismatch")
        if str(transport.get("input_identity_fingerprint") or "") != (
            input_identity_fingerprint
        ):
            errors.append("inspection_input_identity_mismatch")

    for field in (
        "authoritative_evidence",
        "writes_m4_evidence",
        "imports_product_state",
        "creates_review_events",
        "is_trade_instruction",
        "alpha_inference_allowed",
        "predictive_score_used",
        "historical_outcome_used_for_ranking",
    ):
        if inspection.get(field) is not False:
            errors.append(f"inspection_top_level_boundary_invalid:{field}")
    return errors


def _validate_workspace_html(data: bytes) -> list[str]:
    errors: list[str] = []
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return ["workspace_html_not_utf8"]
    required = (
        "HT-CN v4 便携图形复盘",
        "Visual Semantics v2",
        "Source Raw PRZ",
        "不是预测腿",
    )
    for marker in required:
        if marker not in text:
            errors.append(f"workspace_marker_missing:{marker}")
    if "fetch(" in text:
        errors.append("workspace_network_fetch_forbidden")
    if "review-session/event" in text:
        errors.append("workspace_review_write_surface_forbidden")
    return errors


def _nested_v4_verification_from_bytes(data: bytes):
    with tempfile.TemporaryDirectory(prefix="htcn-portable-delivery-v4-") as temp:
        path = Path(temp) / "htcn-daily-handoff-v4.zip"
        path.write_bytes(data)
        return verify_daily_handoff_bundle_v4(path)


def verify_daily_portable_delivery_bundle(
    path: str | Path,
) -> PortableDeliveryVerification:
    bundle_path = Path(path)
    errors: list[str] = []
    warnings: list[str] = []
    manifest: dict[str, Any] | None = None
    schema_version: int | None = None
    file_count = 0
    trade_date: str | None = None
    nested_v4_status: str | None = None
    detail_count = 0
    error_count = 0

    if not bundle_path.is_file():
        return PortableDeliveryVerification(
            status="invalid",
            bundle_path=str(bundle_path),
            schema_version=None,
            file_count=0,
            trade_date=None,
            nested_v4_status=None,
            detail_display_key_count=0,
            error_display_key_count=0,
            errors=("bundle_missing",),
            warnings=(),
            manifest=None,
        )

    try:
        with zipfile.ZipFile(bundle_path, "r") as archive:
            names = [info.filename for info in archive.infolist()]
            if len(names) != len(set(names)):
                errors.append("duplicate_archive_member")
            if any(not _safe_arcname(name) for name in names):
                errors.append("unsafe_archive_member")

            manifest_name = "daily-portable-delivery-manifest.json"
            if manifest_name not in names:
                errors.append("manifest_missing")
            else:
                try:
                    manifest = _read_json_bytes(
                        archive.read(manifest_name),
                        label="portable_delivery_manifest",
                    )
                except RuntimeError as exc:
                    errors.append(str(exc))

            if manifest is not None:
                try:
                    schema_version = int(manifest.get("schema_version"))
                except (TypeError, ValueError):
                    errors.append("manifest_schema_invalid")
                else:
                    if schema_version != PORTABLE_DELIVERY_SCHEMA_VERSION:
                        errors.append("manifest_schema_unsupported")

                trade_date = str(manifest.get("trade_date") or "") or None
                identity = str(
                    manifest.get("input_identity_fingerprint") or ""
                )
                if len(identity) != 64:
                    errors.append("manifest_input_identity_invalid")
                pipeline_hash = str(manifest.get("pipeline_report_sha256") or "")
                if len(pipeline_hash) != 64:
                    errors.append("manifest_pipeline_hash_invalid")

                contract = manifest.get("contract")
                if not isinstance(contract, dict):
                    errors.append("contract_missing")
                else:
                    if contract.get("nested_v4_unmodified") is not True:
                        errors.append("contract_nested_v4_boundary_invalid")
                    if (
                        contract.get(
                            "latest_pointer_is_authoritative_for_phase19"
                        )
                        is not True
                    ):
                        errors.append("contract_pointer_boundary_invalid")
                    if contract.get("frozen_phase14_16_aliases_overwritten") is not False:
                        errors.append("contract_frozen_alias_boundary_invalid")
                    for field in (
                        "authoritative_evidence",
                        "writes_m4_evidence",
                        "imports_product_state",
                        "writes_operator_queue",
                        "writes_operator_history",
                        "writes_review_journal",
                        "creates_review_events",
                        "mutates_harmonic_identity",
                        "mutates_source_raw_prz",
                        "mutates_source_lifecycle",
                        "predictive_score_used",
                        "historical_outcome_used_for_ranking",
                        "alpha_inference_allowed",
                        "is_trade_instruction",
                    ):
                        if contract.get(field) is not False:
                            errors.append(f"contract_boundary_invalid:{field}")

                records = manifest.get("files")
                if not isinstance(records, list):
                    errors.append("manifest_files_invalid")
                    records = []
                file_count = len(records)
                by_arcname: dict[str, dict[str, Any]] = {}
                roles: dict[str, list[str]] = {}
                for record in records:
                    if not isinstance(record, dict):
                        errors.append("manifest_file_record_invalid")
                        continue
                    arcname = str(record.get("arcname") or "")
                    role = str(record.get("role") or "")
                    if not _safe_arcname(arcname):
                        errors.append("manifest_arcname_invalid")
                        continue
                    if arcname in by_arcname:
                        errors.append("duplicate_manifest_arcname")
                    by_arcname[arcname] = record
                    roles.setdefault(role, []).append(arcname)

                actual = set(names) - {manifest_name}
                if set(by_arcname) != actual:
                    errors.append("manifest_member_set_mismatch")
                for arcname, record in by_arcname.items():
                    if arcname not in actual:
                        continue
                    raw = archive.read(arcname)
                    if int(record.get("size_bytes") or -1) != len(raw):
                        errors.append(f"member_size_mismatch:{arcname}")
                    if str(record.get("sha256") or "") != _sha256_bytes(raw):
                        errors.append(f"member_hash_mismatch:{arcname}")

                v4_members = roles.get("m5_handoff_v4_base", [])
                inspection_members = roles.get(
                    "m5_portable_inspector_json",
                    [],
                )
                workspace_members = roles.get(
                    "m5_portable_workspace_html",
                    [],
                )
                if len(v4_members) != 1:
                    errors.append("nested_v4_role_invalid")
                if len(inspection_members) != 1:
                    errors.append("inspection_role_invalid")
                if len(workspace_members) != 1:
                    errors.append("workspace_role_invalid")

                checked_v4 = None
                if len(v4_members) == 1:
                    v4_raw = archive.read(v4_members[0])
                    if _sha256_bytes(v4_raw) != str(
                        manifest.get("nested_v4_sha256") or ""
                    ):
                        errors.append("nested_v4_hash_mismatch")
                    checked_v4 = _nested_v4_verification_from_bytes(v4_raw)
                    if checked_v4.status != "valid":
                        errors.append(
                            "nested_v4_invalid:"
                            + ",".join(checked_v4.errors)
                        )

                if checked_v4 is not None and checked_v4.status == "valid":
                    v4_manifest = checked_v4.manifest or {}
                    nested_v4_status = str(
                        v4_manifest.get("status") or ""
                    ) or None
                    detail_count = int(
                        v4_manifest.get("detail_display_key_count") or 0
                    )
                    error_count = int(
                        v4_manifest.get("error_display_key_count") or 0
                    )
                    if trade_date != str(v4_manifest.get("trade_date") or ""):
                        errors.append("nested_v4_trade_date_mismatch")
                    if identity != str(
                        v4_manifest.get("input_identity_fingerprint") or ""
                    ):
                        errors.append("nested_v4_input_identity_mismatch")
                    if str(manifest.get("nested_v4_status") or "") != (
                        nested_v4_status or ""
                    ):
                        errors.append("nested_v4_status_mismatch")
                    if int(
                        manifest.get("detail_display_key_count") or 0
                    ) != detail_count:
                        errors.append("detail_count_mismatch")
                    if int(
                        manifest.get("error_display_key_count") or 0
                    ) != error_count:
                        errors.append("error_count_mismatch")

                if len(inspection_members) == 1 and trade_date is not None:
                    try:
                        inspection = _read_json_bytes(
                            archive.read(inspection_members[0]),
                            label="portable_inspection",
                        )
                    except RuntimeError as exc:
                        errors.append(str(exc))
                    else:
                        errors.extend(
                            _validate_inspection_payload(
                                inspection,
                                trade_date=trade_date,
                                input_identity_fingerprint=identity,
                            )
                        )

                if len(workspace_members) == 1:
                    errors.extend(
                        _validate_workspace_html(
                            archive.read(workspace_members[0])
                        )
                    )

                expected_status = (
                    "detail_degraded_portable_delivery"
                    if error_count > 0
                    else "complete_portable_delivery"
                )
                if manifest.get("status") != expected_status:
                    errors.append("portable_delivery_status_mismatch")
    except (OSError, ValueError, zipfile.BadZipFile):
        errors.append("bundle_not_readable_zip")

    return PortableDeliveryVerification(
        status="valid" if not errors else "invalid",
        bundle_path=str(bundle_path),
        schema_version=schema_version,
        file_count=file_count,
        trade_date=trade_date,
        nested_v4_status=nested_v4_status,
        detail_display_key_count=detail_count,
        error_display_key_count=error_count,
        errors=tuple(errors),
        warnings=tuple(warnings),
        manifest=manifest,
    )


def build_daily_portable_delivery_bundle(
    *,
    v4_bundle: str | Path,
    inspection_json: str | Path,
    workspace_html: str | Path,
    pipeline_report_sha256: str,
    output: str | Path,
) -> dict[str, Any]:
    v4_path = Path(v4_bundle)
    inspection_path = Path(inspection_json)
    workspace_path = Path(workspace_html)
    output_path = Path(output)

    checked_v4 = verify_daily_handoff_bundle_v4(v4_path)
    if checked_v4.status != "valid":
        raise RuntimeError(
            "handoff_v4_invalid:" + ",".join(checked_v4.errors)
        )
    v4_manifest = checked_v4.manifest or {}
    trade_date = str(v4_manifest.get("trade_date") or "")
    identity = str(v4_manifest.get("input_identity_fingerprint") or "")
    if not trade_date:
        raise RuntimeError("handoff_v4_trade_date_missing")
    if len(identity) != 64:
        raise RuntimeError("handoff_v4_input_identity_invalid")
    if len(str(pipeline_report_sha256)) != 64:
        raise RuntimeError("pipeline_report_sha256_invalid")

    inspection = _read_json_object(inspection_path)
    inspection_errors = _validate_inspection_payload(
        inspection,
        trade_date=trade_date,
        input_identity_fingerprint=identity,
    )
    if inspection_errors:
        raise RuntimeError(
            "inspection_invalid:" + ",".join(inspection_errors)
        )

    workspace_raw = workspace_path.read_bytes()
    workspace_errors = _validate_workspace_html(workspace_raw)
    if workspace_errors:
        raise RuntimeError(
            "workspace_invalid:" + ",".join(workspace_errors)
        )

    v4_raw = v4_path.read_bytes()
    inspection_raw = inspection_path.read_bytes()
    error_count = int(v4_manifest.get("error_display_key_count") or 0)
    detail_count = int(v4_manifest.get("detail_display_key_count") or 0)
    status = (
        "detail_degraded_portable_delivery"
        if error_count > 0
        else "complete_portable_delivery"
    )

    members: list[tuple[str, bytes, str]] = [
        (
            "base/htcn-daily-handoff-v4.zip",
            v4_raw,
            "m5_handoff_v4_base",
        ),
        (
            "workspace/m5-handoff-v4-inspector.json",
            inspection_raw,
            "m5_portable_inspector_json",
        ),
        (
            "workspace/m5-handoff-v4-pattern-workspace.html",
            workspace_raw,
            "m5_portable_workspace_html",
        ),
    ]
    records = [
        {
            "arcname": arcname,
            "role": role,
            "size_bytes": len(raw),
            "sha256": _sha256_bytes(raw),
        }
        for arcname, raw, role in members
    ]
    manifest = {
        "schema_version": PORTABLE_DELIVERY_SCHEMA_VERSION,
        "status": status,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "contract": PortableDeliveryContract().as_payload(),
        "trade_date": trade_date,
        "input_identity_fingerprint": identity,
        "pipeline_report_sha256": str(pipeline_report_sha256),
        "nested_v4_schema_version": 4,
        "nested_v4_status": v4_manifest.get("status"),
        "nested_v4_sha256": _sha256_bytes(v4_raw),
        "visual_semantics_version": 2,
        "detail_display_key_count": detail_count,
        "error_display_key_count": error_count,
        "files": records,
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
            "daily-portable-delivery-manifest.json",
            _canonical_json_bytes(manifest),
        )
        for arcname, raw, _ in members:
            archive.writestr(arcname, raw)

    checked = verify_daily_portable_delivery_bundle(tmp)
    if checked.status != "valid":
        tmp.unlink(missing_ok=True)
        raise RuntimeError(
            "portable_delivery_verification_failed:"
            + ",".join(checked.errors)
        )
    tmp.replace(output_path)
    final = verify_daily_portable_delivery_bundle(output_path)
    if final.status != "valid":
        raise RuntimeError(
            "portable_delivery_post_replace_verification_failed:"
            + ",".join(final.errors)
        )
    return {
        **manifest,
        "output": str(output_path),
        "bundle_size_bytes": output_path.stat().st_size,
        "bundle_sha256": _sha256_path(output_path),
        "verification": final.as_payload(),
    }


def run_daily_portable_delivery(
    *,
    root: str | Path,
    pipeline_report: str | Path,
    output: str | Path,
    run_report: str | Path,
    latest_pointer: str | Path,
    latest_v4_alias: str | Path,
    latest_inspector_alias: str | Path,
    latest_workspace_alias: str | Path,
    archive_root: str | Path,
    bars: int = 420,
    scales: tuple[int, ...] = (3, 5, 8, 13),
    v3_runner: RunV3 = run_daily_handoff_bundle_v3,
    v4_builder: BuildV4 = build_daily_handoff_bundle_v4,
    workspace_writer: WriteWorkspace = write_portable_pattern_workspace,
    identity_factory: IdentityFactory = _default_identity_factory,
    provider_factory: ProviderFactory = _default_provider_factory,
) -> tuple[dict[str, Any], int]:
    repo = Path(root).resolve()

    def resolve(value: str | Path) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = repo / path
        return path.resolve()

    pipeline_path = resolve(pipeline_report)
    output_path = resolve(output)
    run_report_path = resolve(run_report)
    latest_pointer_path = resolve(latest_pointer)
    latest_v4_path = resolve(latest_v4_alias)
    latest_inspector_path = resolve(latest_inspector_alias)
    latest_workspace_path = resolve(latest_workspace_alias)
    archive_root_path = resolve(archive_root)

    generated_at = datetime.now(UTC).isoformat()
    before_hash: str | None = None
    after_hash: str | None = None
    current_identity: str | None = None
    failed_stage: str | None = None
    error: str | None = None
    final_bundle: dict[str, Any] | None = None
    archive_dir: Path | None = None

    try:
        failed_stage = "pipeline_preflight"
        before_hash = _sha256_path(pipeline_path)
        pipeline = _read_json_object(pipeline_path)
        if pipeline.get("m5_product_ready") is not True:
            raise RuntimeError("pipeline_m5_product_not_ready")

        staging_parent = output_path.parent
        staging_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix=".m5-portable-delivery-",
            dir=staging_parent,
        ) as temp:
            stage = Path(temp)
            stage_v3 = stage / "htcn-daily-handoff-v3.zip"
            stage_v3_report = stage / "m5-daily-handoff-v3.json"
            stage_v4 = stage / "htcn-daily-handoff-v4.zip"
            stage_inspector = stage / "m5-handoff-v4-inspector.json"
            stage_workspace = stage / "m5-handoff-v4-pattern-workspace.html"
            stage_delivery = stage / "htcn-daily-portable-delivery-v1.zip"

            failed_stage = "handoff_v3"
            v3_payload, v3_code = v3_runner(
                root=repo,
                pipeline_report=pipeline_path,
                output=stage_v3,
                report=stage_v3_report,
            )
            if int(v3_code) != 0 or v3_payload.get("status") != "ready":
                raise RuntimeError(
                    "handoff_v3_build_failed:"
                    + str(v3_payload.get("error") or v3_code)
                )
            if not stage_v3.is_file():
                raise RuntimeError("handoff_v3_output_missing")

            failed_stage = "input_identity"
            current_identity = str(identity_factory(repo))
            if len(current_identity) != 64:
                raise RuntimeError("current_input_identity_invalid")

            failed_stage = "handoff_v4"
            provider = provider_factory(repo)
            v4_payload = v4_builder(
                v3_bundle=stage_v3,
                analysis_provider=provider,
                current_input_identity_fingerprint=current_identity,
                output=stage_v4,
                bars=int(bars),
                scales=tuple(scales),
            )
            if not stage_v4.is_file():
                raise RuntimeError("handoff_v4_output_missing")

            failed_stage = "workspace"
            workspace_payload = workspace_writer(
                bundle_path=stage_v4,
                json_output=stage_inspector,
                html_output=stage_workspace,
            )
            if workspace_payload.get("status") != "ready":
                raise RuntimeError("portable_workspace_not_ready")
            if not stage_inspector.is_file() or not stage_workspace.is_file():
                raise RuntimeError("portable_workspace_output_missing")

            failed_stage = "portable_delivery_bundle"
            final_bundle = build_daily_portable_delivery_bundle(
                v4_bundle=stage_v4,
                inspection_json=stage_inspector,
                workspace_html=stage_workspace,
                pipeline_report_sha256=before_hash,
                output=stage_delivery,
            )

            failed_stage = "pipeline_stability"
            after_hash = _sha256_path(pipeline_path)
            if after_hash != before_hash:
                raise RuntimeError("pipeline_report_changed_during_delivery")

            checked_delivery = verify_daily_portable_delivery_bundle(
                stage_delivery
            )
            if checked_delivery.status != "valid":
                raise RuntimeError(
                    "portable_delivery_stage_invalid:"
                    + ",".join(checked_delivery.errors)
                )

            trade_date = str(final_bundle.get("trade_date") or "")
            bundle_sha = str(final_bundle.get("bundle_sha256") or "")
            if not trade_date or len(bundle_sha) != 64:
                raise RuntimeError("portable_delivery_identity_missing")

            trade_date_root = archive_root_path / trade_date
            trade_date_root.mkdir(parents=True, exist_ok=True)
            archive_dir = trade_date_root / bundle_sha[:16]
            if archive_dir.exists():
                raise RuntimeError(
                    f"portable_delivery_archive_collision:{archive_dir}"
                )
            archive_stage = trade_date_root / (
                f".{bundle_sha[:16]}.tmp"
            )
            if archive_stage.exists():
                shutil.rmtree(archive_stage)
            archive_stage.mkdir(parents=False, exist_ok=False)

            archive_delivery = (
                archive_stage / "htcn-daily-portable-delivery-v1.zip"
            )
            archive_v4 = archive_stage / "htcn-daily-handoff-v4.zip"
            archive_inspector = (
                archive_stage / "m5-handoff-v4-inspector.json"
            )
            archive_workspace = (
                archive_stage / "m5-handoff-v4-pattern-workspace.html"
            )
            shutil.copyfile(stage_delivery, archive_delivery)
            shutil.copyfile(stage_v4, archive_v4)
            shutil.copyfile(stage_inspector, archive_inspector)
            shutil.copyfile(stage_workspace, archive_workspace)

            archive_manifest = {
                "schema_version": 1,
                "trade_date": trade_date,
                "bundle_sha256": bundle_sha,
                "input_identity_fingerprint": current_identity,
                "pipeline_report_sha256": before_hash,
                "delivery_status": final_bundle.get("status"),
                "files": {
                    "portable_delivery": {
                        "path": str(archive_delivery.relative_to(repo)),
                        "sha256": _sha256_path(archive_delivery),
                    },
                    "handoff_v4": {
                        "path": str(archive_v4.relative_to(repo)),
                        "sha256": _sha256_path(archive_v4),
                    },
                    "inspector_json": {
                        "path": str(archive_inspector.relative_to(repo)),
                        "sha256": _sha256_path(archive_inspector),
                    },
                    "workspace_html": {
                        "path": str(archive_workspace.relative_to(repo)),
                        "sha256": _sha256_path(archive_workspace),
                    },
                },
                "contract": PortableDeliveryContract().as_payload(),
            }
            _write_json_atomic(
                archive_stage / "m5-portable-delivery-archive.json",
                archive_manifest,
            )
            archive_stage.replace(archive_dir)

            # Paths in the manifest are computed against their final immutable
            # directory name, so rewrite once after the atomic directory move.
            archive_delivery = (
                archive_dir / "htcn-daily-portable-delivery-v1.zip"
            )
            archive_v4 = archive_dir / "htcn-daily-handoff-v4.zip"
            archive_inspector = (
                archive_dir / "m5-handoff-v4-inspector.json"
            )
            archive_workspace = (
                archive_dir / "m5-handoff-v4-pattern-workspace.html"
            )
            archive_manifest["files"] = {
                "portable_delivery": {
                    "path": str(archive_delivery.relative_to(repo)),
                    "sha256": _sha256_path(archive_delivery),
                },
                "handoff_v4": {
                    "path": str(archive_v4.relative_to(repo)),
                    "sha256": _sha256_path(archive_v4),
                },
                "inspector_json": {
                    "path": str(archive_inspector.relative_to(repo)),
                    "sha256": _sha256_path(archive_inspector),
                },
                "workspace_html": {
                    "path": str(archive_workspace.relative_to(repo)),
                    "sha256": _sha256_path(archive_workspace),
                },
            }
            _write_json_atomic(
                archive_dir / "m5-portable-delivery-archive.json",
                archive_manifest,
            )

            # Phase19-specific convenience aliases only. Frozen Phase14/16
            # canonical aliases are intentionally not overwritten.
            _copy_atomic(stage_delivery, output_path)
            _copy_atomic(stage_v4, latest_v4_path)
            _copy_atomic(stage_inspector, latest_inspector_path)
            _copy_atomic(stage_workspace, latest_workspace_path)

            latest_payload = {
                "schema_version": 1,
                "status": final_bundle.get("status"),
                "generated_at_utc": generated_at,
                "trade_date": trade_date,
                "input_identity_fingerprint": current_identity,
                "pipeline_report_sha256": before_hash,
                "bundle_sha256": bundle_sha,
                "archive_dir": str(archive_dir.relative_to(repo)),
                "portable_delivery": str(output_path.relative_to(repo)),
                "handoff_v4": str(latest_v4_path.relative_to(repo)),
                "inspector_json": str(
                    latest_inspector_path.relative_to(repo)
                ),
                "workspace_html": str(
                    latest_workspace_path.relative_to(repo)
                ),
                "detail_display_key_count": final_bundle.get(
                    "detail_display_key_count"
                ),
                "error_display_key_count": final_bundle.get(
                    "error_display_key_count"
                ),
                "contract": PortableDeliveryContract().as_payload(),
            }
            _write_json_atomic(latest_pointer_path, latest_payload)

        failed_stage = None
        exit_code = 0
        status = str(final_bundle.get("status") or "ready")
    except Exception as exc:
        exit_code = 2
        status = "failed"
        error = f"{type(exc).__name__}:{exc}"
        if pipeline_path.is_file():
            after_hash = _sha256_path(pipeline_path)

    pipeline_unchanged = (
        before_hash is not None
        and after_hash is not None
        and before_hash == after_hash
    )
    payload = {
        "schema_version": PORTABLE_DELIVERY_RUN_REPORT_SCHEMA_VERSION,
        "generated_at_utc": generated_at,
        "status": status,
        "exit_code": exit_code,
        "failed_stage": failed_stage,
        "error": error,
        "pipeline_report": str(pipeline_path),
        "pipeline_report_sha256_before": before_hash,
        "pipeline_report_sha256_after": after_hash,
        "pipeline_report_unchanged": pipeline_unchanged,
        "current_input_identity_fingerprint": current_identity,
        "output": str(output_path),
        "latest_pointer": str(latest_pointer_path),
        "archive_dir": None if archive_dir is None else str(archive_dir),
        "bundle": final_bundle,
        "previous_successful_delivery_is_preserved_on_failure": True,
        "frozen_phase14_16_aliases_overwritten": False,
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "imports_product_state": False,
        "creates_review_events": False,
        "is_trade_instruction": False,
        "alpha_inference_allowed": False,
        "predictive_score_used": False,
        "historical_outcome_used_for_ranking": False,
    }
    _write_json_atomic(run_report_path, payload)
    return payload, exit_code
