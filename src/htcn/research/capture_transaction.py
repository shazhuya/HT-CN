from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
import json
import os
from typing import Any, Iterable


CAPTURE_TRANSACTION_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class CommittedCapture:
    transaction_id: str
    code_head: str
    as_of_trade_date: str
    captured_at_utc: str
    instrument_count: int
    successful_instruments: int
    failed_instruments: int
    candidate_count: int
    worktree_clean: bool
    journal_rows: tuple[dict[str, Any], ...]
    status: str = "committed"
    schema_version: int = CAPTURE_TRANSACTION_SCHEMA_VERSION
    alpha_inference_allowed: bool = False
    is_trade_instruction: bool = False

    def as_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["journal_rows"] = [dict(row) for row in self.journal_rows]
        return payload


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _transaction_identity_payload(
    *,
    code_head: str,
    as_of_trade_date: str,
    instrument_count: int,
    successful_instruments: int,
    failed_instruments: int,
    journal_rows: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    rows = [dict(row) for row in journal_rows]
    rows.sort(key=lambda row: str(row.get("candidate_key") or ""))
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        clean = dict(row)
        clean.pop("capture_transaction_id", None)
        clean.pop("enrollment_state", None)
        clean.pop("first_observed_trade_date", None)
        clean.pop("prospective_outcome_eligible", None)
        clean.pop("outcome_enrollment_trade_date", None)
        clean.pop("outcome_eligibility_reason", None)
        normalized_rows.append(clean)
    return {
        "schema_version": CAPTURE_TRANSACTION_SCHEMA_VERSION,
        "code_head": code_head,
        "as_of_trade_date": as_of_trade_date,
        "instrument_count": int(instrument_count),
        "successful_instruments": int(successful_instruments),
        "failed_instruments": int(failed_instruments),
        "candidate_count": len(normalized_rows),
        "journal_rows": normalized_rows,
    }


def capture_transaction_id(
    *,
    code_head: str,
    as_of_trade_date: str,
    instrument_count: int,
    successful_instruments: int,
    failed_instruments: int,
    journal_rows: Iterable[dict[str, Any]],
) -> str:
    identity = _transaction_identity_payload(
        code_head=code_head,
        as_of_trade_date=as_of_trade_date,
        instrument_count=instrument_count,
        successful_instruments=successful_instruments,
        failed_instruments=failed_instruments,
        journal_rows=journal_rows,
    )
    return sha256(_canonical_json(identity).encode("utf-8")).hexdigest()[:24]


def _validate_rows(
    *,
    code_head: str,
    as_of_trade_date: str,
    journal_rows: list[dict[str, Any]],
) -> None:
    keys: list[str] = []
    for row in journal_rows:
        if str(row.get("code_head") or "") != code_head:
            raise ValueError("capture transaction journal row code_head mismatch")
        if str(row.get("as_of_trade_date") or "") != as_of_trade_date:
            raise ValueError("capture transaction journal row as-of mismatch")
        key = str(row.get("candidate_key") or "")
        if not key:
            raise ValueError("capture transaction journal row missing candidate_key")
        keys.append(key)
        if row.get("alpha_inference_allowed") is not False:
            raise ValueError("capture transaction row unexpectedly permits alpha inference")
        if row.get("is_trade_instruction") is not False:
            raise ValueError("capture transaction row unexpectedly permits trade instruction")
    if len(keys) != len(set(keys)):
        raise ValueError("capture transaction contains duplicate candidate_key")


def build_committed_capture(
    *,
    code_head: str,
    as_of_trade_date: str,
    captured_at_utc: str,
    instrument_count: int,
    successful_instruments: int,
    failed_instruments: int,
    worktree_clean: bool,
    journal_rows: Iterable[dict[str, Any]],
) -> CommittedCapture:
    rows = [dict(row) for row in journal_rows]
    rows.sort(key=lambda row: str(row.get("candidate_key") or ""))
    if not code_head:
        raise ValueError("capture transaction requires code_head")
    if not as_of_trade_date:
        raise ValueError("capture transaction requires as_of_trade_date")
    if instrument_count <= 0:
        raise ValueError("capture transaction requires positive instrument_count")
    if successful_instruments != instrument_count or failed_instruments != 0:
        raise ValueError("capture transaction requires complete instrument coverage")
    if worktree_clean is not True:
        raise ValueError("capture transaction requires clean worktree")
    _validate_rows(
        code_head=code_head,
        as_of_trade_date=as_of_trade_date,
        journal_rows=rows,
    )
    txid = capture_transaction_id(
        code_head=code_head,
        as_of_trade_date=as_of_trade_date,
        instrument_count=instrument_count,
        successful_instruments=successful_instruments,
        failed_instruments=failed_instruments,
        journal_rows=rows,
    )
    stamped = tuple({**row, "capture_transaction_id": txid} for row in rows)
    return CommittedCapture(
        transaction_id=txid,
        code_head=code_head,
        as_of_trade_date=as_of_trade_date,
        captured_at_utc=captured_at_utc,
        instrument_count=instrument_count,
        successful_instruments=successful_instruments,
        failed_instruments=failed_instruments,
        candidate_count=len(stamped),
        worktree_clean=worktree_clean,
        journal_rows=stamped,
    )


def _capture_filename(capture: CommittedCapture) -> str:
    return f"{capture.as_of_trade_date}__{capture.transaction_id}.json"


def commit_capture_transaction(
    root: str | Path,
    capture: CommittedCapture,
) -> dict[str, Any]:
    target_root = Path(root)
    target_root.mkdir(parents=True, exist_ok=True)
    final_path = target_root / _capture_filename(capture)

    same_date = sorted(target_root.glob(f"{capture.as_of_trade_date}__*.json"))
    for path in same_date:
        if path.name == final_path.name:
            existing = json.loads(path.read_text(encoding="utf-8"))
            existing_txid = str(existing.get("transaction_id") or "")
            if existing_txid != capture.transaction_id:
                raise ValueError(
                    f"committed capture transaction-id drift for {capture.as_of_trade_date}"
                )
            existing_identity = capture_transaction_id(
                code_head=str(existing.get("code_head") or ""),
                as_of_trade_date=str(existing.get("as_of_trade_date") or ""),
                instrument_count=int(existing.get("instrument_count") or 0),
                successful_instruments=int(existing.get("successful_instruments") or 0),
                failed_instruments=int(existing.get("failed_instruments") or 0),
                journal_rows=existing.get("journal_rows") or [],
            )
            if existing_identity != capture.transaction_id:
                raise ValueError(
                    f"committed capture payload drift for {capture.as_of_trade_date}"
                )
            return {
                "status": "already_committed",
                "transaction_id": capture.transaction_id,
                "path": str(final_path),
            }
        raise ValueError(
            f"capture date {capture.as_of_trade_date} already has another committed transaction: {path.name}"
        )

    tmp_path = target_root / f".{final_path.name}.tmp"
    encoded = (_canonical_json(capture.as_payload()) + "\n").encode("utf-8")
    with tmp_path.open("wb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, final_path)
    return {
        "status": "committed",
        "transaction_id": capture.transaction_id,
        "path": str(final_path),
    }


def read_committed_captures(root: str | Path) -> list[dict[str, Any]]:
    target_root = Path(root)
    if not target_root.exists():
        return []
    captures: list[dict[str, Any]] = []
    dates: set[str] = set()
    for path in sorted(target_root.glob("*.json")):
        if path.name.startswith("."):
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") != "committed":
            raise ValueError(f"capture transaction is not committed: {path}")
        if int(payload.get("schema_version") or 0) != CAPTURE_TRANSACTION_SCHEMA_VERSION:
            raise ValueError(f"unsupported capture transaction schema: {path}")
        as_of = str(payload.get("as_of_trade_date") or "")
        txid = str(payload.get("transaction_id") or "")
        rows = [dict(row) for row in payload.get("journal_rows") or []]
        expected = capture_transaction_id(
            code_head=str(payload.get("code_head") or ""),
            as_of_trade_date=as_of,
            instrument_count=int(payload.get("instrument_count") or 0),
            successful_instruments=int(payload.get("successful_instruments") or 0),
            failed_instruments=int(payload.get("failed_instruments") or 0),
            journal_rows=rows,
        )
        if txid != expected:
            raise ValueError(f"capture transaction id mismatch: {path}")
        if as_of in dates:
            raise ValueError(f"multiple committed capture transactions on {as_of}")
        dates.add(as_of)
        _validate_rows(
            code_head=str(payload.get("code_head") or ""),
            as_of_trade_date=as_of,
            journal_rows=rows,
        )
        if int(payload.get("candidate_count") or 0) != len(rows):
            raise ValueError(f"capture transaction candidate_count mismatch: {path}")
        captures.append(payload)
    captures.sort(key=lambda item: str(item.get("as_of_trade_date")))
    return captures


def committed_capture_view(
    *,
    legacy_journal_rows: Iterable[dict[str, Any]],
    capture_rows: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    legacy = [dict(row) for row in legacy_journal_rows]
    captures = [dict(row) for row in capture_rows]
    if not captures:
        return legacy, []
    first_capture_date = min(str(item["as_of_trade_date"]) for item in captures)
    legacy_only = [
        row
        for row in legacy
        if str(row.get("as_of_trade_date") or "") < first_capture_date
    ]
    journal_rows = list(legacy_only)
    manifest_rows: list[dict[str, Any]] = []
    for capture in sorted(captures, key=lambda item: str(item["as_of_trade_date"])):
        txid = str(capture["transaction_id"])
        for row in capture.get("journal_rows") or []:
            journal_rows.append({**dict(row), "capture_transaction_id": txid})
        manifest_rows.append({
            "capture_transaction_id": txid,
            "code_head": capture["code_head"],
            "as_of_trade_date": capture["as_of_trade_date"],
            "captured_at_utc": capture["captured_at_utc"],
            "instrument_count": capture["instrument_count"],
            "successful_instruments": capture["successful_instruments"],
            "failed_instruments": capture["failed_instruments"],
            "candidate_count": capture["candidate_count"],
            "worktree_clean": capture["worktree_clean"],
            "status": "pass",
            "alpha_inference_allowed": False,
            "is_trade_instruction": False,
        })
    return journal_rows, manifest_rows


def _legacy_baseline_path(root: str | Path) -> Path:
    return Path(root) / "legacy_baseline.json"


def _legacy_baseline_id(rows: Iterable[dict[str, Any]]) -> str:
    materialized = [dict(row) for row in rows]
    materialized.sort(
        key=lambda row: (
            str(row.get("as_of_trade_date") or ""),
            str(row.get("candidate_key") or ""),
        )
    )
    return sha256(_canonical_json(materialized).encode("utf-8")).hexdigest()[:24]


def freeze_legacy_baseline(
    root: str | Path,
    rows: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    target_root = Path(root)
    target_root.mkdir(parents=True, exist_ok=True)
    materialized = [dict(row) for row in rows]
    materialized.sort(
        key=lambda row: (
            str(row.get("as_of_trade_date") or ""),
            str(row.get("candidate_key") or ""),
        )
    )
    baseline_id = _legacy_baseline_id(materialized)
    payload = {
        "schema_version": 1,
        "status": "frozen_legacy_baseline",
        "baseline_id": baseline_id,
        "row_count": len(materialized),
        "journal_rows": materialized,
        "alpha_inference_allowed": False,
        "is_trade_instruction": False,
    }
    final_path = _legacy_baseline_path(target_root)
    if final_path.exists():
        existing = json.loads(final_path.read_text(encoding="utf-8"))
        if str(existing.get("baseline_id") or "") != baseline_id:
            raise ValueError("legacy baseline is already frozen with different evidence")
        return {
            "status": "already_frozen",
            "baseline_id": baseline_id,
            "path": str(final_path),
        }
    tmp_path = target_root / ".legacy_baseline.json.tmp"
    encoded = (_canonical_json(payload) + "\n").encode("utf-8")
    with tmp_path.open("wb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, final_path)
    return {
        "status": "frozen",
        "baseline_id": baseline_id,
        "path": str(final_path),
    }


def read_frozen_legacy_baseline(root: str | Path) -> list[dict[str, Any]]:
    path = _legacy_baseline_path(root)
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "frozen_legacy_baseline":
        raise ValueError("legacy baseline status is invalid")
    rows = [dict(row) for row in payload.get("journal_rows") or []]
    expected = _legacy_baseline_id(rows)
    if str(payload.get("baseline_id") or "") != expected:
        raise ValueError("legacy baseline identity mismatch")
    if int(payload.get("row_count") or 0) != len(rows):
        raise ValueError("legacy baseline row_count mismatch")
    if payload.get("alpha_inference_allowed") is not False:
        raise ValueError("legacy baseline unexpectedly permits alpha inference")
    if payload.get("is_trade_instruction") is not False:
        raise ValueError("legacy baseline unexpectedly permits trade instruction")
    return rows
