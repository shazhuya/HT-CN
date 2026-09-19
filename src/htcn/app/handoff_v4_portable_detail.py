from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
from pathlib import Path, PurePosixPath
import tempfile
from typing import Any, Protocol
import zipfile

from htcn.app.daily_handoff_v3 import verify_daily_handoff_bundle_v3
from htcn.app.handoff_v3_inspector import build_handoff_v3_inspection


DAILY_HANDOFF_V4_SCHEMA_VERSION = 4
PORTABLE_DETAIL_SCHEMA_VERSION = 1
DEFAULT_BARS = 420
DEFAULT_SCALES = (3, 5, 8, 13)


class PortableDetailAnalysisProvider(Protocol):
    def analyze(
        self,
        instrument_id: str,
        *,
        bars: int,
        scales: tuple[int, ...],
    ) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class HandoffV4Contract:
    version: int = 1
    semantics: str = "verified_v3_plus_portable_pattern_detail"
    nested_v3_unmodified: bool = True
    queue_semantics_changed: bool = False
    detail_changes_ranking: bool = False
    authoritative_evidence: bool = False
    writes_m4_evidence: bool = False
    writes_operator_queue: bool = False
    writes_operator_history: bool = False
    writes_review_journal: bool = False
    creates_review_events: bool = False
    predictive_score_used: bool = False
    historical_outcome_used_for_ranking: bool = False
    alpha_inference_allowed: bool = False
    is_trade_instruction: bool = False

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DailyHandoffV4Verification:
    status: str
    bundle_path: str
    schema_version: int | None
    file_count: int
    queue_display_key_count: int
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


def _read_json_bytes(data: bytes, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{label}_unreadable:{type(exc).__name__}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label}_not_object")
    return payload


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


def _display_key(instrument_id: str, pattern: dict[str, Any]) -> str:
    points = pattern.get("points") or []
    signature_parts: list[str] = []
    for point in points:
        if not isinstance(point, dict):
            continue
        trade_date = str(point.get("trade_date") or "").strip()
        if trade_date:
            signature_parts.append(trade_date)
        elif point.get("index") is not None:
            signature_parts.append(f"i{point.get('index')}")
    point_signature = "-".join(signature_parts)
    return (
        f"{instrument_id}:{pattern.get('pattern_id')}:{pattern.get('schema')}:"
        f"{pattern.get('direction')}:S{pattern.get('scale')}:{point_signature}"
    )


def _primary_patterns(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    patterns = [
        *(analysis.get("completed") or []),
        *(analysis.get("forming") or []),
    ]
    return [
        dict(pattern)
        for pattern in patterns
        if isinstance(pattern, dict)
        and pattern.get("is_primary_identity") is not False
    ]


def _queue_items(inspection: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in ((inspection.get("indexes") or {}).get("current_queue_items") or [])
        if isinstance(item, dict)
        and str(item.get("display_key") or "")
        and str(item.get("instrument_id") or "")
    ]


def _current_snapshot_identity(inspection: dict[str, Any]) -> str:
    snapshot = inspection.get("current_product_snapshot") or {}
    identity = snapshot.get("input_identity") or {}
    value = str(identity.get("fingerprint") or "")
    if len(value) != 64:
        raise RuntimeError("nested_v3_current_input_identity_missing")
    return value


def _detail_arcname(instrument_id: str) -> str:
    safe = "".join(
        char if char.isalnum() or char in "._-" else "_"
        for char in instrument_id
    )
    return f"detail/instruments/{safe}.json"


def _nested_v3_inspection(data: bytes) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="htcn-handoff-v4-v3-") as temp:
        path = Path(temp) / "htcn-daily-handoff-v3.zip"
        path.write_bytes(data)
        checked = verify_daily_handoff_bundle_v3(path)
        if checked.status != "valid":
            raise RuntimeError(
                "nested_handoff_v3_invalid:" + ",".join(checked.errors)
            )
        return build_handoff_v3_inspection(path)


