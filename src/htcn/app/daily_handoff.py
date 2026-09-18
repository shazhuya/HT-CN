from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import tempfile
from typing import Any
import zipfile

from htcn.app.operator_snapshot import (
    OPERATOR_SNAPSHOT_CONTRACT_VERSION,
    OPERATOR_SNAPSHOT_SCHEMA_VERSION,
)
from htcn.research.evidence_bundle import verify_evidence_bundle


DAILY_HANDOFF_SCHEMA_VERSION = 2
CANONICAL_BARS = 420
CANONICAL_SCALES = (3, 5, 8, 13)
PERSISTED_CACHE_STATUSES = {
    "hit",
    "hit_after_race",
    "hit_after_process_wait",
    "rebuilt",
    "rebuilt_force",
    "coalesced_wait",
}


@dataclass(frozen=True, slots=True)
class ProductBinding:
    trade_date: str
    cache_path: str
    cache_status: str
    cache_freshness: str
    input_identity_contract_version: int
    input_identity_fingerprint: str
    report_sha256: str
    snapshot_sha256: str

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DailyHandoffVerification:
    status: str
    bundle_path: str
    schema_version: int | None
    file_count: int
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    manifest: dict[str, Any] | None

    def as_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["errors"] = list(self.errors)
        payload["warnings"] = list(self.warnings)
        return payload


def _sha256_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _safe_arcname(name: str) -> bool:
    if not name or "\\" in name:
        return False
    path = PurePosixPath(name)
    if path.is_absolute():
        return False
    return all(part not in ("", ".", "..") for part in path.parts)


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{label}_unreadable:{type(exc).__name__}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{label}_not_object")
    return value


