from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import PurePosixPath, Path
import json
from typing import Any
import zipfile


SUPPORTED_BUNDLE_SCHEMA_VERSIONS = (1,)


@dataclass(frozen=True, slots=True)
class BundleVerification:
    status: str
    bundle_path: str
    schema_version: int | None
    listed_file_count: int
    archive_member_count: int
    error_count: int
    warning_count: int
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    manifest: dict[str, Any] | None

    def as_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["errors"] = list(self.errors)
        payload["warnings"] = list(self.warnings)
        return payload


def _safe_member_name(name: str) -> bool:
    if not name or "\\" in name:
        return False
    path = PurePosixPath(name)
    if path.is_absolute():
        return False
    return all(part not in ("", ".", "..") for part in path.parts)


def _sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def verify_evidence_bundle(path: str | Path) -> BundleVerification:
    bundle_path = Path(path)
    errors: list[str] = []
    warnings: list[str] = []
    manifest: dict[str, Any] | None = None
    schema_version: int | None = None
    listed_count = 0
    archive_count = 0

    if not bundle_path.is_file():
        errors.append("bundle_missing")
        return BundleVerification(
            status="invalid",
            bundle_path=str(bundle_path),
            schema_version=None,
            listed_file_count=0,
            archive_member_count=0,
            error_count=1,
            warning_count=0,
            errors=tuple(errors),
            warnings=(),
            manifest=None,
        )

    try:
        with zipfile.ZipFile(bundle_path, "r") as archive:
            infos = archive.infolist()
            archive_count = len(infos)
            names = [info.filename for info in infos]

            if len(names) != len(set(names)):
                errors.append("duplicate_archive_member")

            unsafe = sorted(name for name in names if not _safe_member_name(name))
            if unsafe:
                errors.append(
                    "unsafe_archive_member:" + ",".join(unsafe)
                )

            if "bundle-manifest.json" not in names:
                errors.append("bundle_manifest_missing")
            else:
                try:
                    raw_manifest = archive.read("bundle-manifest.json")
                    value = json.loads(raw_manifest.decode("utf-8"))
                    if not isinstance(value, dict):
                        errors.append("bundle_manifest_not_object")
                    else:
                        manifest = value
                except (KeyError, UnicodeDecodeError, json.JSONDecodeError):
                    errors.append("bundle_manifest_unreadable")

            if manifest is not None:
                try:
                    schema_version = int(manifest.get("schema_version"))
                except (TypeError, ValueError):
                    errors.append("bundle_schema_invalid")
                else:
                    if schema_version not in SUPPORTED_BUNDLE_SCHEMA_VERSIONS:
                        errors.append("bundle_schema_unsupported")

                records_raw = manifest.get("files")
                if not isinstance(records_raw, list):
                    errors.append("bundle_files_manifest_invalid")
                    records: list[dict[str, Any]] = []
                else:
                    records = []
                    for item in records_raw:
                        if not isinstance(item, dict):
                            errors.append("bundle_file_record_not_object")
                            continue
                        records.append(dict(item))

                listed_count = len(records)
                arcnames = [str(item.get("arcname") or "") for item in records]
                if len(arcnames) != len(set(arcnames)):
                    errors.append("duplicate_manifest_arcname")
                if any(not _safe_member_name(name) for name in arcnames):
                    errors.append("unsafe_manifest_arcname")

                archive_payload_names = sorted(
                    name for name in names if name != "bundle-manifest.json"
                )
                if sorted(arcnames) != archive_payload_names:
                    missing = sorted(set(arcnames) - set(archive_payload_names))
                    extra = sorted(set(archive_payload_names) - set(arcnames))
                    if missing:
                        errors.append(
                            "manifest_member_missing:" + ",".join(missing)
                        )
                    if extra:
                        errors.append(
                            "unlisted_archive_member:" + ",".join(extra)
                        )

                for item in records:
                    arcname = str(item.get("arcname") or "")
                    if not arcname or arcname not in names:
                        continue
                    try:
                        payload = archive.read(arcname)
                    except KeyError:
                        continue
                    expected_size = item.get("size_bytes")
                    expected_sha = str(item.get("sha256") or "")
                    try:
                        size_ok = int(expected_size) == len(payload)
                    except (TypeError, ValueError):
                        size_ok = False
                    if not size_ok:
                        errors.append(f"size_mismatch:{arcname}")
                    if len(expected_sha) != 64 or _sha256_bytes(payload) != expected_sha:
                        errors.append(f"sha256_mismatch:{arcname}")

                if manifest.get("alpha_inference_allowed") is not False:
                    errors.append("alpha_inference_boundary_invalid")
                if manifest.get("is_trade_instruction") is not False:
                    errors.append("trade_instruction_boundary_invalid")
                if manifest.get("authoritative_evidence_modified") is not False:
                    errors.append("authoritative_modification_boundary_invalid")

                status = str(manifest.get("status") or "")
                blocker_count = manifest.get("evidence_health_blocker_count")
                if status == "transport_bundle_ready":
                    try:
                        blockers = int(blocker_count or 0)
                    except (TypeError, ValueError):
                        blockers = -1
                    if blockers != 0:
                        errors.append("ready_bundle_has_health_blockers")
                    if manifest.get("committed_capture_read_error") not in (None, ""):
                        errors.append("ready_bundle_has_capture_read_error")
                elif status == "evidence_health_blocked":
                    warnings.append("bundle_reports_evidence_health_blocked")
                else:
                    errors.append("bundle_status_invalid")

                try:
                    capture_count = int(manifest.get("committed_capture_count") or 0)
                except (TypeError, ValueError):
                    capture_count = -1
                    errors.append("committed_capture_count_invalid")

                capture_members = [
                    name
                    for name in arcnames
                    if name.startswith("authoritative/captures/")
                    and name.endswith(".json")
                ]
                if capture_count >= 0 and len(capture_members) < capture_count:
                    errors.append("capture_member_count_below_manifest")

                if capture_count > 0:
                    if not manifest.get("latest_committed_capture_date"):
                        errors.append("latest_capture_date_missing")
                    if not manifest.get("latest_capture_transaction_id"):
                        errors.append("latest_capture_transaction_id_missing")

                if not manifest.get("methodology_fingerprint"):
                    errors.append("methodology_fingerprint_missing")
                if not manifest.get("methodology_contract_version"):
                    errors.append("methodology_contract_version_missing")

    except (OSError, zipfile.BadZipFile):
        errors.append("bundle_not_readable_zip")

    return BundleVerification(
        status="valid" if not errors else "invalid",
        bundle_path=str(bundle_path),
        schema_version=schema_version,
        listed_file_count=listed_count,
        archive_member_count=archive_count,
        error_count=len(errors),
        warning_count=len(warnings),
        errors=tuple(errors),
        warnings=tuple(warnings),
        manifest=manifest,
    )