def _detail_payload(
    *,
    instrument_id: str,
    trade_date: str,
    analysis: dict[str, Any],
    required_keys: set[str],
) -> tuple[dict[str, Any], set[str]]:
    if str(analysis.get("last_trade_date") or "") != trade_date:
        raise RuntimeError("analysis_trade_date_mismatch")
    bars = analysis.get("bars")
    if not isinstance(bars, list) or not bars:
        raise RuntimeError("analysis_bars_missing")

    matched: list[dict[str, Any]] = []
    seen: set[str] = set()
    for pattern in _primary_patterns(analysis):
        key = _display_key(instrument_id, pattern)
        if key not in required_keys:
            continue
        if key in seen:
            raise RuntimeError(f"duplicate_analysis_display_key:{key}")
        seen.add(key)
        matched.append(
            {
                "display_key": key,
                "pattern": pattern,
            }
        )

    payload = {
        "schema_version": PORTABLE_DETAIL_SCHEMA_VERSION,
        "instrument_id": instrument_id,
        "trade_date": trade_date,
        "price_mode": analysis.get("price_mode"),
        "warning": analysis.get("warning"),
        "bars": bars,
        "patterns": matched,
        "display_keys": sorted(seen),
        "portable_detail_only": True,
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "changes_queue_semantics": False,
        "changes_ranking": False,
        "is_trade_instruction": False,
    }
    return payload, seen


