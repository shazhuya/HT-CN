from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any

from htcn.app.daily_review_digest import (
    build_latest_daily_review_digest,
    filter_daily_review_digest,
)
from htcn.app.operator_history import query_operator_history
from htcn.app.operator_process_lock import OperatorCacheProcessLock


REVIEW_JOURNAL_SCHEMA_VERSION = 1
REVIEW_STATES = ("unseen", "reviewed", "follow_up")
MAX_REVIEW_NOTE_LENGTH = 1000


@dataclass(frozen=True, slots=True)
class ReviewFollowupJournalContract:
    version: int = 1
    semantics: str = "product_review_workflow_only"
    append_only: bool = True
    binding: str = "source_observation_id_plus_display_key"
    default_state_without_event: str = "unseen"
    follow_up_continuity: str = "latest_event_per_display_key"
    idempotency: str = "client_request_id"
    authoritative_transition: bool = False
    authoritative_evidence: bool = False
    writes_m4_evidence: bool = False
    predictive_score_used: bool = False
    historical_outcome_used_for_ranking: bool = False
    alpha_inference_allowed: bool = False
    is_trade_instruction: bool = False
    mutates_operator_queue: bool = False
    mutates_operator_history: bool = False
    mutates_action_state: bool = False
    mutates_lifecycle: bool = False
    mutates_harmonic_identity: bool = False
    mutates_source_raw_prz: bool = False

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


def _binding_id(source_observation_id: str, display_key: str) -> str:
    return sha256(
        f"{source_observation_id}\n{display_key}".encode("utf-8")
    ).hexdigest()


def _event_integrity_sha256(event: dict[str, Any]) -> str:
    material = dict(event)
    material.pop("record_integrity_sha256", None)
    return sha256(_canonical_json(material).encode("utf-8")).hexdigest()


def _write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    data = _canonical_json_bytes(payload)
    with temp.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def _event_files(journal_root: Path) -> list[Path]:
    if not journal_root.is_dir():
        return []
    return sorted(
        path
        for path in journal_root.glob("*/*/*.json")
        if path.is_file()
    )


def _normalize_note(note: object) -> str:
    value = "" if note is None else str(note)
    value = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if len(value) > MAX_REVIEW_NOTE_LENGTH:
        raise ValueError(
            f"review note exceeds {MAX_REVIEW_NOTE_LENGTH} characters"
        )
    return value


def _validate_request_id(value: object) -> str:
    request_id = str(value or "").strip()
    if not request_id:
        raise ValueError("client_request_id is required")
    if len(request_id) > 128:
        raise ValueError("client_request_id is too long")
    return request_id


def _validate_state(value: object) -> str:
    state = str(value or "").strip()
    if state not in REVIEW_STATES:
        raise ValueError(f"unknown review state: {state}")
    return state


def _find_source_change(
    *,
    history_root: Path,
    source_observation_id: str,
    display_key: str,
) -> dict[str, Any]:
    if len(source_observation_id) != 64:
        raise ValueError("source_observation_id must be a sha256 id")
    if not display_key:
        raise ValueError("display_key is required")

    payload = query_operator_history(
        history_root=history_root,
        display_key=display_key,
        latest_revision_per_day=False,
        summary_only=False,
        limit=100000,
    )
    for observation in payload.get("observations") or []:
        if observation.get("observation_id") != source_observation_id:
            continue
        matches = [
            dict(change)
            for change in (observation.get("changes") or [])
            if str(change.get("display_key") or "") == display_key
        ]
        if len(matches) != 1:
            raise ValueError(
                "review source display key is not unique in observation"
            )
        change = matches[0]
        instrument_id = str(change.get("instrument_id") or "")
        if not instrument_id:
            raise ValueError("review source instrument_id is missing")
        return {
            "trade_date": str(observation.get("trade_date") or ""),
            "revision_ordinal": int(
                observation.get("revision_ordinal") or 0
            ),
            "source_generated_at_utc": str(
                observation.get("source_generated_at_utc") or ""
            ),
            "instrument_id": instrument_id,
            "change_types": [
                str(value)
                for value in (change.get("change_types") or [])
            ],
        }
    raise ValueError(
        "review source observation/display_key binding not found"
    )


