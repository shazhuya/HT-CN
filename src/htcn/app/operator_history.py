from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any

from htcn.app.operator_delta import (
    OperatorDeltaContract,
    build_operator_delta,
)
from htcn.app.operator_process_lock import OperatorCacheProcessLock
from htcn.app.operator_snapshot import (
    OPERATOR_SNAPSHOT_CONTRACT_VERSION,
    OPERATOR_SNAPSHOT_SCHEMA_VERSION,
)


OPERATOR_HISTORY_SCHEMA_VERSION = 1
PERSISTED_CACHE_STATUSES = {
    "hit",
    "hit_after_race",
    "hit_after_process_wait",
    "rebuilt",
    "rebuilt_force",
    "coalesced_wait",
}


@dataclass(frozen=True, slots=True)
class OperatorHistoryContract:
    version: int = 1
    semantics: str = "product_observation_only"
    append_only: bool = True
    same_day_revision_mode: str = "append_not_overwrite"
    previous_baseline_mode: str = (
        "latest_observation_of_previous_recorded_trade_date"
    )
    authoritative_transition: bool = False
    writes_m4_evidence: bool = False
    predictive_score_used: bool = False
    historical_outcome_used_for_ranking: bool = False
    alpha_inference_allowed: bool = False
    is_trade_instruction: bool = False
    mutates_harmonic_identity: bool = False
    mutates_source_raw_prz: bool = False
    owns_lifecycle: bool = False

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


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


def _validate_current_source(
    *,
    repo: Path,
    report_path: Path,
) -> dict[str, Any]:
    report = _read_json_object(report_path, label="m5_operator_snapshot_report")
    report_bytes = report_path.read_bytes()

    if int(report.get("schema_version") or 0) != 2:
        raise RuntimeError("m5_report_schema_mismatch")
    if report.get("product_ready") is not True:
        raise RuntimeError("m5_report_not_product_ready")
    trade_date = str(report.get("as_of_trade_date") or "")
    if not trade_date:
        raise RuntimeError("m5_report_trade_date_missing")
    if report.get("observation_integrity") != "single_as_of":
        raise RuntimeError("m5_report_not_single_as_of")

    identity = report.get("input_identity")
    if not isinstance(identity, dict):
        raise RuntimeError("m5_report_input_identity_missing")
    fingerprint = str(identity.get("fingerprint") or "")
    if len(fingerprint) != 64:
        raise RuntimeError("m5_report_input_identity_invalid")

    cache = report.get("product_cache")
    if not isinstance(cache, dict):
        raise RuntimeError("m5_report_product_cache_missing")
    if str(cache.get("status") or "") not in PERSISTED_CACHE_STATUSES:
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

    raw_cache_path = str(cache.get("cache_path") or "")
    if not raw_cache_path:
        raise RuntimeError("m5_report_cache_path_missing")
    cache_root = (repo / "data" / "product" / "m5" / "operator_queue").resolve()
    raw_path = Path(raw_cache_path)
    snapshot_path = _resolve_inside(
        cache_root if raw_path.is_absolute() else repo,
        raw_path,
        label="operator_snapshot",
    )
    if snapshot_path != cache_root and cache_root not in snapshot_path.parents:
        raise RuntimeError("operator_snapshot_outside_cache_root")
    if snapshot_path.parent != cache_root:
        raise RuntimeError("operator_snapshot_not_cache_root_member")
    if not snapshot_path.is_file():
        raise RuntimeError("operator_snapshot_missing")

    snapshot = _read_json_object(snapshot_path, label="operator_snapshot")
    snapshot_bytes = snapshot_path.read_bytes()
    if int(snapshot.get("schema_version") or 0) != OPERATOR_SNAPSHOT_SCHEMA_VERSION:
        raise RuntimeError("operator_snapshot_schema_mismatch")
    if int(snapshot.get("contract_version") or 0) != OPERATOR_SNAPSHOT_CONTRACT_VERSION:
        raise RuntimeError("operator_snapshot_contract_mismatch")
    if str(snapshot.get("expected_trade_date") or "") != trade_date:
        raise RuntimeError("operator_snapshot_trade_date_mismatch")
    snapshot_identity = snapshot.get("input_identity")
    if not isinstance(snapshot_identity, dict) or snapshot_identity != identity:
        raise RuntimeError("operator_snapshot_input_identity_mismatch")
    queue = snapshot.get("queue")
    if not isinstance(queue, dict):
        raise RuntimeError("operator_snapshot_queue_missing")
    if str(queue.get("as_of_trade_date") or "") != trade_date:
        raise RuntimeError("operator_snapshot_queue_trade_date_mismatch")
    if queue.get("observation_integrity") != "single_as_of":
        raise RuntimeError("operator_snapshot_queue_not_single_as_of")
    if snapshot.get("authoritative_evidence") is not False:
        raise RuntimeError("operator_snapshot_authority_boundary_invalid")
    if snapshot.get("writes_m4_evidence") is not False:
        raise RuntimeError("operator_snapshot_m4_write_boundary_invalid")

    generated_at = str(snapshot.get("generated_at_utc") or "")
    if not generated_at:
        raise RuntimeError("operator_snapshot_generated_at_missing")
    queue_sha = _sha256_bytes(_canonical_json_bytes(queue))
    report_sha = _sha256_bytes(report_bytes)
    snapshot_sha = _sha256_bytes(snapshot_bytes)
    material = {
        "trade_date": trade_date,
        "source_generated_at_utc": generated_at,
        "input_identity_fingerprint": fingerprint,
        "report_sha256": report_sha,
        "snapshot_sha256": snapshot_sha,
        "queue_sha256": queue_sha,
    }
    observation_id = sha256(
        _canonical_json(material).encode("utf-8")
    ).hexdigest()

    return {
        "trade_date": trade_date,
        "generated_at_utc": generated_at,
        "identity": identity,
        "identity_fingerprint": fingerprint,
        "report_path": report_path,
        "report_sha256": report_sha,
        "snapshot_path": snapshot_path,
        "snapshot_sha256": snapshot_sha,
        "queue": queue,
        "queue_sha256": queue_sha,
        "observation_id": observation_id,
    }


