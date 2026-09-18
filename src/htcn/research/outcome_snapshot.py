from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Iterable


OUTCOME_SNAPSHOT_SCHEMA_VERSION = 1
_PROHIBITED_RESULT_KEYS = {
    "trade_entry_price",
    "stop_loss",
    "position_size",
    "fees",
    "execution_pnl",
    "win_loss_label",
    "win_rate",
    "alpha",
    "benchmark_excess_return",
    "p_value",
    "significance_test",
    "buy_sell_ranking",
}


@dataclass(frozen=True, slots=True)
class OutcomeSnapshot:
    snapshot_id: str
    outcome_as_of_trade_date: str
    outcome_protocol_id: str
    outcome_protocol_fingerprint: str
    capture_methodology_fingerprint: str
    result_count: int
    results: tuple[dict[str, Any], ...]
    status: str = "committed"
    schema_version: int = OUTCOME_SNAPSHOT_SCHEMA_VERSION
    evidence_only: bool = True
    is_trade_instruction: bool = False
    alpha_inference_allowed: bool = False

    def as_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["results"] = [dict(item) for item in self.results]
        return payload


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _walk_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(str(key))
            keys.update(_walk_keys(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            keys.update(_walk_keys(item))
    return keys


def _validate_hash(value: object, *, label: str) -> str:
    text = str(value or "")
    if len(text) != 64:
        raise ValueError(f"invalid {label} length")
    try:
        int(text, 16)
    except ValueError as exc:
        raise ValueError(f"invalid {label} encoding") from exc
    return text


def _normalize_results(
    results: Iterable[dict[str, Any]],
    *,
    outcome_as_of_trade_date: str,
    outcome_protocol_id: str,
    outcome_protocol_fingerprint: str,
    capture_methodology_fingerprint: str,
) -> list[dict[str, Any]]:
    materialized = [dict(item) for item in results]
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for item in materialized:
        key = str(item.get("candidate_key") or "")
        if not key:
            raise ValueError("outcome result missing candidate_key")
        if key in seen:
            raise ValueError(
                f"duplicate outcome candidate in snapshot: {key}"
            )
        seen.add(key)
        if str(item.get("outcome_as_of_trade_date") or "") != (
            outcome_as_of_trade_date
        ):
            raise ValueError(
                f"outcome result as-of drift for {key}"
            )
        if str(item.get("outcome_protocol_id") or "") != outcome_protocol_id:
            raise ValueError(
                f"outcome protocol id drift for {key}"
            )
        if str(item.get("outcome_protocol_fingerprint") or "") != (
            outcome_protocol_fingerprint
        ):
            raise ValueError(
                f"outcome protocol fingerprint drift for {key}"
            )
        if str(item.get("capture_methodology_fingerprint") or "") != (
            capture_methodology_fingerprint
        ):
            raise ValueError(
                f"capture methodology fingerprint drift for {key}"
            )
        _validate_hash(
            item.get("market_path_sha256"),
            label=f"market path hash for {key}",
        )
        prohibited = _walk_keys(item).intersection(
            _PROHIBITED_RESULT_KEYS
        )
        if prohibited:
            raise ValueError(
                f"prohibited outcome-v1 result keys for {key}: "
                f"{sorted(prohibited)}"
            )
        interpretation = item.get("interpretation") or {}
        if interpretation.get("evidence_only") is not True:
            raise ValueError(
                f"outcome result is not evidence-only: {key}"
            )
        if interpretation.get("is_trade_instruction") is not False:
            raise ValueError(
                f"outcome result crossed trade-instruction boundary: {key}"
            )
        if interpretation.get("alpha_inference_allowed") is not False:
            raise ValueError(
                f"outcome result crossed alpha boundary: {key}"
            )
        normalized.append(item)
    normalized.sort(key=lambda item: str(item["candidate_key"]))
    return normalized


def outcome_snapshot_id(
    *,
    outcome_as_of_trade_date: str,
    outcome_protocol_id: str,
    outcome_protocol_fingerprint: str,
    capture_methodology_fingerprint: str,
    results: Iterable[dict[str, Any]],
    schema_version: int = OUTCOME_SNAPSHOT_SCHEMA_VERSION,
) -> str:
    protocol_fp = _validate_hash(
        outcome_protocol_fingerprint,
        label="outcome protocol fingerprint",
    )
    methodology_fp = _validate_hash(
        capture_methodology_fingerprint,
        label="capture methodology fingerprint",
    )
    normalized = _normalize_results(
        results,
        outcome_as_of_trade_date=outcome_as_of_trade_date,
        outcome_protocol_id=outcome_protocol_id,
        outcome_protocol_fingerprint=protocol_fp,
        capture_methodology_fingerprint=methodology_fp,
    )
    identity = {
        "schema_version": int(schema_version),
        "outcome_as_of_trade_date": outcome_as_of_trade_date,
        "outcome_protocol_id": outcome_protocol_id,
        "outcome_protocol_fingerprint": protocol_fp,
        "capture_methodology_fingerprint": methodology_fp,
        "result_count": len(normalized),
        "results": normalized,
    }
    return sha256(_canonical_json(identity).encode("utf-8")).hexdigest()[:24]


def build_outcome_snapshot(
    *,
    outcome_as_of_trade_date: str,
    outcome_protocol_id: str,
    outcome_protocol_fingerprint: str,
    capture_methodology_fingerprint: str,
    results: Iterable[dict[str, Any]],
) -> OutcomeSnapshot:
    normalized = _normalize_results(
        results,
        outcome_as_of_trade_date=outcome_as_of_trade_date,
        outcome_protocol_id=outcome_protocol_id,
        outcome_protocol_fingerprint=_validate_hash(
            outcome_protocol_fingerprint,
            label="outcome protocol fingerprint",
        ),
        capture_methodology_fingerprint=_validate_hash(
            capture_methodology_fingerprint,
            label="capture methodology fingerprint",
        ),
    )
    snapshot_id = outcome_snapshot_id(
        outcome_as_of_trade_date=outcome_as_of_trade_date,
        outcome_protocol_id=outcome_protocol_id,
        outcome_protocol_fingerprint=outcome_protocol_fingerprint,
        capture_methodology_fingerprint=capture_methodology_fingerprint,
        results=normalized,
    )
    return OutcomeSnapshot(
        snapshot_id=snapshot_id,
        outcome_as_of_trade_date=outcome_as_of_trade_date,
        outcome_protocol_id=outcome_protocol_id,
        outcome_protocol_fingerprint=outcome_protocol_fingerprint,
        capture_methodology_fingerprint=capture_methodology_fingerprint,
        result_count=len(normalized),
        results=tuple(normalized),
    )


def _validate_snapshot_payload(payload: dict[str, Any]) -> dict[str, Any]:
    schema = int(payload.get("schema_version") or 0)
    if schema != OUTCOME_SNAPSHOT_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported outcome snapshot schema: {schema}"
        )
    snapshot = build_outcome_snapshot(
        outcome_as_of_trade_date=str(
            payload.get("outcome_as_of_trade_date") or ""
        ),
        outcome_protocol_id=str(
            payload.get("outcome_protocol_id") or ""
        ),
        outcome_protocol_fingerprint=str(
            payload.get("outcome_protocol_fingerprint") or ""
        ),
        capture_methodology_fingerprint=str(
            payload.get("capture_methodology_fingerprint") or ""
        ),
        results=payload.get("results") or [],
    )
    if str(payload.get("snapshot_id") or "") != snapshot.snapshot_id:
        raise ValueError("outcome snapshot id mismatch")
    if int(payload.get("result_count") or 0) != snapshot.result_count:
        raise ValueError("outcome snapshot result_count mismatch")
    if payload.get("status") != "committed":
        raise ValueError("outcome snapshot status must be committed")
    if payload.get("evidence_only") is not True:
        raise ValueError("outcome snapshot must remain evidence-only")
    if payload.get("is_trade_instruction") is not False:
        raise ValueError("outcome snapshot cannot be a trade instruction")
    if payload.get("alpha_inference_allowed") is not False:
        raise ValueError("outcome snapshot cannot authorize alpha inference")
    return snapshot.as_payload()


def read_outcome_snapshots(root: str | Path) -> list[dict[str, Any]]:
    directory = Path(root)
    if not directory.exists():
        return []
    snapshots: list[dict[str, Any]] = []
    for path in sorted(directory.glob("????-??-??__*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(
                f"outcome snapshot is not a JSON object: {path}"
            )
        validated = _validate_snapshot_payload(payload)
        expected_name = (
            f"{validated['outcome_as_of_trade_date']}__"
            f"{validated['snapshot_id']}.json"
        )
        if path.name != expected_name:
            raise ValueError(
                f"outcome snapshot filename mismatch: {path.name}"
            )
        snapshots.append(validated)

    dates = [
        str(item["outcome_as_of_trade_date"])
        for item in snapshots
    ]
    if len(dates) != len(set(dates)):
        raise ValueError(
            "multiple committed outcome snapshots exist for one as-of date"
        )
    return snapshots


def commit_outcome_snapshot(
    root: str | Path,
    snapshot: OutcomeSnapshot,
) -> dict[str, Any]:
    directory = Path(root)
    directory.mkdir(parents=True, exist_ok=True)
    payload = _validate_snapshot_payload(snapshot.as_payload())
    date_value = str(payload["outcome_as_of_trade_date"])
    target = directory / (
        f"{date_value}__{payload['snapshot_id']}.json"
    )

    existing = [
        path
        for path in directory.glob(f"{date_value}__*.json")
        if path.is_file()
    ]
    if target.exists():
        current = _validate_snapshot_payload(
            json.loads(target.read_text(encoding="utf-8"))
        )
        if _canonical_json(current) != _canonical_json(payload):
            raise ValueError(
                "same outcome snapshot id contains different facts"
            )
        return {
            "status": "already_committed",
            "snapshot_id": payload["snapshot_id"],
            "path": str(target),
        }
    if existing:
        prior = existing[0]
        prior_payload = _validate_snapshot_payload(
            json.loads(prior.read_text(encoding="utf-8"))
        )
        raise ValueError(
            "outcome data drift for same as-of date: "
            f"existing={prior_payload['snapshot_id']} "
            f"new={payload['snapshot_id']}"
        )

    tmp = directory / f".{target.name}.tmp"
    serialized = (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    )
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(serialized)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, target)

    committed = _validate_snapshot_payload(
        json.loads(target.read_text(encoding="utf-8"))
    )
    if _canonical_json(committed) != _canonical_json(payload):
        raise ValueError(
            "outcome snapshot changed during atomic commit"
        )
    return {
        "status": "committed",
        "snapshot_id": payload["snapshot_id"],
        "path": str(target),
    }