def _resolve_inside(root: Path, value: str | Path, *, label: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    base = root.resolve()
    if resolved != base and base not in resolved.parents:
        raise RuntimeError(f"{label}_outside_root")
    return resolved


def _repo_relative(repo: Path, path: Path, *, label: str) -> str:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError as exc:
        raise RuntimeError(f"{label}_outside_repository") from exc


def _artifact_path(
    repo: Path,
    pipeline_summary: dict[str, Any],
    key: str,
    fallback: str,
) -> Path:
    artifacts = pipeline_summary.get("artifacts")
    raw = fallback
    if isinstance(artifacts, dict) and artifacts.get(key):
        raw = str(artifacts[key])
    return _resolve_inside(repo, raw, label=f"{key}_path")


def _require_pipeline_source(
    repo: Path,
    pipeline_summary: dict[str, Any],
) -> tuple[Path, bytes]:
    path = _artifact_path(
        repo,
        pipeline_summary,
        "pipeline_report",
        "artifacts/reports/m5-daily-close-pipeline.json",
    )
    if not path.is_file():
        raise RuntimeError("pipeline_report_missing")
    payload = _read_json_object(path, label="pipeline_report")
    if payload != pipeline_summary:
        raise RuntimeError("pipeline_report_payload_mismatch")
    return path, path.read_bytes()


def _canonical_snapshot_name(trade_date: str) -> str:
    scales = "-".join(str(value) for value in CANONICAL_SCALES)
    return f"{trade_date}__b{CANONICAL_BARS}__s{scales}.json"


def _validate_product_binding(
    repo: Path,
    pipeline_summary: dict[str, Any],
) -> tuple[ProductBinding, Path, bytes, Path, bytes]:
    report_path = _artifact_path(
        repo,
        pipeline_summary,
        "m5_operator_snapshot_report",
        "artifacts/reports/m5-operator-snapshot.json",
    )
    if not report_path.is_file():
        raise RuntimeError("m5_operator_snapshot_report_missing")
    report = _read_json_object(report_path, label="m5_operator_snapshot_report")
    report_bytes = report_path.read_bytes()

    if int(report.get("schema_version") or 0) != 2:
        raise RuntimeError("m5_operator_snapshot_report_schema_mismatch")
    if report.get("product_ready") is not True:
        raise RuntimeError("pipeline_product_ready_but_m5_report_not_ready")

    trade_date = str(report.get("as_of_trade_date") or "")
    if not trade_date:
        raise RuntimeError("m5_report_trade_date_missing")
    if report.get("observation_integrity") != "single_as_of":
        raise RuntimeError("m5_report_not_single_as_of")

    identity = report.get("input_identity")
    if not isinstance(identity, dict):
        raise RuntimeError("m5_report_input_identity_missing")
    fingerprint = str(identity.get("fingerprint") or "")
    contract_version = int(identity.get("contract_version") or 0)
    if len(fingerprint) != 64:
        raise RuntimeError("m5_report_input_identity_invalid")

    cache = report.get("product_cache")
    if not isinstance(cache, dict):
        raise RuntimeError("m5_report_product_cache_missing")
    cache_status = str(cache.get("status") or "")
    if cache_status not in PERSISTED_CACHE_STATUSES:
        raise RuntimeError("m5_report_cache_not_persisted")
    if cache.get("freshness") != "current":
        raise RuntimeError("m5_report_cache_not_current")
    if cache.get("input_identity_stable_during_build") is not True:
        raise RuntimeError("m5_report_input_identity_not_stable")
    if str(cache.get("expected_local_trade_date") or "") != trade_date:
        raise RuntimeError("m5_report_expected_trade_date_mismatch")
    if str(cache.get("queue_as_of_trade_date") or "") != trade_date:
        raise RuntimeError("m5_report_queue_trade_date_mismatch")
    if str(cache.get("input_identity_fingerprint") or "") != fingerprint:
        raise RuntimeError("m5_report_cache_identity_mismatch")
    if int(cache.get("input_identity_contract_version") or 0) != contract_version:
        raise RuntimeError("m5_report_cache_identity_contract_mismatch")

    raw_cache_path = str(cache.get("cache_path") or "")
    if not raw_cache_path:
        raise RuntimeError("m5_report_cache_path_missing")
    cache_root = (repo / "data" / "product" / "m5" / "operator_queue").resolve()
    raw_snapshot_path = Path(raw_cache_path)
    if raw_snapshot_path.is_absolute():
        snapshot_path = _resolve_inside(
            cache_root,
            raw_snapshot_path,
            label="m5_current_snapshot",
        )
    else:
        snapshot_path = _resolve_inside(
            repo,
            raw_snapshot_path,
            label="m5_current_snapshot",
        )
        if snapshot_path != cache_root and cache_root not in snapshot_path.parents:
            raise RuntimeError("m5_current_snapshot_outside_cache_root")
    if snapshot_path.parent != cache_root:
        raise RuntimeError("m5_current_snapshot_not_cache_root_member")
    if snapshot_path.name != _canonical_snapshot_name(trade_date):
        raise RuntimeError("m5_current_snapshot_filename_mismatch")
    if not snapshot_path.is_file():
        raise RuntimeError("m5_current_snapshot_missing")

    snapshot = _read_json_object(snapshot_path, label="m5_current_snapshot")
    snapshot_bytes = snapshot_path.read_bytes()
    if int(snapshot.get("schema_version") or 0) != OPERATOR_SNAPSHOT_SCHEMA_VERSION:
        raise RuntimeError("m5_current_snapshot_schema_mismatch")
    if int(snapshot.get("contract_version") or 0) != OPERATOR_SNAPSHOT_CONTRACT_VERSION:
        raise RuntimeError("m5_current_snapshot_contract_mismatch")
    if str(snapshot.get("expected_trade_date") or "") != trade_date:
        raise RuntimeError("m5_current_snapshot_trade_date_mismatch")
    if int(snapshot.get("bars") or 0) != CANONICAL_BARS:
        raise RuntimeError("m5_current_snapshot_bars_mismatch")
    if tuple(int(value) for value in snapshot.get("scales") or []) != CANONICAL_SCALES:
        raise RuntimeError("m5_current_snapshot_scales_mismatch")
    snapshot_identity = snapshot.get("input_identity")
    if not isinstance(snapshot_identity, dict):
        raise RuntimeError("m5_current_snapshot_input_identity_missing")
    if snapshot_identity != identity:
        raise RuntimeError("m5_current_snapshot_input_identity_mismatch")
    queue = snapshot.get("queue")
    if not isinstance(queue, dict):
        raise RuntimeError("m5_current_snapshot_queue_missing")
    if str(queue.get("as_of_trade_date") or "") != trade_date:
        raise RuntimeError("m5_current_snapshot_queue_trade_date_mismatch")
    if queue.get("observation_integrity") != "single_as_of":
        raise RuntimeError("m5_current_snapshot_queue_not_single_as_of")
    if snapshot.get("authoritative_evidence") is not False:
        raise RuntimeError("m5_current_snapshot_authority_boundary_invalid")
    if snapshot.get("writes_m4_evidence") is not False:
        raise RuntimeError("m5_current_snapshot_m4_write_boundary_invalid")

    binding = ProductBinding(
        trade_date=trade_date,
        cache_path=_repo_relative(
            repo,
            snapshot_path,
            label="m5_current_snapshot",
        ),
        cache_status=cache_status,
        cache_freshness="current",
        input_identity_contract_version=contract_version,
        input_identity_fingerprint=fingerprint,
        report_sha256=_sha256_bytes(report_bytes),
        snapshot_sha256=_sha256_bytes(snapshot_bytes),
    )
    return binding, report_path, report_bytes, snapshot_path, snapshot_bytes


def _previous_snapshot(
    cache_root: Path,
    *,
    current_path: Path,
    current_trade_date: str,
) -> tuple[Path, bytes] | None:
    candidates: list[tuple[str, Path]] = []
    if not cache_root.is_dir():
        return None
    for path in cache_root.glob("*.json"):
        if path.resolve() == current_path.resolve():
            continue
        try:
            payload = _read_json_object(path, label="previous_snapshot")
        except RuntimeError:
            continue
        trade_date = str(payload.get("expected_trade_date") or "")
        if not trade_date or trade_date >= current_trade_date:
            continue
        if int(payload.get("schema_version") or 0) != OPERATOR_SNAPSHOT_SCHEMA_VERSION:
            continue
        if int(payload.get("contract_version") or 0) != OPERATOR_SNAPSHOT_CONTRACT_VERSION:
            continue
        if int(payload.get("bars") or 0) != CANONICAL_BARS:
            continue
        if tuple(int(v) for v in payload.get("scales") or []) != CANONICAL_SCALES:
            continue
        if path.name != _canonical_snapshot_name(trade_date):
            continue
        if payload.get("authoritative_evidence") is not False:
            continue
        if payload.get("writes_m4_evidence") is not False:
            continue
        queue = payload.get("queue")
        if not isinstance(queue, dict):
            continue
        if str(queue.get("as_of_trade_date") or "") != trade_date:
            continue
        if queue.get("observation_integrity") != "single_as_of":
            continue
        candidates.append((trade_date, path))
    if not candidates:
        return None
    _, path = max(candidates, key=lambda item: item[0])
    return path, path.read_bytes()


def _verify_nested_m4_bytes(data: bytes) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="htcn-m4-bundle-") as temp:
        path = Path(temp) / "m4-evidence-bundle.zip"
        path.write_bytes(data)
        return verify_evidence_bundle(path).as_payload()