def verify_review_journal_event(path: str | Path) -> dict[str, Any]:
    event_path = Path(path)
    errors: list[str] = []
    try:
        raw = json.loads(event_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "status": "invalid",
            "path": str(event_path),
            "errors": [f"review_event_unreadable:{type(exc).__name__}"],
            "event": None,
        }
    if not isinstance(raw, dict):
        return {
            "status": "invalid",
            "path": str(event_path),
            "errors": ["review_event_not_object"],
            "event": None,
        }
    event = raw

    if int(event.get("schema_version") or 0) != REVIEW_JOURNAL_SCHEMA_VERSION:
        errors.append("review_event_schema_mismatch")

    contract = event.get("contract")
    if not isinstance(contract, dict):
        errors.append("review_event_contract_missing")
    else:
        required_false = (
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
        )
        for field in required_false:
            if contract.get(field) is not False:
                errors.append(f"review_event_boundary_invalid:{field}")
        if contract.get("append_only") is not True:
            errors.append("review_event_append_only_invalid")

    source = event.get("source")
    if not isinstance(source, dict):
        errors.append("review_event_source_missing")
        source = {}

    source_observation_id = str(
        source.get("observation_id") or ""
    )
    display_key = str(source.get("display_key") or "")
    trade_date = str(source.get("trade_date") or "")
    binding_id = str(event.get("binding_id") or "")
    expected_binding = _binding_id(
        source_observation_id,
        display_key,
    )
    if binding_id != expected_binding:
        errors.append("review_event_binding_id_mismatch")

    state = str(event.get("review_state") or "")
    if state not in REVIEW_STATES:
        errors.append("review_event_state_invalid")

    note = event.get("note")
    if not isinstance(note, str):
        errors.append("review_event_note_invalid")
    elif len(note) > MAX_REVIEW_NOTE_LENGTH:
        errors.append("review_event_note_too_long")

    request_id = str(event.get("client_request_id") or "")
    if not request_id:
        errors.append("review_event_request_id_missing")

    event_id = str(event.get("event_id") or "")
    material = {
        "source": source,
        "binding_id": binding_id,
        "review_state": state,
        "note": note,
        "client_request_id": request_id,
        "created_at_utc": event.get("created_at_utc"),
        "binding_event_ordinal": event.get("binding_event_ordinal"),
        "display_key_event_ordinal": event.get(
            "display_key_event_ordinal"
        ),
        "previous_binding_event_id": event.get(
            "previous_binding_event_id"
        ),
        "previous_display_key_event_id": event.get(
            "previous_display_key_event_id"
        ),
    }
    expected_event_id = sha256(
        _canonical_json(material).encode("utf-8")
    ).hexdigest()
    if event_id != expected_event_id:
        errors.append("review_event_id_mismatch")

    if event_path.name != f"{event_id}.json":
        errors.append("review_event_filename_mismatch")
    if event_path.parent.name != binding_id:
        errors.append("review_event_binding_directory_mismatch")
    if event_path.parent.parent.name != trade_date:
        errors.append("review_event_trade_date_directory_mismatch")

    integrity = str(event.get("record_integrity_sha256") or "")
    if len(integrity) != 64:
        errors.append("review_event_integrity_missing")
    elif integrity != _event_integrity_sha256(event):
        errors.append("review_event_integrity_mismatch")

    return {
        "status": "valid" if not errors else "invalid",
        "path": str(event_path),
        "errors": errors,
        "event": event,
    }


def _event_sort_key(event: dict[str, Any]) -> tuple[int, str]:
    return (
        int(event.get("display_key_event_ordinal") or 0),
        str(event.get("event_id") or ""),
    )