def verify_daily_handoff_bundle_v4(
    path: str | Path,
) -> DailyHandoffV4Verification:
    bundle_path = Path(path)
    errors: list[str] = []
    warnings: list[str] = []
    manifest: dict[str, Any] | None = None
    schema_version: int | None = None
    file_count = 0
    queue_count = 0
    detail_count = 0
    error_count = 0

    if not bundle_path.is_file():
        return DailyHandoffV4Verification(
            status="invalid",
            bundle_path=str(bundle_path),
            schema_version=None,
            file_count=0,
            queue_display_key_count=0,
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

            manifest_name = "daily-handoff-v4-manifest.json"
            if manifest_name not in names:
                errors.append("manifest_missing")
            else:
                try:
                    manifest = _read_json_bytes(
                        archive.read(manifest_name),
                        label="handoff_v4_manifest",
                    )
                except RuntimeError as exc:
                    errors.append(str(exc))

            if manifest is not None:
                try:
                    schema_version = int(manifest.get("schema_version"))
                except (TypeError, ValueError):
                    errors.append("manifest_schema_invalid")
                else:
                    if schema_version != DAILY_HANDOFF_V4_SCHEMA_VERSION:
                        errors.append("manifest_schema_unsupported")

                contract = manifest.get("contract")
                if not isinstance(contract, dict):
                    errors.append("contract_missing")
                else:
                    required_false = (
                        "queue_semantics_changed",
                        "detail_changes_ranking",
                        "authoritative_evidence",
                        "writes_m4_evidence",
                        "writes_operator_queue",
                        "writes_operator_history",
                        "writes_review_journal",
                        "creates_review_events",
                        "predictive_score_used",
                        "historical_outcome_used_for_ranking",
                        "alpha_inference_allowed",
                        "is_trade_instruction",
                    )
                    if contract.get("nested_v3_unmodified") is not True:
                        errors.append("contract_nested_v3_boundary_invalid")
                    for field in required_false:
                        if contract.get(field) is not False:
                            errors.append(f"contract_boundary_invalid:{field}")

                raw_files = manifest.get("files")
                records = raw_files if isinstance(raw_files, list) else []
                if not isinstance(raw_files, list):
                    errors.append("manifest_files_invalid")
                file_count = len(records)
                by_arcname: dict[str, dict[str, Any]] = {}
                roles: dict[str, list[str]] = {}
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
                    roles.setdefault(str(record.get("role") or ""), []).append(arcname)

                actual = set(names) - {manifest_name}
                if set(by_arcname) != actual:
                    errors.append("manifest_member_set_mismatch")
                for arcname, record in by_arcname.items():
                    if arcname not in actual:
                        continue
                    data = archive.read(arcname)
                    if int(record.get("size_bytes") or -1) != len(data):
                        errors.append(f"member_size_mismatch:{arcname}")
                    if str(record.get("sha256") or "") != _sha256_bytes(data):
                        errors.append(f"member_hash_mismatch:{arcname}")

                base_members = roles.get("m5_handoff_v3_base", [])
                inspection: dict[str, Any] | None = None
                if len(base_members) != 1:
                    errors.append("nested_v3_role_invalid")
                else:
                    base_raw = archive.read(base_members[0])
                    if _sha256_bytes(base_raw) != str(
                        manifest.get("nested_v3_sha256") or ""
                    ):
                        errors.append("nested_v3_hash_mismatch")
                    try:
                        inspection = _nested_v3_inspection(base_raw)
                    except RuntimeError as exc:
                        errors.append(str(exc))

                if inspection is not None:
                    queue_items = _queue_items(inspection)
                    queue_keys = {
                        str(item["display_key"])
                        for item in queue_items
                    }
                    queue_count = len(queue_keys)
                    trade_date = str(
                        (inspection.get("summary") or {}).get("trade_date") or ""
                    )
                    expected_identity = _current_snapshot_identity(inspection)
                    if str(manifest.get("trade_date") or "") != trade_date:
                        errors.append("trade_date_mismatch")
                    if str(
                        manifest.get("input_identity_fingerprint") or ""
                    ) != expected_identity:
                        errors.append("input_identity_mismatch")
                    try:
                        declared_queue_count = int(
                            manifest.get("queue_display_key_count")
                        )
                    except (TypeError, ValueError):
                        declared_queue_count = -1
                    if declared_queue_count != queue_count:
                        errors.append("queue_display_key_count_mismatch")

                    detail_keys: set[str] = set()
                    for arcname in roles.get("m5_portable_instrument_detail", []):
                        try:
                            payload = _read_json_bytes(
                                archive.read(arcname),
                                label="portable_detail",
                            )
                        except RuntimeError as exc:
                            errors.append(str(exc))
                            continue
                        if int(payload.get("schema_version") or 0) != PORTABLE_DETAIL_SCHEMA_VERSION:
                            errors.append("detail_schema_mismatch")
                        if str(payload.get("trade_date") or "") != trade_date:
                            errors.append("detail_trade_date_mismatch")
                        if payload.get("portable_detail_only") is not True:
                            errors.append("detail_boundary_invalid")
                        for field in (
                            "authoritative_evidence",
                            "writes_m4_evidence",
                            "changes_queue_semantics",
                            "changes_ranking",
                            "is_trade_instruction",
                        ):
                            if payload.get(field) is not False:
                                errors.append(f"detail_boundary_invalid:{field}")
                        instrument_id = str(payload.get("instrument_id") or "")
                        bars = payload.get("bars")
                        if not instrument_id or not isinstance(bars, list) or not bars:
                            errors.append("detail_payload_incomplete")
                        declared_keys = {
                            str(value)
                            for value in (payload.get("display_keys") or [])
                            if value
                        }
                        actual_keys: set[str] = set()
                        for entry in payload.get("patterns") or []:
                            if not isinstance(entry, dict):
                                errors.append("detail_pattern_entry_invalid")
                                continue
                            pattern = entry.get("pattern")
                            if not isinstance(pattern, dict):
                                errors.append("detail_pattern_missing")
                                continue
                            declared = str(entry.get("display_key") or "")
                            derived = _display_key(instrument_id, pattern)
                            if declared != derived:
                                errors.append("detail_display_key_derivation_mismatch")
                                continue
                            actual_keys.add(declared)
                        if declared_keys != actual_keys:
                            errors.append("detail_declared_key_set_mismatch")
                        if not actual_keys.issubset(queue_keys):
                            errors.append("detail_key_not_in_current_queue")
                        if detail_keys.intersection(actual_keys):
                            errors.append("duplicate_detail_display_key")
                        detail_keys.update(actual_keys)

                    error_members = roles.get("m5_portable_detail_errors", [])
                    error_keys: set[str] = set()
                    if len(error_members) != 1:
                        errors.append("detail_errors_role_invalid")
                    else:
                        try:
                            error_payload = _read_json_bytes(
                                archive.read(error_members[0]),
                                label="portable_detail_errors",
                            )
                        except RuntimeError as exc:
                            errors.append(str(exc))
                        else:
                            for item in error_payload.get("items") or []:
                                if not isinstance(item, dict):
                                    errors.append("detail_error_record_invalid")
                                    continue
                                key = str(item.get("display_key") or "")
                                if key:
                                    error_keys.add(key)
                            if not error_keys.issubset(queue_keys):
                                errors.append("detail_error_key_not_in_current_queue")

                    if detail_keys.intersection(error_keys):
                        errors.append("detail_and_error_key_overlap")
                    if detail_keys.union(error_keys) != queue_keys:
                        errors.append("detail_coverage_not_exhaustive")
                    detail_count = len(detail_keys)
                    error_count = len(error_keys)
                    try:
                        declared_detail_count = int(
                            manifest.get("detail_display_key_count")
                        )
                    except (TypeError, ValueError):
                        declared_detail_count = -1
                    try:
                        declared_error_count = int(
                            manifest.get("error_display_key_count")
                        )
                    except (TypeError, ValueError):
                        declared_error_count = -1
                    if declared_detail_count != detail_count:
                        errors.append("detail_display_key_count_mismatch")
                    if declared_error_count != error_count:
                        errors.append("error_display_key_count_mismatch")
                    expected_status = (
                        "complete_detail_transport"
                        if error_count == 0
                        else "detail_transport_degraded"
                    )
                    if manifest.get("status") != expected_status:
                        errors.append("detail_transport_status_mismatch")
    except (OSError, zipfile.BadZipFile, ValueError):
        errors.append("bundle_not_readable_zip")

    return DailyHandoffV4Verification(
        status="valid" if not errors else "invalid",
        bundle_path=str(bundle_path),
        schema_version=schema_version,
        file_count=file_count,
        queue_display_key_count=queue_count,
        detail_display_key_count=detail_count,
        error_display_key_count=error_count,
        errors=tuple(errors),
        warnings=tuple(warnings),
        manifest=manifest,
    )


def build_daily_handoff_bundle_v4(
    *,
    v3_bundle: str | Path,
    analysis_provider: PortableDetailAnalysisProvider,
    current_input_identity_fingerprint: str,
    output: str | Path,
    bars: int = DEFAULT_BARS,
    scales: tuple[int, ...] = DEFAULT_SCALES,
) -> dict[str, Any]:
    source_path = Path(v3_bundle)
    source_checked = verify_daily_handoff_bundle_v3(source_path)
    if source_checked.status != "valid":
        raise RuntimeError(
            "handoff_v3_invalid:" + ",".join(source_checked.errors)
        )
    source_bytes = source_path.read_bytes()
    inspection = build_handoff_v3_inspection(source_path)
    queue_items = _queue_items(inspection)
    trade_date = str((inspection.get("summary") or {}).get("trade_date") or "")
    if not trade_date:
        raise RuntimeError("handoff_v3_trade_date_missing")

    source_identity = _current_snapshot_identity(inspection)
    if str(current_input_identity_fingerprint) != source_identity:
        raise RuntimeError("portable_detail_input_identity_mismatch")

    required_by_instrument: dict[str, set[str]] = {}
    for item in queue_items:
        required_by_instrument.setdefault(
            str(item["instrument_id"]),
            set(),
        ).add(str(item["display_key"]))

    members: list[tuple[str, bytes, str]] = [
        (
            "base/htcn-daily-handoff-v3.zip",
            source_bytes,
            "m5_handoff_v3_base",
        )
    ]
    errors: list[dict[str, str]] = []
    matched_keys: set[str] = set()

    for instrument_id in sorted(required_by_instrument):
        required = required_by_instrument[instrument_id]
        try:
            analysis = analysis_provider.analyze(
                instrument_id,
                bars=int(bars),
                scales=tuple(scales),
            )
            detail, seen = _detail_payload(
                instrument_id=instrument_id,
                trade_date=trade_date,
                analysis=analysis,
                required_keys=required,
            )
        except Exception as exc:
            for key in sorted(required):
                errors.append(
                    {
                        "display_key": key,
                        "instrument_id": instrument_id,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
            continue

        missing = required.difference(seen)
        for key in sorted(missing):
            errors.append(
                {
                    "display_key": key,
                    "instrument_id": instrument_id,
                    "error": "current_queue_pattern_not_found_in_exact_analysis",
                }
            )
        matched_keys.update(seen)
        if seen:
            members.append(
                (
                    _detail_arcname(instrument_id),
                    _canonical_json_bytes(detail),
                    "m5_portable_instrument_detail",
                )
            )

    error_payload = {
        "schema_version": 1,
        "trade_date": trade_date,
        "items": errors,
        "error_display_key_count": len(errors),
        "portable_detail_only": True,
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "changes_queue_semantics": False,
        "changes_ranking": False,
        "is_trade_instruction": False,
    }
    members.append(
        (
            "detail/errors.json",
            _canonical_json_bytes(error_payload),
            "m5_portable_detail_errors",
        )
    )

    queue_keys = {
        str(item["display_key"])
        for item in queue_items
    }
    error_keys = {str(item["display_key"]) for item in errors}
    if matched_keys.intersection(error_keys):
        raise RuntimeError("portable_detail_internal_overlap")
    if matched_keys.union(error_keys) != queue_keys:
        raise RuntimeError("portable_detail_internal_coverage_failure")

    status = (
        "complete_detail_transport"
        if not errors
        else "detail_transport_degraded"
    )
    records = [
        {
            "arcname": arcname,
            "role": role,
            "size_bytes": len(data),
            "sha256": _sha256_bytes(data),
        }
        for arcname, data, role in members
    ]
    manifest = {
        "schema_version": DAILY_HANDOFF_V4_SCHEMA_VERSION,
        "status": status,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "contract": HandoffV4Contract().as_payload(),
        "trade_date": trade_date,
        "bars": int(bars),
        "scales": list(scales),
        "input_identity_fingerprint": source_identity,
        "nested_v3_sha256": _sha256_bytes(source_bytes),
        "nested_v3_schema_version": 3,
        "queue_display_key_count": len(queue_keys),
        "detail_display_key_count": len(matched_keys),
        "error_display_key_count": len(error_keys),
        "files": records,
    }

    output_path = Path(output)
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
            "daily-handoff-v4-manifest.json",
            _canonical_json_bytes(manifest),
        )
        for arcname, data, _ in members:
            archive.writestr(arcname, data)

    checked = verify_daily_handoff_bundle_v4(tmp)
    if checked.status != "valid":
        tmp.unlink(missing_ok=True)
        raise RuntimeError(
            "daily_handoff_v4_verification_failed:"
            + ",".join(checked.errors)
        )
    tmp.replace(output_path)
    final = verify_daily_handoff_bundle_v4(output_path)
    if final.status != "valid":
        raise RuntimeError(
            "daily_handoff_v4_post_replace_verification_failed:"
            + ",".join(final.errors)
        )

    return {
        **manifest,
        "output": str(output_path),
        "bundle_size_bytes": output_path.stat().st_size,
        "bundle_sha256": _sha256_path(output_path),
        "verification": final.as_payload(),
    }