def _m4_verification_summary(checked: Any) -> dict[str, Any]:
    manifest = checked.manifest if isinstance(checked.manifest, dict) else {}
    return {
        "status": checked.status,
        "schema_version": checked.schema_version,
        "listed_file_count": checked.listed_file_count,
        "archive_member_count": checked.archive_member_count,
        "error_count": checked.error_count,
        "warning_count": checked.warning_count,
        "errors": list(checked.errors),
        "warnings": list(checked.warnings),
        "nested_manifest_status": manifest.get("status"),
        "methodology_contract_version": manifest.get(
            "methodology_contract_version"
        ),
        "methodology_fingerprint": manifest.get("methodology_fingerprint"),
        "latest_committed_capture_date": manifest.get(
            "latest_committed_capture_date"
        ),
        "latest_capture_transaction_id": manifest.get(
            "latest_capture_transaction_id"
        ),
    }


def verify_daily_handoff_bundle(path: str | Path) -> DailyHandoffVerification:
    bundle_path = Path(path)
    errors: list[str] = []
    warnings: list[str] = []
    manifest: dict[str, Any] | None = None
    schema_version: int | None = None
    file_count = 0

    if not bundle_path.is_file():
        return DailyHandoffVerification(
            status="invalid",
            bundle_path=str(bundle_path),
            schema_version=None,
            file_count=0,
            errors=("bundle_missing",),
            warnings=(),
            manifest=None,
        )

    try:
        with zipfile.ZipFile(bundle_path, "r") as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                errors.append("duplicate_archive_member")
            if any(not _safe_arcname(name) for name in names):
                errors.append("unsafe_archive_member")

            if "daily-handoff-manifest.json" not in names:
                errors.append("manifest_missing")
            else:
                try:
                    loaded = json.loads(
                        archive.read("daily-handoff-manifest.json").decode("utf-8")
                    )
                except (KeyError, UnicodeDecodeError, json.JSONDecodeError):
                    errors.append("manifest_unreadable")
                else:
                    if isinstance(loaded, dict):
                        manifest = loaded
                    else:
                        errors.append("manifest_not_object")

            if manifest is not None:
                try:
                    schema_version = int(manifest.get("schema_version"))
                except (TypeError, ValueError):
                    errors.append("manifest_schema_invalid")
                else:
                    if schema_version != DAILY_HANDOFF_SCHEMA_VERSION:
                        errors.append("manifest_schema_unsupported")

                if manifest.get("transport_only") is not True:
                    errors.append("transport_only_boundary_invalid")
                if manifest.get("authoritative_evidence") is not False:
                    errors.append("handoff_authority_boundary_invalid")
                if manifest.get("writes_m4_evidence") is not False:
                    errors.append("handoff_m4_write_boundary_invalid")
                if manifest.get("is_trade_instruction") is not False:
                    errors.append("trade_instruction_boundary_invalid")
                if manifest.get("alpha_inference_allowed") is not False:
                    errors.append("alpha_boundary_invalid")

                raw_records = manifest.get("files")
                records = raw_records if isinstance(raw_records, list) else []
                if not isinstance(raw_records, list):
                    errors.append("manifest_files_invalid")
                file_count = len(records)
                by_arcname: dict[str, dict[str, Any]] = {}
                for record in records:
                    if not isinstance(record, dict):
                        errors.append("manifest_file_record_invalid")
                        continue
                    arcname = str(record.get("arcname") or "")
                    if not _safe_arcname(arcname):
                        errors.append("manifest_arcname_invalid")
                        continue
                    if arcname in by_arcname:
                        errors.append("duplicate_manifest_arcname")
                    by_arcname[arcname] = record

                actual = set(names) - {"daily-handoff-manifest.json"}
                if set(by_arcname) != actual:
                    errors.append("manifest_member_set_mismatch")

                for arcname, record in by_arcname.items():
                    if arcname not in actual:
                        continue
                    data = archive.read(arcname)
                    try:
                        expected_size = int(record.get("size_bytes"))
                    except (TypeError, ValueError):
                        expected_size = -1
                    if expected_size != len(data):
                        errors.append(f"member_size_mismatch:{arcname}")
                    if str(record.get("sha256") or "") != _sha256_bytes(data):
                        errors.append(f"member_hash_mismatch:{arcname}")

                product_ready = manifest.get("m5_product_ready") is True
                research_ready = manifest.get("m4_research_ready") is True
                roles: dict[str, list[str]] = {}
                for arcname, record in by_arcname.items():
                    roles.setdefault(str(record.get("role") or ""), []).append(arcname)

                pipeline_members = roles.get("pipeline_summary", [])
                if len(pipeline_members) != 1:
                    errors.append("pipeline_summary_role_invalid")
                else:
                    pipeline_raw = archive.read(pipeline_members[0])
                    if _sha256_bytes(pipeline_raw) != str(
                        manifest.get("pipeline_report_sha256") or ""
                    ):
                        errors.append("pipeline_report_hash_mismatch")
                    try:
                        pipeline_payload = json.loads(
                            pipeline_raw.decode("utf-8")
                        )
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        errors.append("pipeline_summary_unreadable")
                    else:
                        if not isinstance(pipeline_payload, dict):
                            errors.append("pipeline_summary_not_object")
                        else:
                            if (
                                pipeline_payload.get("m5_product_ready") is True
                            ) != product_ready:
                                errors.append(
                                    "pipeline_product_ready_mismatch"
                                )
                            if (
                                pipeline_payload.get("m4_research_ready") is True
                            ) != research_ready:
                                errors.append(
                                    "pipeline_research_ready_mismatch"
                                )
                            if pipeline_payload.get("overall_status") != manifest.get(
                                "pipeline_overall_status"
                            ):
                                errors.append(
                                    "pipeline_overall_status_mismatch"
                                )

                if product_ready:
                    if len(roles.get("m5_current_product_snapshot", [])) != 1:
                        errors.append("current_product_snapshot_role_invalid")
                    if len(roles.get("m5_final_product_report", [])) != 1:
                        errors.append("final_product_report_role_invalid")
                    binding = manifest.get("product_binding")
                    if not isinstance(binding, dict):
                        errors.append("product_binding_missing")
                    else:
                        current = roles.get("m5_current_product_snapshot", [])
                        report = roles.get("m5_final_product_report", [])
                        if current:
                            raw = archive.read(current[0])
                            if _sha256_bytes(raw) != str(
                                binding.get("snapshot_sha256") or ""
                            ):
                                errors.append("product_binding_snapshot_hash_mismatch")
                            try:
                                snap = json.loads(raw.decode("utf-8"))
                            except (UnicodeDecodeError, json.JSONDecodeError):
                                errors.append("bound_snapshot_unreadable")
                            else:
                                if not isinstance(snap, dict):
                                    errors.append("bound_snapshot_not_object")
                                else:
                                    if int(snap.get("contract_version") or 0) != OPERATOR_SNAPSHOT_CONTRACT_VERSION:
                                        errors.append("bound_snapshot_contract_mismatch")
                                    if str(snap.get("expected_trade_date") or "") != str(binding.get("trade_date") or ""):
                                        errors.append("bound_snapshot_trade_date_mismatch")
                                    identity = snap.get("input_identity")
                                    if not isinstance(identity, dict) or str(identity.get("fingerprint") or "") != str(binding.get("input_identity_fingerprint") or ""):
                                        errors.append("bound_snapshot_identity_mismatch")
                        if report:
                            raw = archive.read(report[0])
                            if _sha256_bytes(raw) != str(
                                binding.get("report_sha256") or ""
                            ):
                                errors.append("product_binding_report_hash_mismatch")
                            try:
                                report_payload = json.loads(
                                    raw.decode("utf-8")
                                )
                            except (UnicodeDecodeError, json.JSONDecodeError):
                                errors.append("bound_product_report_unreadable")
                            else:
                                if not isinstance(report_payload, dict):
                                    errors.append("bound_product_report_not_object")
                                else:
                                    if int(report_payload.get("schema_version") or 0) != 2:
                                        errors.append("bound_product_report_schema_mismatch")
                                    if report_payload.get("product_ready") is not True:
                                        errors.append("bound_product_report_not_ready")
                                    if report_payload.get("observation_integrity") != "single_as_of":
                                        errors.append("bound_product_report_not_single_as_of")
                                    if str(report_payload.get("as_of_trade_date") or "") != str(
                                        binding.get("trade_date") or ""
                                    ):
                                        errors.append("bound_product_report_trade_date_mismatch")
                                    report_identity = report_payload.get("input_identity")
                                    if (
                                        not isinstance(report_identity, dict)
                                        or str(report_identity.get("fingerprint") or "")
                                        != str(binding.get("input_identity_fingerprint") or "")
                                    ):
                                        errors.append("bound_product_report_identity_mismatch")
                                    report_cache = report_payload.get("product_cache")
                                    if not isinstance(report_cache, dict):
                                        errors.append("bound_product_report_cache_missing")
                                    else:
                                        if str(report_cache.get("status") or "") not in PERSISTED_CACHE_STATUSES:
                                            errors.append("bound_product_report_cache_not_persisted")
                                        if report_cache.get("freshness") != "current":
                                            errors.append("bound_product_report_cache_not_current")
                                        if report_cache.get("input_identity_stable_during_build") is not True:
                                            errors.append("bound_product_report_identity_not_stable")
                                        if str(report_cache.get("input_identity_fingerprint") or "") != str(
                                            binding.get("input_identity_fingerprint") or ""
                                        ):
                                            errors.append("bound_product_report_cache_identity_mismatch")

                m4_current = roles.get("m4_current_evidence_bundle", [])
                if research_ready and len(m4_current) != 1:
                    errors.append("current_m4_evidence_role_invalid")
                for arcname in (
                    roles.get("m4_current_evidence_bundle", [])
                    + roles.get("m4_existing_evidence_bundle", [])
                ):
                    nested = _verify_nested_m4_bytes(archive.read(arcname))
                    if nested.get("status") != "valid":
                        errors.append("nested_m4_bundle_invalid")
    except (OSError, zipfile.BadZipFile):
        errors.append("bundle_not_readable_zip")

    return DailyHandoffVerification(
        status="valid" if not errors else "invalid",
        bundle_path=str(bundle_path),
        schema_version=schema_version,
        file_count=file_count,
        errors=tuple(errors),
        warnings=tuple(warnings),
        manifest=manifest,
    )