def _history_files(history_root: Path) -> list[Path]:
    if not history_root.is_dir():
        return []
    return sorted(
        path
        for path in history_root.glob("*/*.json")
        if path.is_file()
    )


def verify_operator_history_record(path: str | Path) -> dict[str, Any]:
    record_path = Path(path)
    errors: list[str] = []
    try:
        record = _read_json_object(record_path, label="operator_history_record")
    except RuntimeError as exc:
        return {
            "status": "invalid",
            "path": str(record_path),
            "errors": [str(exc)],
            "record": None,
        }

    if int(record.get("schema_version") or 0) != OPERATOR_HISTORY_SCHEMA_VERSION:
        errors.append("history_schema_mismatch")
    contract = record.get("contract")
    if not isinstance(contract, dict):
        errors.append("history_contract_missing")
    else:
        required_false = (
            "authoritative_transition",
            "writes_m4_evidence",
            "predictive_score_used",
            "historical_outcome_used_for_ranking",
            "alpha_inference_allowed",
            "is_trade_instruction",
            "mutates_harmonic_identity",
            "mutates_source_raw_prz",
            "owns_lifecycle",
        )
        for field in required_false:
            if contract.get(field) is not False:
                errors.append(f"history_contract_boundary_invalid:{field}")
        if contract.get("append_only") is not True:
            errors.append("history_contract_append_only_invalid")

    trade_date = str(record.get("trade_date") or "")
    observation_id = str(record.get("observation_id") or "")
    source = record.get("source")
    queue = record.get("queue_snapshot")
    if not trade_date:
        errors.append("history_trade_date_missing")
    if not isinstance(source, dict):
        errors.append("history_source_missing")
    if not isinstance(queue, dict):
        errors.append("history_queue_missing")
    else:
        if str(queue.get("as_of_trade_date") or "") != trade_date:
            errors.append("history_queue_trade_date_mismatch")
        if queue.get("observation_integrity") != "single_as_of":
            errors.append("history_queue_not_single_as_of")

    if isinstance(source, dict) and isinstance(queue, dict):
        queue_sha = _sha256_bytes(_canonical_json_bytes(queue))
        if queue_sha != str(source.get("queue_sha256") or ""):
            errors.append("history_queue_hash_mismatch")
        material = {
            "trade_date": trade_date,
            "source_generated_at_utc": source.get("generated_at_utc"),
            "input_identity_fingerprint": source.get(
                "input_identity_fingerprint"
            ),
            "report_sha256": source.get("report_sha256"),
            "snapshot_sha256": source.get("snapshot_sha256"),
            "queue_sha256": queue_sha,
        }
        expected_id = sha256(
            _canonical_json(material).encode("utf-8")
        ).hexdigest()
        if observation_id != expected_id:
            errors.append("history_observation_id_mismatch")
        if record_path.name != f"{observation_id}.json":
            errors.append("history_filename_mismatch")
        if record_path.parent.name != trade_date:
            errors.append("history_directory_trade_date_mismatch")

    return {
        "status": "valid" if not errors else "invalid",
        "path": str(record_path),
        "errors": errors,
        "record": record,
    }