def _load_valid_events(journal_root: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    request_ids: set[str] = set()
    for path in _event_files(journal_root):
        checked = verify_review_journal_event(path)
        if checked["status"] != "valid":
            raise RuntimeError(
                "review_journal_integrity_failure:"
                + ",".join(checked["errors"])
            )
        event = checked["event"]
        assert isinstance(event, dict)
        request_id = str(event.get("client_request_id") or "")
        if request_id in request_ids:
            raise RuntimeError(
                "review_journal_integrity_failure:"
                "duplicate_client_request_id"
            )
        request_ids.add(request_id)
        events.append(event)

    by_binding: dict[str, list[dict[str, Any]]] = {}
    by_display_key: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        by_binding.setdefault(
            str(event.get("binding_id") or ""),
            [],
        ).append(event)
        source = event.get("source") or {}
        by_display_key.setdefault(
            str(source.get("display_key") or ""),
            [],
        ).append(event)

    for binding_id, sequence in by_binding.items():
        sequence.sort(
            key=lambda item: (
                int(item.get("binding_event_ordinal") or 0),
                str(item.get("event_id") or ""),
            )
        )
        for index, event in enumerate(sequence, start=1):
            if int(event.get("binding_event_ordinal") or 0) != index:
                raise RuntimeError(
                    "review_journal_integrity_failure:"
                    f"binding_ordinal_gap:{binding_id}"
                )
            expected_previous = (
                None if index == 1 else sequence[index - 2]["event_id"]
            )
            if event.get("previous_binding_event_id") != expected_previous:
                raise RuntimeError(
                    "review_journal_integrity_failure:"
                    f"binding_link_mismatch:{binding_id}"
                )

    for display_key, sequence in by_display_key.items():
        sequence.sort(key=_event_sort_key)
        for index, event in enumerate(sequence, start=1):
            if int(event.get("display_key_event_ordinal") or 0) != index:
                raise RuntimeError(
                    "review_journal_integrity_failure:"
                    f"display_key_ordinal_gap:{display_key}"
                )
            expected_previous = (
                None if index == 1 else sequence[index - 2]["event_id"]
            )
            if event.get("previous_display_key_event_id") != expected_previous:
                raise RuntimeError(
                    "review_journal_integrity_failure:"
                    f"display_key_link_mismatch:{display_key}"
                )
    return events


def append_review_event(
    *,
    history_root: str | Path,
    journal_root: str | Path,
    source_observation_id: str,
    display_key: str,
    review_state: str,
    note: object,
    client_request_id: object,
    lock_timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    history = Path(history_root).resolve()
    journal = Path(journal_root).resolve()
    state = _validate_state(review_state)
    normalized_note = _normalize_note(note)
    request_id = _validate_request_id(client_request_id)
    source_meta = _find_source_change(
        history_root=history,
        source_observation_id=source_observation_id,
        display_key=display_key,
    )
    binding_id = _binding_id(source_observation_id, display_key)

    lock = OperatorCacheProcessLock(
        journal / ".locks" / "review-journal.lock",
        timeout_seconds=lock_timeout_seconds,
    )
    acquisition = lock.acquire()
    try:
        events = _load_valid_events(journal)
        for event in events:
            if event.get("client_request_id") != request_id:
                continue
            source = event.get("source") or {}
            equivalent = (
                source.get("observation_id") == source_observation_id
                and source.get("display_key") == display_key
                and event.get("review_state") == state
                and event.get("note") == normalized_note
            )
            if not equivalent:
                raise ValueError("client_request_id replay conflict")
            return {
                "status": "idempotent_existing",
                "event": event,
                "waited_for_lock": acquisition.waited,
                "wait_seconds": acquisition.wait_seconds,
            }

        binding_events = [
            event
            for event in events
            if event.get("binding_id") == binding_id
        ]
        display_events = [
            event
            for event in events
            if (event.get("source") or {}).get("display_key")
            == display_key
        ]
        binding_events.sort(
            key=lambda item: int(
                item.get("binding_event_ordinal") or 0
            )
        )
        display_events.sort(key=_event_sort_key)
        previous_binding = binding_events[-1] if binding_events else None
        previous_display = display_events[-1] if display_events else None

        created_at = datetime.now(timezone.utc).isoformat()
        source = {
            "observation_id": source_observation_id,
            "trade_date": source_meta["trade_date"],
            "revision_ordinal": source_meta["revision_ordinal"],
            "source_generated_at_utc": source_meta[
                "source_generated_at_utc"
            ],
            "display_key": display_key,
            "instrument_id": source_meta["instrument_id"],
            "change_types": source_meta["change_types"],
        }
        material = {
            "source": source,
            "binding_id": binding_id,
            "review_state": state,
            "note": normalized_note,
            "client_request_id": request_id,
            "created_at_utc": created_at,
            "binding_event_ordinal": len(binding_events) + 1,
            "display_key_event_ordinal": len(display_events) + 1,
            "previous_binding_event_id": (
                None
                if previous_binding is None
                else previous_binding.get("event_id")
            ),
            "previous_display_key_event_id": (
                None
                if previous_display is None
                else previous_display.get("event_id")
            ),
        }
        event_id = sha256(
            _canonical_json(material).encode("utf-8")
        ).hexdigest()
        event = {
            "schema_version": REVIEW_JOURNAL_SCHEMA_VERSION,
            "contract": ReviewFollowupJournalContract().as_payload(),
            "event_id": event_id,
            **material,
            "authoritative_evidence": False,
            "writes_m4_evidence": False,
            "is_trade_instruction": False,
        }
        event["record_integrity_sha256"] = _event_integrity_sha256(
            event
        )

        path = (
            journal
            / source_meta["trade_date"]
            / binding_id
            / f"{event_id}.json"
        )
        _write_atomic(path, event)
        checked = verify_review_journal_event(path)
        if checked["status"] != "valid":
            raise RuntimeError(
                "review_journal_write_verification_failed:"
                + ",".join(checked["errors"])
            )
        return {
            "status": "appended",
            "event": event,
            "path": str(path),
            "waited_for_lock": acquisition.waited,
            "wait_seconds": acquisition.wait_seconds,
        }
    finally:
        lock.release()


def _review_state_index(
    *,
    journal_root: Path,
    source_observation_id: str,
    display_keys: list[str],
) -> dict[str, dict[str, Any]]:
    events = _load_valid_events(journal_root)
    result: dict[str, dict[str, Any]] = {}

    for display_key in display_keys:
        binding_id = _binding_id(source_observation_id, display_key)
        binding_events = [
            event
            for event in events
            if event.get("binding_id") == binding_id
        ]
        binding_events.sort(
            key=lambda item: int(
                item.get("binding_event_ordinal") or 0
            )
        )
        display_events = [
            event
            for event in events
            if (event.get("source") or {}).get("display_key")
            == display_key
        ]
        display_events.sort(key=_event_sort_key)

        current_event = (
            binding_events[-1] if binding_events else None
        )
        latest_display_event = (
            display_events[-1] if display_events else None
        )
        active_follow_up = bool(
            latest_display_event is not None
            and latest_display_event.get("review_state") == "follow_up"
        )
        result[display_key] = {
            "review_state": (
                str(current_event.get("review_state"))
                if current_event is not None
                else "unseen"
            ),
            "note": (
                str(current_event.get("note") or "")
                if current_event is not None
                else ""
            ),
            "current_event_id": (
                current_event.get("event_id")
                if current_event is not None
                else None
            ),
            "active_follow_up": active_follow_up,
            "active_follow_up_event_id": (
                latest_display_event.get("event_id")
                if active_follow_up
                else None
            ),
            "active_follow_up_origin_observation_id": (
                (latest_display_event.get("source") or {}).get(
                    "observation_id"
                )
                if active_follow_up
                else None
            ),
            "active_follow_up_origin_trade_date": (
                (latest_display_event.get("source") or {}).get(
                    "trade_date"
                )
                if active_follow_up
                else None
            ),
        }
    return result


def query_active_follow_ups(
    *,
    journal_root: str | Path,
) -> list[dict[str, Any]]:
    events = _load_valid_events(Path(journal_root).resolve())
    latest: dict[str, dict[str, Any]] = {}
    for event in events:
        source = event.get("source") or {}
        display_key = str(source.get("display_key") or "")
        prior = latest.get(display_key)
        if (
            prior is None
            or int(event.get("display_key_event_ordinal") or 0)
            > int(prior.get("display_key_event_ordinal") or 0)
        ):
            latest[display_key] = event

    active: list[dict[str, Any]] = []
    for display_key, event in latest.items():
        if event.get("review_state") != "follow_up":
            continue
        source = event.get("source") or {}
        active.append({
            "display_key": display_key,
            "instrument_id": source.get("instrument_id"),
            "source_observation_id": source.get("observation_id"),
            "source_trade_date": source.get("trade_date"),
            "source_revision_ordinal": source.get("revision_ordinal"),
            "source_change_types": source.get("change_types") or [],
            "event_id": event.get("event_id"),
            "created_at_utc": event.get("created_at_utc"),
            "note": event.get("note") or "",
            "review_state": "follow_up",
        })
    active.sort(
        key=lambda item: (
            str(item.get("created_at_utc") or ""),
            str(item.get("display_key") or ""),
        ),
        reverse=True,
    )
    return active


def build_latest_review_session(
    *,
    history_root: str | Path,
    journal_root: str | Path,
) -> dict[str, Any]:
    digest = build_latest_daily_review_digest(
        history_root=str(Path(history_root).resolve()),
    )
    result = dict(digest)
    result["session_contract"] = (
        ReviewFollowupJournalContract().as_payload()
    )
    active_follow_ups = query_active_follow_ups(
        journal_root=journal_root,
    )
    if not digest.get("review_ready"):
        result["review_state_counts"] = {
            "unseen": 0,
            "reviewed": 0,
            "follow_up": 0,
        }
        result["active_follow_ups"] = active_follow_ups
        result["active_follow_up_count"] = len(active_follow_ups)
        result["active_follow_up_in_current_digest_count"] = 0
        return result

    source_observation_id = str(
        digest.get("source_observation_id") or ""
    )
    display_keys = [
        str(item.get("display_key") or "")
        for section in (digest.get("workflow_sections") or [])
        for item in (section.get("items") or [])
    ]
    states = _review_state_index(
        journal_root=Path(journal_root).resolve(),
        source_observation_id=source_observation_id,
        display_keys=display_keys,
    )

    counts: Counter[str] = Counter()
    active_in_current_count = 0
    sections: list[dict[str, Any]] = []
    for raw_section in digest.get("workflow_sections") or []:
        section = dict(raw_section)
        items: list[dict[str, Any]] = []
        for raw_item in section.get("items") or []:
            item = dict(raw_item)
            review = states.get(
                str(item.get("display_key") or ""),
                {
                    "review_state": "unseen",
                    "note": "",
                    "current_event_id": None,
                    "active_follow_up": False,
                    "active_follow_up_event_id": None,
                    "active_follow_up_origin_observation_id": None,
                    "active_follow_up_origin_trade_date": None,
                },
            )
            item["review"] = review
            counts[str(review["review_state"])] += 1
            if review["active_follow_up"]:
                active_in_current_count += 1
            items.append(item)
        section["items"] = items
        sections.append(section)

    result["workflow_sections"] = sections
    result["review_state_counts"] = {
        state: int(counts.get(state, 0))
        for state in REVIEW_STATES
    }
    current_keys = set(display_keys)
    for item in active_follow_ups:
        item["in_current_digest"] = (
            str(item.get("display_key") or "") in current_keys
        )
    result["active_follow_ups"] = active_follow_ups
    result["active_follow_up_count"] = len(active_follow_ups)
    result["active_follow_up_in_current_digest_count"] = (
        active_in_current_count
    )
    result["review_workflow_mutates_source"] = False
    return result


def filter_review_session(
    payload: dict[str, Any],
    *,
    workflow_bucket: str | None = None,
    change_type: str | None = None,
    instrument_id: str | None = None,
    review_state: str | None = None,
    follow_up_only: bool = False,
) -> dict[str, Any]:
    if review_state is not None and review_state not in REVIEW_STATES:
        raise ValueError(f"unknown review state: {review_state}")

    filtered = filter_daily_review_digest(
        payload,
        workflow_bucket=workflow_bucket,
        change_type=change_type,
        instrument_id=instrument_id,
    )
    sections: list[dict[str, Any]] = []
    count = 0
    for raw_section in filtered.get("filtered_workflow_sections") or []:
        section = dict(raw_section)
        items = []
        for raw_item in section.get("items") or []:
            item = dict(raw_item)
            review = item.get("review") or {}
            if (
                review_state is not None
                and review.get("review_state") != review_state
            ):
                continue
            if follow_up_only and review.get("active_follow_up") is not True:
                continue
            items.append(item)
        if items:
            section["items"] = items
            section["change_count"] = len(items)
            sections.append(section)
            count += len(items)

    filtered["filtered_workflow_sections"] = sections
    filtered["filtered_change_count"] = count
    filtered["review_filter"] = {
        "review_state": review_state,
        "follow_up_only": bool(follow_up_only),
    }
    filtered["source_review_state_counts_unchanged"] = payload.get(
        "review_state_counts"
    )
    filtered["source_active_follow_up_count_unchanged"] = payload.get(
        "active_follow_up_count"
    )
    return filtered