def build_daily_handoff_bundle(
    *,
    root: str | Path,
    pipeline_summary: dict[str, Any],
    output: str | Path,
) -> dict[str, Any]:
    repo = Path(root).resolve()
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = repo / output_path
    output_path = output_path.resolve()

    pipeline_path, pipeline_bytes = _require_pipeline_source(
        repo,
        pipeline_summary,
    )
    product_ready = pipeline_summary.get("m5_product_ready") is True
    research_ready = pipeline_summary.get("m4_research_ready") is True

    members: list[tuple[str, bytes, str]] = [
        (
            "pipeline/m5-daily-close-pipeline.json",
            pipeline_bytes,
            "pipeline_summary",
        )
    ]
    warnings: list[str] = []
    product_binding: ProductBinding | None = None

    if product_ready:
        (
            product_binding,
            report_path,
            report_bytes,
            snapshot_path,
            snapshot_bytes,
        ) = _validate_product_binding(repo, pipeline_summary)
        members.append(
            (
                "m5/m5-operator-snapshot.json",
                report_bytes,
                "m5_final_product_report",
            )
        )
        members.append(
            (
                f"m5/operator_snapshots/{snapshot_path.name}",
                snapshot_bytes,
                "m5_current_product_snapshot",
            )
        )
        previous = _previous_snapshot(
            snapshot_path.parent,
            current_path=snapshot_path,
            current_trade_date=product_binding.trade_date,
        )
        if previous is not None:
            previous_path, previous_bytes = previous
            members.append(
                (
                    f"m5/operator_snapshots/{previous_path.name}",
                    previous_bytes,
                    "m5_previous_product_snapshot",
                )
            )
    else:
        report_path = _artifact_path(
            repo,
            pipeline_summary,
            "m5_operator_snapshot_report",
            "artifacts/reports/m5-operator-snapshot.json",
        )
        if report_path.is_file():
            members.append(
                (
                    "m5/m5-operator-snapshot.json",
                    report_path.read_bytes(),
                    "m5_existing_product_report",
                )
            )

    reports_root = (repo / "artifacts" / "reports").resolve()
    for path in sorted(reports_root.glob("m5-daily-*.log")):
        if path.is_file():
            members.append(
                (
                    f"logs/{path.name}",
                    path.read_bytes(),
                    "pipeline_step_log",
                )
            )

    m4_path = _artifact_path(
        repo,
        pipeline_summary,
        "m4_evidence_bundle",
        "artifacts/reports/m4-evidence-bundle.zip",
    )
    m4_verification: dict[str, Any] | None = None
    if m4_path.is_file():
        checked = verify_evidence_bundle(m4_path)
        m4_verification = _m4_verification_summary(checked)
        if checked.status == "valid":
            members.append(
                (
                    "m4/m4-evidence-bundle.zip",
                    m4_path.read_bytes(),
                    (
                        "m4_current_evidence_bundle"
                        if research_ready
                        else "m4_existing_evidence_bundle"
                    ),
                )
            )
        elif research_ready:
            raise RuntimeError(
                "m4_research_ready_but_evidence_bundle_invalid:"
                + ",".join(checked.errors)
            )
        else:
            warnings.append("invalid_existing_m4_bundle_omitted")
    elif research_ready:
        raise RuntimeError("m4_research_ready_but_evidence_bundle_missing")

    records = [
        {
            "arcname": arcname,
            "role": role,
            "size_bytes": len(data),
            "sha256": _sha256_bytes(data),
        }
        for arcname, data, role in members
    ]
    status = (
        "complete_transport"
        if product_ready and research_ready
        else "product_transport_research_degraded"
        if product_ready
        else "research_transport_product_failed"
        if research_ready
        else "degraded_transport"
    )
    manifest: dict[str, Any] = {
        "schema_version": DAILY_HANDOFF_SCHEMA_VERSION,
        "status": status,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "transport_only": True,
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "is_trade_instruction": False,
        "alpha_inference_allowed": False,
        "m4_authority_remains_nested_capture_chain": True,
        "m5_product_snapshot_is_authoritative_evidence": False,
        "pipeline_overall_status": pipeline_summary.get("overall_status"),
        "pipeline_report_sha256": _sha256_bytes(pipeline_bytes),
        "pipeline_report_source": _repo_relative(
            repo,
            pipeline_path,
            label="pipeline_report",
        ),
        "m5_product_ready": product_ready,
        "m4_research_ready": research_ready,
        "product_binding": (
            None if product_binding is None else product_binding.as_payload()
        ),
        "m4_nested_bundle_verification": m4_verification,
        "warnings": warnings,
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
            "daily-handoff-manifest.json",
            _canonical_json_bytes(manifest),
        )
        for arcname, data, _ in members:
            archive.writestr(arcname, data)

    verification = verify_daily_handoff_bundle(tmp)
    if verification.status != "valid":
        tmp.unlink(missing_ok=True)
        raise RuntimeError(
            "daily_handoff_verification_failed:"
            + ",".join(verification.errors)
        )
    tmp.replace(output_path)

    final = verify_daily_handoff_bundle(output_path)
    if final.status != "valid":
        raise RuntimeError(
            "daily_handoff_post_replace_verification_failed:"
            + ",".join(final.errors)
        )

    return {
        **manifest,
        "output": str(output_path),
        "bundle_size_bytes": output_path.stat().st_size,
        "bundle_sha256": _sha256_path(output_path),
        "verification": final.as_payload(),
    }
