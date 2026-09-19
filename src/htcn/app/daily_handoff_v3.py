from __future__ import annotations

import io
import json
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any

from htcn.app.daily_handoff import (
    build_daily_handoff_bundle,
    verify_daily_handoff_bundle,
)
from htcn.app.daily_review_digest import build_daily_review_digest
from htcn.app.operator_delta import build_operator_delta
from htcn.app.operator_history import (
    OperatorHistoryContract,
    query_operator_history,
    verify_operator_history_record,
)
from htcn.app.operator_process_lock import OperatorCacheProcessLock
from htcn.app.review_followup_journal import (
    build_latest_review_session,
    query_review_journal,
    verify_review_journal_event,
)

DAILY_HANDOFF_V3_SCHEMA_VERSION = 3
BASE_V2_SCHEMA_VERSION = 2
JOURNAL_QUERY_LIMIT = 10_000_000


@dataclass(frozen=True, slots=True)
class DailyHandoffV3Verification:
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


def _read_json_bytes(data: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{label}_unreadable:{type(exc).__name__}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{label}_not_object")
    return value


def _read_json_path(path: Path, *, label: str) -> dict[str, Any]:
    try:
        return _read_json_bytes(path.read_bytes(), label=label)
    except OSError as exc:
        raise RuntimeError(f"{label}_unreadable:{type(exc).__name__}") from exc


def _safe_arcname(name: str) -> bool:
    if not name or "\\" in name:
        return False
    path = PurePosixPath(name)
    if path.is_absolute():
        return False
    return all(part not in ("", ".", "..") for part in path.parts)


def _resolve_repo_path(repo: Path, value: str | Path, *, label: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = repo / candidate
    resolved = candidate.resolve()
    if resolved != repo and repo not in resolved.parents:
        raise RuntimeError(f"{label}_outside_repository")
    return resolved


def _repo_relative(repo: Path, path: Path, *, label: str) -> str:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError as exc:
        raise RuntimeError(f"{label}_outside_repository") from exc


def _pipeline_source(
    repo: Path,
    pipeline_summary: dict[str, Any],
) -> tuple[Path, bytes]:
    artifacts = pipeline_summary.get("artifacts")
    raw = "artifacts/reports/m5-daily-close-pipeline.json"
    if isinstance(artifacts, dict) and artifacts.get("pipeline_report"):
        raw = str(artifacts["pipeline_report"])
    path = _resolve_repo_path(repo, raw, label="pipeline_report")
    if not path.is_file():
        raise RuntimeError("pipeline_report_missing")
    raw_bytes = path.read_bytes()
    if _read_json_bytes(raw_bytes, label="pipeline_report") != pipeline_summary:
        raise RuntimeError("pipeline_report_payload_mismatch")
    return path, raw_bytes


def _verify_nested_v2_bytes(
    data: bytes,
) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    with tempfile.TemporaryDirectory(prefix="htcn-handoff-v2-") as temp:
        path = Path(temp) / "htcn-daily-handoff-v2.zip"
        path.write_bytes(data)
        checked = verify_daily_handoff_bundle(path)
        if checked.status != "valid" or not isinstance(checked.manifest, dict):
            raise RuntimeError(
                "nested_handoff_v2_invalid:"
                + ",".join(checked.errors)
            )
    with zipfile.ZipFile(io.BytesIO(data), "r") as archive:
        manifest = _read_json_bytes(
            archive.read("daily-handoff-manifest.json"),
            label="nested_v2_manifest",
        )
        pipeline_raw = archive.read(
            "pipeline/m5-daily-close-pipeline.json"
        )
        pipeline = _read_json_bytes(
            pipeline_raw,
            label="nested_v2_pipeline",
        )
    return manifest, pipeline, pipeline_raw


def _history_payload_from_record(record: dict[str, Any]) -> dict[str, Any]:
    queue = record.get("queue_snapshot") or {}
    delta = record.get("delta") or {}
    return {
        "schema_version": 1,
        "contract": OperatorHistoryContract().as_payload(),
        "filter": {},
        "observation_count": 1,
        "observations": [{
            "trade_date": record.get("trade_date"),
            "observation_id": record.get("observation_id"),
            "revision_ordinal": record.get("revision_ordinal"),
            "source_generated_at_utc": (
                (record.get("source") or {}).get("generated_at_utc")
            ),
            "previous_recorded_trade_date": record.get(
                "previous_recorded_trade_date"
            ),
            "queue_candidate_count": len(queue.get("items") or []),
            "delta_total_change_count": int(delta.get("change_count") or 0),
            "item_count": len(queue.get("items") or []),
            "items": queue.get("items") or [],
            "change_count": len(delta.get("changes") or []),
            "changes": delta.get("changes") or [],
            "delta_status": delta.get("status"),
            "comparison_incomplete_instruments": delta.get(
                "comparison_incomplete_instruments"
            ) or [],
        }],
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "historical_outcome_used_for_ranking": False,
        "alpha_inference_allowed": False,
        "is_trade_instruction": False,
    }


def _digest_core(payload: dict[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result.pop("generated_at_utc", None)
    result.pop("history_root", None)
    result.pop("report_path", None)
    return result


def _session_digest_projection(payload: dict[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    for key in (
        "session_contract",
        "review_state_counts",
        "active_follow_ups",
        "active_follow_up_count",
        "active_follow_up_in_current_digest_count",
        "review_workflow_mutates_source",
    ):
        result.pop(key, None)

    sections: list[dict[str, Any]] = []
    for raw_section in result.get("workflow_sections") or []:
        section = dict(raw_section)
        items = []
        for raw_item in section.get("items") or []:
            item = dict(raw_item)
            item.pop("review", None)
            items.append(item)
        section["items"] = items
        sections.append(section)
    result["workflow_sections"] = sections
    return result


def _latest_history_record(
    repo: Path,
    *,
    trade_date: str,
) -> tuple[Path, bytes, dict[str, Any]]:
    history_root = repo / "data" / "product" / "m5" / "operator_history"
    queried = query_operator_history(
        history_root=history_root,
        start_trade_date=trade_date,
        end_trade_date=trade_date,
        latest_revision_per_day=True,
        summary_only=False,
        limit=1,
    )
    observations = list(queried.get("observations") or [])
    if len(observations) != 1:
        raise RuntimeError("current_history_observation_missing")
    observation_id = str(observations[0].get("observation_id") or "")
    path = history_root / trade_date / f"{observation_id}.json"
    checked = verify_operator_history_record(path)
    if checked.get("status") != "valid":
        raise RuntimeError(
            "current_history_record_invalid:"
            + ",".join(checked.get("errors") or [])
        )
    record = checked.get("record")
    if not isinstance(record, dict):
        raise RuntimeError("current_history_record_missing")
    return path, path.read_bytes(), record


def _history_link_record(
    history_root: Path,
    *,
    trade_date: str,
    observation_id: str,
    label: str,
) -> tuple[Path, bytes, dict[str, Any]]:
    path = history_root / trade_date / f"{observation_id}.json"
    checked = verify_operator_history_record(path)
    if checked.get("status") != "valid":
        raise RuntimeError(
            f"{label}_invalid:" + ",".join(checked.get("errors") or [])
        )
    record = checked.get("record")
    if not isinstance(record, dict):
        raise RuntimeError(f"{label}_missing")
    return path, path.read_bytes(), record


def _load_valid_digest(
    repo: Path,
    *,
    current_record: dict[str, Any],
) -> tuple[Path, bytes, dict[str, Any]]:
    path = repo / "artifacts" / "reports" / "m5-daily-review-digest.json"
    if not path.is_file():
        raise RuntimeError("daily_review_digest_missing")
    data = path.read_bytes()
    payload = _read_json_bytes(data, label="daily_review_digest")
    expected = build_daily_review_digest(
        _history_payload_from_record(current_record)
    )
    if _digest_core(payload) != expected:
        raise RuntimeError("daily_review_digest_source_mismatch")
    if payload.get("review_ready") is not True:
        raise RuntimeError("daily_review_digest_not_ready")
    return path, data, payload


def _review_root_event_ids(session: dict[str, Any]) -> set[str]:
    roots: set[str] = set()
    for section in session.get("workflow_sections") or []:
        for item in section.get("items") or []:
            review = item.get("review") or {}
            for field in (
                "current_event_id",
                "active_follow_up_event_id",
            ):
                value = str(review.get(field) or "")
                if value:
                    roots.add(value)
    for item in session.get("active_follow_ups") or []:
        value = str(item.get("event_id") or "")
        if value:
            roots.add(value)
    return roots


def _review_event_closure(
    *,
    journal_root: Path,
    session: dict[str, Any],
) -> list[tuple[Path, bytes, dict[str, Any]]]:
    queried = query_review_journal(
        journal_root=journal_root,
        limit=JOURNAL_QUERY_LIMIT,
    )
    events = list(queried.get("events") or [])
    by_id = {
        str(event.get("event_id") or ""): dict(event)
        for event in events
    }
    roots = _review_root_event_ids(session)
    closure: set[str] = set()
    pending = list(roots)
    while pending:
        event_id = pending.pop()
        if event_id in closure:
            continue
        event = by_id.get(event_id)
        if event is None:
            raise RuntimeError(
                f"review_session_event_missing:{event_id}"
            )
        closure.add(event_id)
        for field in (
            "previous_binding_event_id",
            "previous_display_key_event_id",
        ):
            previous = str(event.get(field) or "")
            if previous and previous not in closure:
                pending.append(previous)

    result: list[tuple[Path, bytes, dict[str, Any]]] = []
    for event_id in sorted(closure):
        event = by_id[event_id]
        source = event.get("source") or {}
        trade_date = str(source.get("trade_date") or "")
        binding_id = str(event.get("binding_id") or "")
        path = (
            journal_root
            / trade_date
            / binding_id
            / f"{event_id}.json"
        )
        checked = verify_review_journal_event(path)
        if checked.get("status") != "valid":
            raise RuntimeError(
                "review_session_event_invalid:"
                + ",".join(checked.get("errors") or [])
            )
        result.append((path, path.read_bytes(), event))
    return result


def _build_review_session_export(
    repo: Path,
    *,
    current_record: dict[str, Any],
    digest_payload: dict[str, Any],
) -> tuple[bytes, dict[str, Any], list[tuple[Path, bytes, dict[str, Any]]]]:
    history_root = repo / "data" / "product" / "m5" / "operator_history"
    journal_root = repo / "data" / "product" / "m5" / "review_journal"
    lock = OperatorCacheProcessLock(
        journal_root / ".locks" / "review-journal.lock",
        timeout_seconds=30.0,
    )
    lock.acquire()
    try:
        session = build_latest_review_session(
            history_root=history_root,
            journal_root=journal_root,
        )
        expected_digest = build_daily_review_digest(
            _history_payload_from_record(current_record)
        )
        if _session_digest_projection(session) != expected_digest:
            raise RuntimeError("review_session_digest_projection_mismatch")
        if str(session.get("source_observation_id") or "") != str(
            current_record.get("observation_id") or ""
        ):
            raise RuntimeError("review_session_observation_mismatch")
        if _digest_core(digest_payload) != expected_digest:
            raise RuntimeError("review_session_digest_artifact_mismatch")
        events = _review_event_closure(
            journal_root=journal_root,
            session=session,
        )
    finally:
        lock.release()
    return _canonical_json_bytes(session), session, events


def _event_arcname(event: dict[str, Any]) -> str:
    source = event.get("source") or {}
    return (
        "m5/review_journal/"
        f"{source.get('trade_date')}/"
        f"{event.get('binding_id')}/"
        f"{event.get('event_id')}.json"
    )


def _verify_history_member_bytes(
    data: bytes,
    *,
    arcname: str,
    temp_root: Path,
) -> dict[str, Any]:
    path = temp_root / arcname
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    checked = verify_operator_history_record(path)
    if checked.get("status") != "valid":
        raise RuntimeError(
            "transport_history_record_invalid:"
            + ",".join(checked.get("errors") or [])
        )
    record = checked.get("record")
    if not isinstance(record, dict):
        raise RuntimeError("transport_history_record_missing")
    return record


def _verify_review_event_member_bytes(
    data: bytes,
    *,
    arcname: str,
    temp_root: Path,
) -> dict[str, Any]:
    path = temp_root / arcname
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    checked = verify_review_journal_event(path)
    if checked.get("status") != "valid":
        raise RuntimeError(
            "transport_review_event_invalid:"
            + ",".join(checked.get("errors") or [])
        )
    event = checked.get("event")
    if not isinstance(event, dict):
        raise RuntimeError("transport_review_event_missing")
    return event


def verify_daily_handoff_bundle_v3(
    path: str | Path,
) -> DailyHandoffV3Verification:
    bundle_path = Path(path)
    errors: list[str] = []
    warnings: list[str] = []
    manifest: dict[str, Any] | None = None
    schema_version: int | None = None
    file_count = 0

    if not bundle_path.is_file():
        return DailyHandoffV3Verification(
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

            manifest_name = "daily-handoff-v3-manifest.json"
            if manifest_name not in names:
                errors.append("manifest_missing")
            else:
                try:
                    loaded = _read_json_bytes(
                        archive.read(manifest_name),
                        label="handoff_v3_manifest",
                    )
                except RuntimeError as exc:
                    errors.append(str(exc))
                else:
                    manifest = loaded

            if manifest is not None:
                try:
                    schema_version = int(manifest.get("schema_version"))
                except (TypeError, ValueError):
                    errors.append("manifest_schema_invalid")
                else:
                    if schema_version != DAILY_HANDOFF_V3_SCHEMA_VERSION:
                        errors.append("manifest_schema_unsupported")

                required_true = ("transport_only",)
                required_false = (
                    "authoritative_evidence",
                    "writes_m4_evidence",
                    "is_trade_instruction",
                    "alpha_inference_allowed",
                    "predictive_score_used",
                    "historical_outcome_used_for_ranking",
                    "review_state_changes_product_ranking",
                )
                for field in required_true:
                    if manifest.get(field) is not True:
                        errors.append(f"manifest_boundary_invalid:{field}")
                for field in required_false:
                    if manifest.get(field) is not False:
                        errors.append(f"manifest_boundary_invalid:{field}")

                raw_records = manifest.get("files")
                records = raw_records if isinstance(raw_records, list) else []
                if not isinstance(raw_records, list):
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
                    roles.setdefault(
                        str(record.get("role") or ""),
                        [],
                    ).append(arcname)

                actual = set(names) - {manifest_name}
                if set(by_arcname) != actual:
                    errors.append("manifest_member_set_mismatch")
                for arcname, record in by_arcname.items():
                    if arcname not in actual:
                        continue
                    data = archive.read(arcname)
                    try:
                        size = int(record.get("size_bytes"))
                    except (TypeError, ValueError):
                        size = -1
                    if size != len(data):
                        errors.append(f"member_size_mismatch:{arcname}")
                    if str(record.get("sha256") or "") != _sha256_bytes(data):
                        errors.append(f"member_hash_mismatch:{arcname}")

                base_members = roles.get("m5_handoff_v2_base", [])
                base_manifest: dict[str, Any] | None = None
                pipeline_payload: dict[str, Any] | None = None
                if len(base_members) != 1:
                    errors.append("nested_v2_role_invalid")
                else:
                    try:
                        (
                            base_manifest,
                            pipeline_payload,
                            nested_pipeline_raw,
                        ) = _verify_nested_v2_bytes(
                            archive.read(base_members[0])
                        )
                    except RuntimeError as exc:
                        errors.append(str(exc))

                if base_manifest is not None and pipeline_payload is not None:
                    base_binding = manifest.get("nested_v2_binding")
                    if not isinstance(base_binding, dict):
                        errors.append("nested_v2_binding_missing")
                    else:
                        if int(
                            base_binding.get("schema_version") or 0
                        ) != BASE_V2_SCHEMA_VERSION:
                            errors.append(
                                "nested_v2_binding_schema_mismatch"
                            )
                        if base_binding.get("status") != base_manifest.get(
                            "status"
                        ):
                            errors.append(
                                "nested_v2_binding_status_mismatch"
                            )
                        if base_binding.get(
                            "product_binding"
                        ) != base_manifest.get("product_binding"):
                            errors.append(
                                "nested_v2_binding_product_mismatch"
                            )
                        if len(base_members) == 1:
                            base_raw = archive.read(base_members[0])
                            if _sha256_bytes(base_raw) != str(
                                base_binding.get("bundle_sha256") or ""
                            ):
                                errors.append(
                                    "nested_v2_binding_hash_mismatch"
                                )
                    if int(base_manifest.get("schema_version") or 0) != BASE_V2_SCHEMA_VERSION:
                        errors.append("nested_v2_schema_mismatch")
                    if str(
                        manifest.get("pipeline_report_sha256") or ""
                    ) != _sha256_bytes(nested_pipeline_raw):
                        errors.append("pipeline_report_hash_mismatch")
                    for field in (
                        "m5_product_ready",
                        "m4_research_ready",
                    ):
                        if manifest.get(field) != base_manifest.get(field):
                            errors.append(f"nested_v2_{field}_mismatch")
                    for field in (
                        "m5_history_ready",
                        "m5_review_digest_ready",
                    ):
                        if manifest.get(field) != pipeline_payload.get(field):
                            errors.append(f"pipeline_{field}_mismatch")

                    product_ready = manifest.get("m5_product_ready") is True
                    history_ready = manifest.get("m5_history_ready") is True
                    digest_ready = (
                        manifest.get("m5_review_digest_ready") is True
                    )
                    if digest_ready and not history_ready:
                        errors.append("digest_ready_without_history_ready")
                    if history_ready and not product_ready:
                        errors.append("history_ready_without_product_ready")

                    current_history: dict[str, Any] | None = None
                    with tempfile.TemporaryDirectory(
                        prefix="htcn-handoff-v3-verify-"
                    ) as temp:
                        temp_root = Path(temp)

                        current_members = roles.get(
                            "m5_current_history_record", []
                        )
                        if history_ready:
                            if len(current_members) != 1:
                                errors.append(
                                    "current_history_role_invalid"
                                )
                            else:
                                arcname = current_members[0]
                                try:
                                    current_history = (
                                        _verify_history_member_bytes(
                                            archive.read(arcname),
                                            arcname=arcname,
                                            temp_root=temp_root,
                                        )
                                    )
                                except RuntimeError as exc:
                                    errors.append(str(exc))
                        elif current_members:
                            errors.append(
                                "history_member_present_when_not_ready"
                            )

                        if current_history is not None:
                            binding = manifest.get("history_binding")
                            if not isinstance(binding, dict):
                                errors.append("history_binding_missing")
                            else:
                                current_raw = archive.read(
                                    current_members[0]
                                )
                                if _sha256_bytes(current_raw) != str(
                                    binding.get("record_sha256") or ""
                                ):
                                    errors.append(
                                        "history_binding_hash_mismatch"
                                    )
                                if str(
                                    current_history.get(
                                        "observation_id"
                                    ) or ""
                                ) != str(
                                    binding.get("observation_id") or ""
                                ):
                                    errors.append(
                                        "history_binding_observation_mismatch"
                                    )
                                if str(
                                    current_history.get("trade_date") or ""
                                ) != str(binding.get("trade_date") or ""):
                                    errors.append(
                                        "history_binding_trade_date_mismatch"
                                    )

                            product_binding = base_manifest.get(
                                "product_binding"
                            )
                            source = current_history.get("source") or {}
                            if not isinstance(product_binding, dict):
                                errors.append(
                                    "nested_v2_product_binding_missing"
                                )
                            else:
                                if str(source.get("report_sha256") or "") != str(
                                    product_binding.get(
                                        "report_sha256"
                                    ) or ""
                                ):
                                    errors.append(
                                        "history_product_report_hash_mismatch"
                                    )
                                if str(
                                    source.get("snapshot_sha256") or ""
                                ) != str(
                                    product_binding.get(
                                        "snapshot_sha256"
                                    ) or ""
                                ):
                                    errors.append(
                                        "history_product_snapshot_hash_mismatch"
                                    )
                                if str(
                                    current_history.get("trade_date") or ""
                                ) != str(
                                    product_binding.get("trade_date") or ""
                                ):
                                    errors.append(
                                        "history_product_trade_date_mismatch"
                                    )

                            previous_date = current_history.get(
                                "previous_recorded_trade_date"
                            )
                            previous_id = current_history.get(
                                "previous_observation_id"
                            )
                            previous_members = roles.get(
                                "m5_previous_history_record", []
                            )
                            if previous_date is None:
                                if previous_members:
                                    errors.append(
                                        "unexpected_previous_history_record"
                                    )
                                delta = current_history.get("delta") or {}
                                if delta.get("status") != (
                                    "baseline_no_previous_observation"
                                ):
                                    errors.append(
                                        "history_baseline_status_mismatch"
                                    )
                            else:
                                if len(previous_members) != 1:
                                    errors.append(
                                        "previous_history_role_invalid"
                                    )
                                else:
                                    arcname = previous_members[0]
                                    try:
                                        previous = (
                                            _verify_history_member_bytes(
                                                archive.read(arcname),
                                                arcname=arcname,
                                                temp_root=temp_root,
                                            )
                                        )
                                    except RuntimeError as exc:
                                        errors.append(str(exc))
                                    else:
                                        if str(
                                            previous.get("observation_id")
                                            or ""
                                        ) != str(previous_id or ""):
                                            errors.append(
                                                "previous_history_id_mismatch"
                                            )
                                        if str(
                                            previous.get("trade_date") or ""
                                        ) != str(previous_date or ""):
                                            errors.append(
                                                "previous_history_date_mismatch"
                                            )
                                        try:
                                            expected_delta = (
                                                build_operator_delta(
                                                    previous.get(
                                                        "queue_snapshot"
                                                    ) or {},
                                                    current_history.get(
                                                        "queue_snapshot"
                                                    ) or {},
                                                )
                                            )
                                        except ValueError as exc:
                                            errors.append(
                                                "history_delta_rebuild_failed:"
                                                + str(exc)
                                            )
                                        else:
                                            if expected_delta != current_history.get(
                                                "delta"
                                            ):
                                                errors.append(
                                                    "history_delta_mismatch"
                                                )

                            previous_same = current_history.get(
                                "previous_same_day_observation_id"
                            )
                            same_members = roles.get(
                                "m5_previous_same_day_history_record",
                                [],
                            )
                            if previous_same is None:
                                if same_members:
                                    errors.append(
                                        "unexpected_previous_same_day_record"
                                    )
                            else:
                                if len(same_members) != 1:
                                    errors.append(
                                        "previous_same_day_role_invalid"
                                    )
                                else:
                                    arcname = same_members[0]
                                    try:
                                        previous_same_record = (
                                            _verify_history_member_bytes(
                                                archive.read(arcname),
                                                arcname=arcname,
                                                temp_root=temp_root,
                                            )
                                        )
                                    except RuntimeError as exc:
                                        errors.append(str(exc))
                                    else:
                                        if str(
                                            previous_same_record.get(
                                                "observation_id"
                                            ) or ""
                                        ) != str(previous_same or ""):
                                            errors.append(
                                                "previous_same_day_id_mismatch"
                                            )
                                        if str(
                                            previous_same_record.get(
                                                "trade_date"
                                            ) or ""
                                        ) != str(
                                            current_history.get(
                                                "trade_date"
                                            ) or ""
                                        ):
                                            errors.append(
                                                "previous_same_day_date_mismatch"
                                            )

                        digest_members = roles.get(
                            "m5_daily_review_digest", []
                        )
                        digest_payload: dict[str, Any] | None = None
                        expected_digest: dict[str, Any] | None = None
                        if digest_ready:
                            if current_history is None:
                                errors.append(
                                    "digest_without_current_history"
                                )
                            if len(digest_members) != 1:
                                errors.append("digest_role_invalid")
                            elif current_history is not None:
                                try:
                                    digest_payload = _read_json_bytes(
                                        archive.read(digest_members[0]),
                                        label="transport_review_digest",
                                    )
                                except RuntimeError as exc:
                                    errors.append(str(exc))
                                else:
                                    expected_digest = build_daily_review_digest(
                                        _history_payload_from_record(
                                            current_history
                                        )
                                    )
                                    if _digest_core(
                                        digest_payload
                                    ) != expected_digest:
                                        errors.append(
                                            "transport_digest_source_mismatch"
                                        )
                                    digest_binding = manifest.get(
                                        "digest_binding"
                                    )
                                    if not isinstance(
                                        digest_binding, dict
                                    ):
                                        errors.append(
                                            "digest_binding_missing"
                                        )
                                    else:
                                        raw = archive.read(
                                            digest_members[0]
                                        )
                                        if _sha256_bytes(raw) != str(
                                            digest_binding.get(
                                                "digest_sha256"
                                            ) or ""
                                        ):
                                            errors.append(
                                                "digest_binding_hash_mismatch"
                                            )
                        elif digest_members:
                            errors.append(
                                "digest_member_present_when_not_ready"
                            )

                        session_members = roles.get(
                            "m5_review_session_snapshot", []
                        )
                        event_members = roles.get(
                            "m5_review_journal_event", []
                        )
                        if digest_ready:
                            if len(session_members) != 1:
                                errors.append(
                                    "review_session_role_invalid"
                                )
                            elif expected_digest is not None:
                                try:
                                    session = _read_json_bytes(
                                        archive.read(session_members[0]),
                                        label="transport_review_session",
                                    )
                                except RuntimeError as exc:
                                    errors.append(str(exc))
                                else:
                                    if _session_digest_projection(
                                        session
                                    ) != expected_digest:
                                        errors.append(
                                            "review_session_digest_mismatch"
                                        )
                                    session_contract = session.get(
                                        "session_contract"
                                    )
                                    if not isinstance(
                                        session_contract, dict
                                    ):
                                        errors.append(
                                            "review_session_contract_missing"
                                        )
                                    else:
                                        for field in (
                                            "authoritative_transition",
                                            "authoritative_evidence",
                                            "writes_m4_evidence",
                                            "predictive_score_used",
                                            "historical_outcome_used_for_ranking",
                                            "alpha_inference_allowed",
                                            "is_trade_instruction",
                                            "mutates_operator_queue",
                                            "mutates_operator_history",
                                            "mutates_action_state",
                                            "mutates_lifecycle",
                                            "mutates_harmonic_identity",
                                            "mutates_source_raw_prz",
                                        ):
                                            if session_contract.get(
                                                field
                                            ) is not False:
                                                errors.append(
                                                    "review_session_boundary_invalid:"
                                                    + field
                                                )

                                    events_by_id: dict[
                                        str, dict[str, Any]
                                    ] = {}
                                    for arcname in event_members:
                                        try:
                                            event = (
                                                _verify_review_event_member_bytes(
                                                    archive.read(arcname),
                                                    arcname=arcname,
                                                    temp_root=temp_root,
                                                )
                                            )
                                        except RuntimeError as exc:
                                            errors.append(str(exc))
                                            continue
                                        event_id = str(
                                            event.get("event_id") or ""
                                        )
                                        if event_id in events_by_id:
                                            errors.append(
                                                "duplicate_review_event_id"
                                            )
                                        events_by_id[event_id] = event

                                    roots = _review_root_event_ids(session)
                                    visited: set[str] = set()
                                    pending = list(roots)
                                    while pending:
                                        event_id = pending.pop()
                                        if event_id in visited:
                                            continue
                                        event = events_by_id.get(
                                            event_id
                                        )
                                        if event is None:
                                            errors.append(
                                                "review_event_closure_missing:"
                                                + event_id
                                            )
                                            continue
                                        visited.add(event_id)
                                        for field in (
                                            "previous_binding_event_id",
                                            "previous_display_key_event_id",
                                        ):
                                            previous = str(
                                                event.get(field) or ""
                                            )
                                            if (
                                                previous
                                                and previous not in visited
                                            ):
                                                pending.append(previous)
                                    if visited != set(events_by_id):
                                        errors.append(
                                            "review_event_closure_has_extras"
                                        )

                                    for section in session.get(
                                        "workflow_sections"
                                    ) or []:
                                        for item in section.get(
                                            "items"
                                        ) or []:
                                            review = item.get(
                                                "review"
                                            ) or {}
                                            display_key = str(
                                                item.get(
                                                    "display_key"
                                                ) or ""
                                            )
                                            current_event_id = str(
                                                review.get(
                                                    "current_event_id"
                                                ) or ""
                                            )
                                            if current_event_id:
                                                event = events_by_id.get(
                                                    current_event_id
                                                )
                                                if event is not None:
                                                    source = event.get(
                                                        "source"
                                                    ) or {}
                                                    if str(
                                                        source.get(
                                                            "observation_id"
                                                        ) or ""
                                                    ) != str(
                                                        session.get(
                                                            "source_observation_id"
                                                        ) or ""
                                                    ):
                                                        errors.append(
                                                            "current_review_event_observation_mismatch"
                                                        )
                                                    if str(
                                                        source.get(
                                                            "display_key"
                                                        ) or ""
                                                    ) != display_key:
                                                        errors.append(
                                                            "current_review_event_key_mismatch"
                                                        )
                                                    if event.get(
                                                        "review_state"
                                                    ) != review.get(
                                                        "review_state"
                                                    ):
                                                        errors.append(
                                                            "current_review_event_state_mismatch"
                                                        )
                                                    if str(
                                                        event.get(
                                                            "note"
                                                        ) or ""
                                                    ) != str(
                                                        review.get(
                                                            "note"
                                                        ) or ""
                                                    ):
                                                        errors.append(
                                                            "current_review_event_note_mismatch"
                                                        )

                                    for active in session.get(
                                        "active_follow_ups"
                                    ) or []:
                                        event_id = str(
                                            active.get("event_id") or ""
                                        )
                                        event = events_by_id.get(
                                            event_id
                                        )
                                        if event is not None:
                                            source = event.get(
                                                "source"
                                            ) or {}
                                            if event.get(
                                                "review_state"
                                            ) != "follow_up":
                                                errors.append(
                                                    "active_follow_up_event_state_mismatch"
                                                )
                                            for source_field, active_field in (
                                                (
                                                    "display_key",
                                                    "display_key",
                                                ),
                                                (
                                                    "instrument_id",
                                                    "instrument_id",
                                                ),
                                                (
                                                    "observation_id",
                                                    "source_observation_id",
                                                ),
                                                (
                                                    "trade_date",
                                                    "source_trade_date",
                                                ),
                                            ):
                                                if str(
                                                    source.get(
                                                        source_field
                                                    ) or ""
                                                ) != str(
                                                    active.get(
                                                        active_field
                                                    ) or ""
                                                ):
                                                    errors.append(
                                                        "active_follow_up_source_mismatch:"
                                                        + source_field
                                                    )

                                    review_binding = manifest.get(
                                        "review_session_binding"
                                    )
                                    if not isinstance(
                                        review_binding, dict
                                    ):
                                        errors.append(
                                            "review_session_binding_missing"
                                        )
                                    else:
                                        raw = archive.read(
                                            session_members[0]
                                        )
                                        if _sha256_bytes(raw) != str(
                                            review_binding.get(
                                                "session_sha256"
                                            ) or ""
                                        ):
                                            errors.append(
                                                "review_session_binding_hash_mismatch"
                                            )
                                        if int(
                                            review_binding.get(
                                                "journal_event_count"
                                            ) or 0
                                        ) != len(events_by_id):
                                            errors.append(
                                                "review_session_event_count_mismatch"
                                            )
                                        if sorted(
                                            review_binding.get(
                                                "root_event_ids"
                                            ) or []
                                        ) != sorted(roots):
                                            errors.append(
                                                "review_session_root_ids_mismatch"
                                            )
                        else:
                            if session_members or event_members:
                                errors.append(
                                    "review_state_present_without_digest"
                                )
    except (OSError, zipfile.BadZipFile):
        errors.append("bundle_not_readable_zip")

    return DailyHandoffV3Verification(
        status="valid" if not errors else "invalid",
        bundle_path=str(bundle_path),
        schema_version=schema_version,
        file_count=file_count,
        errors=tuple(errors),
        warnings=tuple(warnings),
        manifest=manifest,
    )


def build_daily_handoff_bundle_v3(
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

    pipeline_path, pipeline_bytes = _pipeline_source(
        repo,
        pipeline_summary,
    )
    product_ready = pipeline_summary.get("m5_product_ready") is True
    history_ready = pipeline_summary.get("m5_history_ready") is True
    digest_ready = (
        pipeline_summary.get("m5_review_digest_ready") is True
    )
    research_ready = pipeline_summary.get("m4_research_ready") is True

    if digest_ready and not history_ready:
        raise RuntimeError("digest_ready_without_history_ready")
    if history_ready and not product_ready:
        raise RuntimeError("history_ready_without_product_ready")

    members: list[tuple[str, bytes, str]] = []
    warnings: list[str] = []

    with tempfile.TemporaryDirectory(prefix="htcn-handoff-v3-build-") as temp:
        base_path = Path(temp) / "htcn-daily-handoff-v2.zip"
        base_payload = build_daily_handoff_bundle(
            root=repo,
            pipeline_summary=pipeline_summary,
            output=base_path,
        )
        base_bytes = base_path.read_bytes()
        base_checked = verify_daily_handoff_bundle(base_path)
        if (
            base_checked.status != "valid"
            or not isinstance(base_checked.manifest, dict)
        ):
            raise RuntimeError(
                "handoff_v2_base_invalid:"
                + ",".join(base_checked.errors)
            )
        base_manifest = base_checked.manifest
        members.append(
            (
                "base/htcn-daily-handoff-v2.zip",
                base_bytes,
                "m5_handoff_v2_base",
            )
        )

        history_binding: dict[str, Any] | None = None
        digest_binding: dict[str, Any] | None = None
        review_binding: dict[str, Any] | None = None

        current_record: dict[str, Any] | None = None
        digest_payload: dict[str, Any] | None = None

        if history_ready:
            product_binding = base_manifest.get("product_binding")
            if not isinstance(product_binding, dict):
                raise RuntimeError("handoff_v2_product_binding_missing")
            trade_date = str(product_binding.get("trade_date") or "")
            if not trade_date:
                raise RuntimeError("handoff_v2_trade_date_missing")

            current_path, current_bytes, current_record = (
                _latest_history_record(
                    repo,
                    trade_date=trade_date,
                )
            )
            source = current_record.get("source") or {}
            if str(source.get("report_sha256") or "") != str(
                product_binding.get("report_sha256") or ""
            ):
                raise RuntimeError(
                    "history_product_report_hash_mismatch"
                )
            if str(source.get("snapshot_sha256") or "") != str(
                product_binding.get("snapshot_sha256") or ""
            ):
                raise RuntimeError(
                    "history_product_snapshot_hash_mismatch"
                )

            current_arcname = (
                "m5/history/current/"
                f"{trade_date}/{current_path.name}"
            )
            members.append(
                (
                    current_arcname,
                    current_bytes,
                    "m5_current_history_record",
                )
            )

            history_root = (
                repo / "data" / "product" / "m5" / "operator_history"
            )
            previous_date = current_record.get(
                "previous_recorded_trade_date"
            )
            previous_id = current_record.get(
                "previous_observation_id"
            )
            previous_record: dict[str, Any] | None = None
            if previous_date is not None:
                (
                    previous_path,
                    previous_bytes,
                    previous_record,
                ) = _history_link_record(
                    history_root,
                    trade_date=str(previous_date),
                    observation_id=str(previous_id or ""),
                    label="previous_history_record",
                )
                expected_delta = build_operator_delta(
                    previous_record.get("queue_snapshot") or {},
                    current_record.get("queue_snapshot") or {},
                )
                if expected_delta != current_record.get("delta"):
                    raise RuntimeError("current_history_delta_mismatch")
                members.append(
                    (
                        ("m5/history/previous/"
                        f"{previous_date}/{previous_path.name}"),
                        previous_bytes,
                        "m5_previous_history_record",
                    )
                )
            else:
                delta = current_record.get("delta") or {}
                if delta.get("status") != (
                    "baseline_no_previous_observation"
                ):
                    raise RuntimeError(
                        "current_history_baseline_status_mismatch"
                    )

            previous_same_id = current_record.get(
                "previous_same_day_observation_id"
            )
            if previous_same_id is not None:
                (
                    same_path,
                    same_bytes,
                    _,
                ) = _history_link_record(
                    history_root,
                    trade_date=trade_date,
                    observation_id=str(previous_same_id),
                    label="previous_same_day_history_record",
                )
                members.append(
                    (
                        ("m5/history/previous_same_day/"
                        f"{trade_date}/{same_path.name}"),
                        same_bytes,
                        "m5_previous_same_day_history_record",
                    )
                )

            history_binding = {
                "trade_date": trade_date,
                "observation_id": current_record.get(
                    "observation_id"
                ),
                "revision_ordinal": current_record.get(
                    "revision_ordinal"
                ),
                "record_integrity_sha256": current_record.get(
                    "record_integrity_sha256"
                ),
                "record_sha256": _sha256_bytes(current_bytes),
                "source_report_sha256": source.get(
                    "report_sha256"
                ),
                "source_snapshot_sha256": source.get(
                    "snapshot_sha256"
                ),
                "previous_recorded_trade_date": previous_date,
                "previous_observation_id": previous_id,
                "previous_same_day_observation_id": (
                    previous_same_id
                ),
            }

        if digest_ready:
            if current_record is None:
                raise RuntimeError("digest_ready_without_current_history")
            (
                digest_path,
                digest_bytes,
                digest_payload,
            ) = _load_valid_digest(
                repo,
                current_record=current_record,
            )
            members.append(
                (
                    "m5/review/m5-daily-review-digest.json",
                    digest_bytes,
                    "m5_daily_review_digest",
                )
            )
            digest_binding = {
                "source_path": _repo_relative(
                    repo,
                    digest_path,
                    label="daily_review_digest",
                ),
                "trade_date": digest_payload.get("trade_date"),
                "source_observation_id": digest_payload.get(
                    "source_observation_id"
                ),
                "source_revision_ordinal": digest_payload.get(
                    "source_revision_ordinal"
                ),
                "status": digest_payload.get("status"),
                "change_count": digest_payload.get("change_count"),
                "digest_sha256": _sha256_bytes(digest_bytes),
            }

            (
                session_bytes,
                session,
                journal_events,
            ) = _build_review_session_export(
                repo,
                current_record=current_record,
                digest_payload=digest_payload,
            )
            members.append(
                (
                    "m5/review/m5-review-session-snapshot.json",
                    session_bytes,
                    "m5_review_session_snapshot",
                )
            )
            for _, event_bytes, event in journal_events:
                members.append(
                    (
                        _event_arcname(event),
                        event_bytes,
                        "m5_review_journal_event",
                    )
                )
            root_event_ids = sorted(
                _review_root_event_ids(session)
            )
            review_binding = {
                "trade_date": session.get("trade_date"),
                "source_observation_id": session.get(
                    "source_observation_id"
                ),
                "source_revision_ordinal": session.get(
                    "source_revision_ordinal"
                ),
                "session_sha256": _sha256_bytes(session_bytes),
                "review_state_counts": session.get(
                    "review_state_counts"
                ),
                "active_follow_up_count": session.get(
                    "active_follow_up_count"
                ),
                "active_follow_up_in_current_digest_count": (
                    session.get(
                        "active_follow_up_in_current_digest_count"
                    )
                ),
                "journal_event_count": len(journal_events),
                "root_event_ids": root_event_ids,
            }

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
        "complete_review_transport"
        if product_ready and history_ready and digest_ready
        else "history_transport_review_degraded"
        if product_ready and history_ready
        else "product_transport_history_degraded"
        if product_ready
        else "base_transport_product_failed"
    )

    manifest: dict[str, Any] = {
        "schema_version": DAILY_HANDOFF_V3_SCHEMA_VERSION,
        "status": status,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "transport_only": True,
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "is_trade_instruction": False,
        "alpha_inference_allowed": False,
        "predictive_score_used": False,
        "historical_outcome_used_for_ranking": False,
        "review_state_changes_product_ranking": False,
        "m4_authority_remains_inside_nested_v2_capture_chain": True,
        "phase10_handoff_v2_is_nested_and_unmodified": True,
        "review_session_is_product_workflow_only": True,
        "pipeline_report_source": _repo_relative(
            repo,
            pipeline_path,
            label="pipeline_report",
        ),
        "pipeline_report_sha256": _sha256_bytes(pipeline_bytes),
        "m5_product_ready": product_ready,
        "m5_history_ready": history_ready,
        "m5_review_digest_ready": digest_ready,
        "m4_research_ready": research_ready,
        "nested_v2_binding": {
            "schema_version": BASE_V2_SCHEMA_VERSION,
            "bundle_sha256": _sha256_bytes(base_bytes),
            "status": base_payload.get("status"),
            "product_binding": base_manifest.get(
                "product_binding"
            ),
        },
        "history_binding": history_binding,
        "digest_binding": digest_binding,
        "review_session_binding": review_binding,
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
            "daily-handoff-v3-manifest.json",
            _canonical_json_bytes(manifest),
        )
        for arcname, data, _ in members:
            archive.writestr(arcname, data)

    checked = verify_daily_handoff_bundle_v3(tmp)
    if checked.status != "valid":
        tmp.unlink(missing_ok=True)
        raise RuntimeError(
            "daily_handoff_v3_verification_failed:"
            + ",".join(checked.errors)
        )
    tmp.replace(output_path)

    final = verify_daily_handoff_bundle_v3(output_path)
    if final.status != "valid":
        raise RuntimeError(
            "daily_handoff_v3_post_replace_verification_failed:"
            + ",".join(final.errors)
        )

    return {
        **manifest,
        "output": str(output_path),
        "bundle_size_bytes": output_path.stat().st_size,
        "bundle_sha256": _sha256_path(output_path),
        "verification": final.as_payload(),
    }