def _load_valid_records(history_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in _history_files(history_root):
        checked = verify_operator_history_record(path)
        if checked["status"] != "valid":
            raise RuntimeError(
                "operator_history_integrity_failure:"
                + ",".join(checked["errors"])
            )
        record = checked["record"]
        assert isinstance(record, dict)
        records.append(record)
    return records


def _record_sort_key(record: dict[str, Any]) -> tuple[str, str, str]:
    source = record.get("source") or {}
    return (
        str(record.get("trade_date") or ""),
        str(source.get("generated_at_utc") or ""),
        str(record.get("observation_id") or ""),
    )


def _latest_for_date(
    records: list[dict[str, Any]],
    trade_date: str,
) -> dict[str, Any] | None:
    same = [
        record
        for record in records
        if str(record.get("trade_date") or "") == trade_date
    ]
    return max(same, key=_record_sort_key) if same else None


def _previous_trade_date_record(
    records: list[dict[str, Any]],
    current_trade_date: str,
) -> dict[str, Any] | None:
    prior_dates = sorted({
        str(record.get("trade_date") or "")
        for record in records
        if str(record.get("trade_date") or "") < current_trade_date
    })
    if not prior_dates:
        return None
    return _latest_for_date(records, prior_dates[-1])


def _baseline_delta(current_queue: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "contract": OperatorDeltaContract().as_payload(),
        "previous_as_of_trade_date": None,
        "current_as_of_trade_date": current_queue.get("as_of_trade_date"),
        "status": "baseline_no_previous_observation",
        "change_count": 0,
        "change_type_counts": {},
        "changes": [],
        "comparison_incomplete_instruments": [],
        "warnings": [],
    }


def _write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(
        f".{path.name}.{os.getpid()}.tmp"
    )
    data = _canonical_json_bytes(payload)
    with tmp.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def append_operator_history(
    *,
    root: str | Path,
    report_path: str | Path,
    history_root: str | Path | None = None,
    lock_timeout_seconds: float = 1800.0,
) -> dict[str, Any]:
    repo = Path(root).resolve()
    report = Path(report_path)
    if not report.is_absolute():
        report = repo / report
    report = report.resolve()
    if history_root is None:
        history = repo / "data" / "product" / "m5" / "operator_history"
    else:
        history = Path(history_root)
        if not history.is_absolute():
            history = repo / history
    history = history.resolve()

    current = _validate_current_source(repo=repo, report_path=report)
    lock = OperatorCacheProcessLock(
        history / ".locks" / "operator-history.lock",
        timeout_seconds=lock_timeout_seconds,
    )
    acquisition = lock.acquire()
    try:
        records = _load_valid_records(history)
        trade_date = str(current["trade_date"])
        observation_id = str(current["observation_id"])
        exact_path = history / trade_date / f"{observation_id}.json"

        existing = next(
            (
                record
                for record in records
                if record.get("observation_id") == observation_id
            ),
            None,
        )
        if existing is not None:
            return {
                "status": "idempotent_existing",
                "trade_date": trade_date,
                "observation_id": observation_id,
                "revision_ordinal": existing.get("revision_ordinal"),
                "record_path": _repo_relative(
                    repo,
                    exact_path,
                    label="history_record",
                ),
                "delta": existing.get("delta"),
                "cross_process_waited": acquisition.waited,
                "cross_process_wait_seconds": acquisition.wait_seconds,
                "authoritative_evidence": False,
                "writes_m4_evidence": False,
            }

        latest_trade_date = max(
            (
                str(record.get("trade_date") or "")
                for record in records
            ),
            default="",
        )
        if latest_trade_date and trade_date < latest_trade_date:
            raise RuntimeError(
                "operator_history_backfill_forbidden:"
                f"{trade_date}<{latest_trade_date}"
            )

        same_date = [
            record
            for record in records
            if str(record.get("trade_date") or "") == trade_date
        ]
        latest_same = (
            max(same_date, key=_record_sort_key)
            if same_date
            else None
        )
        if latest_same is not None:
            latest_source = latest_same.get("source") or {}
            latest_generated = str(
                latest_source.get("generated_at_utc") or ""
            )
            if str(current["generated_at_utc"]) < latest_generated:
                raise RuntimeError(
                    "operator_history_older_same_day_revision_forbidden"
                )

        previous = _previous_trade_date_record(records, trade_date)
        if previous is None:
            delta = _baseline_delta(current["queue"])
            previous_trade_date = None
            previous_observation_id = None
        else:
            previous_queue = previous.get("queue_snapshot")
            if not isinstance(previous_queue, dict):
                raise RuntimeError(
                    "operator_history_previous_queue_missing"
                )
            delta = build_operator_delta(
                previous_queue,
                current["queue"],
            )
            previous_trade_date = previous.get("trade_date")
            previous_observation_id = previous.get("observation_id")

        record = {
            "schema_version": OPERATOR_HISTORY_SCHEMA_VERSION,
            "contract": OperatorHistoryContract().as_payload(),
            "trade_date": trade_date,
            "observation_id": observation_id,
            "revision_ordinal": len(same_date) + 1,
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
            "source": {
                "generated_at_utc": current["generated_at_utc"],
                "input_identity_fingerprint": current[
                    "identity_fingerprint"
                ],
                "report_path": _repo_relative(
                    repo,
                    current["report_path"],
                    label="history_report",
                ),
                "report_sha256": current["report_sha256"],
                "snapshot_path": _repo_relative(
                    repo,
                    current["snapshot_path"],
                    label="history_snapshot",
                ),
                "snapshot_sha256": current["snapshot_sha256"],
                "queue_sha256": current["queue_sha256"],
            },
            "previous_recorded_trade_date": previous_trade_date,
            "previous_observation_id": previous_observation_id,
            "queue_snapshot": current["queue"],
            "delta": delta,
            "authoritative_evidence": False,
            "writes_m4_evidence": False,
            "is_trade_instruction": False,
            "alpha_inference_allowed": False,
        }
        _write_atomic(exact_path, record)
        checked = verify_operator_history_record(exact_path)
        if checked["status"] != "valid":
            exact_path.unlink(missing_ok=True)
            raise RuntimeError(
                "operator_history_post_write_verification_failed:"
                + ",".join(checked["errors"])
            )

        return {
            "status": (
                "appended_revision"
                if same_date
                else "appended_new_trade_date"
            ),
            "trade_date": trade_date,
            "observation_id": observation_id,
            "revision_ordinal": record["revision_ordinal"],
            "record_path": _repo_relative(
                repo,
                exact_path,
                label="history_record",
            ),
            "previous_recorded_trade_date": previous_trade_date,
            "previous_observation_id": previous_observation_id,
            "delta": delta,
            "cross_process_waited": acquisition.waited,
            "cross_process_wait_seconds": acquisition.wait_seconds,
            "authoritative_evidence": False,
            "writes_m4_evidence": False,
        }
    finally:
        lock.release()


def query_operator_history(
    *,
    history_root: str | Path,
    instrument_id: str | None = None,
    display_key: str | None = None,
    start_trade_date: str | None = None,
    end_trade_date: str | None = None,
    latest_revision_per_day: bool = True,
    limit: int = 60,
) -> dict[str, Any]:
    root = Path(history_root)
    records = _load_valid_records(root)

    if latest_revision_per_day:
        latest: dict[str, dict[str, Any]] = {}
        for record in records:
            trade_date = str(record.get("trade_date") or "")
            prior = latest.get(trade_date)
            if prior is None or _record_sort_key(record) > _record_sort_key(prior):
                latest[trade_date] = record
        records = list(latest.values())

    records.sort(key=_record_sort_key, reverse=True)
    observations: list[dict[str, Any]] = []
    for record in records:
        trade_date = str(record.get("trade_date") or "")
        if start_trade_date and trade_date < start_trade_date:
            continue
        if end_trade_date and trade_date > end_trade_date:
            continue

        queue = record.get("queue_snapshot") or {}
        items = [
            item
            for item in (queue.get("items") or [])
            if (
                (instrument_id is None or item.get("instrument_id") == instrument_id)
                and (display_key is None or item.get("display_key") == display_key)
            )
        ]
        delta = record.get("delta") or {}
        changes = [
            change
            for change in (delta.get("changes") or [])
            if (
                (instrument_id is None or change.get("instrument_id") == instrument_id)
                and (display_key is None or change.get("display_key") == display_key)
            )
        ]

        if instrument_id is not None or display_key is not None:
            if not items and not changes:
                continue

        observations.append({
            "trade_date": trade_date,
            "observation_id": record.get("observation_id"),
            "revision_ordinal": record.get("revision_ordinal"),
            "source_generated_at_utc": (
                (record.get("source") or {}).get("generated_at_utc")
            ),
            "previous_recorded_trade_date": record.get(
                "previous_recorded_trade_date"
            ),
            "item_count": len(items),
            "items": items,
            "change_count": len(changes),
            "changes": changes,
            "delta_status": delta.get("status"),
            "comparison_incomplete_instruments": delta.get(
                "comparison_incomplete_instruments"
            ) or [],
        })
        if len(observations) >= max(1, int(limit)):
            break

    return {
        "schema_version": 1,
        "contract": OperatorHistoryContract().as_payload(),
        "filter": {
            "instrument_id": instrument_id,
            "display_key": display_key,
            "start_trade_date": start_trade_date,
            "end_trade_date": end_trade_date,
            "latest_revision_per_day": latest_revision_per_day,
            "limit": max(1, int(limit)),
        },
        "observation_count": len(observations),
        "observations": observations,
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "historical_outcome_used_for_ranking": False,
        "alpha_inference_allowed": False,
        "is_trade_instruction": False,
    }
