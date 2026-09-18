from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from .outcome_evaluator import canonical_market_path_hash


OUTCOME_SNAPSHOT_SCHEMA_VERSION = 2
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
    outcome_engine_contract_version: int
    outcome_engine_fingerprint: str
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
    outcome_engine_contract_version: int,
    outcome_engine_fingerprint: str,
) -> list[dict[str, Any]]:
    materialized = [dict(item) for item in results]
    if not materialized:
        raise ValueError("outcome snapshot requires at least one candidate result")

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
            raise ValueError(f"outcome result as-of drift for {key}")
        if str(item.get("outcome_protocol_id") or "") != outcome_protocol_id:
            raise ValueError(f"outcome protocol id drift for {key}")
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
        if int(item.get("outcome_engine_contract_version") or 0) != (
            outcome_engine_contract_version
        ):
            raise ValueError(
                f"outcome engine contract drift for {key}"
            )
        if str(item.get("outcome_engine_fingerprint") or "") != (
            outcome_engine_fingerprint
        ):
            raise ValueError(
                f"outcome engine fingerprint drift for {key}"
            )

        path_hash = _validate_hash(
            item.get("market_path_sha256"),
            label=f"market path hash for {key}",
        )
        path_rows = item.get("market_path_rows")
        if not isinstance(path_rows, list) or not path_rows:
            raise ValueError(
                f"outcome result missing canonical market_path_rows: {key}"
            )
        try:
            path_frame = pd.DataFrame(path_rows)
            recomputed_path_hash = canonical_market_path_hash(
                path_frame,
                price_basis_id=str(
                    item.get("current_price_basis_id") or ""
                ),
            )
        except Exception as exc:
            raise ValueError(
                f"invalid outcome market path rows for {key}: "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        if recomputed_path_hash != path_hash:
            raise ValueError(
                f"outcome market path hash mismatch for {key}"
            )
        expected_dates = [
            str(row.get("trade_date") or "")
            for row in path_rows
        ]
        if item.get("market_path_trade_dates") != expected_dates:
            raise ValueError(
                f"outcome market path date list mismatch for {key}"
            )
        if int(item.get("market_path_traded_bar_count") or 0) != len(
            path_rows
        ):
            raise ValueError(
                f"outcome market path bar count mismatch for {key}"
            )

        prohibited = _walk_keys(item).intersection(
            _PROHIBITED_RESULT_KEYS
        )
        if prohibited:
            raise ValueError(
                f"prohibited outcome result keys for {key}: "
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


def _engine_identity_from_results(
    results: Iterable[dict[str, Any]],
) -> tuple[int, str]:
    materialized = [dict(item) for item in results]
    if not materialized:
        raise ValueError("outcome snapshot requires candidate results")
    pairs = {
        (
            int(item.get("outcome_engine_contract_version") or 0),
            str(item.get("outcome_engine_fingerprint") or ""),
        )
        for item in materialized
    }
    if len(pairs) != 1:
        raise ValueError("mixed outcome engine identity inside one snapshot")
    contract_version, fingerprint = next(iter(pairs))
    if contract_version <= 0:
        raise ValueError("invalid outcome engine contract version")
    _validate_hash(fingerprint, label="outcome engine fingerprint")
    return contract_version, fingerprint


def outcome_snapshot_id(
    *,
    outcome_as_of_trade_date: str,
    outcome_protocol_id: str,
    outcome_protocol_fingerprint: str,
    capture_methodology_fingerprint: str,
    outcome_engine_contract_version: int,
    outcome_engine_fingerprint: str,
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
    engine_fp = _validate_hash(
        outcome_engine_fingerprint,
        label="outcome engine fingerprint",
    )
    if int(outcome_engine_contract_version) <= 0:
        raise ValueError("invalid outcome engine contract version")

    normalized = _normalize_results(
        results,
        outcome_as_of_trade_date=outcome_as_of_trade_date,
        outcome_protocol_id=outcome_protocol_id,
        outcome_protocol_fingerprint=protocol_fp,
        capture_methodology_fingerprint=methodology_fp,
        outcome_engine_contract_version=int(
            outcome_engine_contract_version
        ),
        outcome_engine_fingerprint=engine_fp,
    )
    identity = {
        "schema_version": int(schema_version),
        "outcome_as_of_trade_date": outcome_as_of_trade_date,
        "outcome_protocol_id": outcome_protocol_id,
        "outcome_protocol_fingerprint": protocol_fp,
        "capture_methodology_fingerprint": methodology_fp,
        "outcome_engine_contract_version": int(
            outcome_engine_contract_version
        ),
        "outcome_engine_fingerprint": engine_fp,
        "result_count": len(normalized),
        "results": normalized,
    }
    return sha256(
        _canonical_json(identity).encode("utf-8")
    ).hexdigest()[:24]


def build_outcome_snapshot(
    *,
    outcome_as_of_trade_date: str,
    outcome_protocol_id: str,
    outcome_protocol_fingerprint: str,
    capture_methodology_fingerprint: str,
    results: Iterable[dict[str, Any]],
) -> OutcomeSnapshot:
    materialized = [dict(item) for item in results]
    engine_version, engine_fingerprint = _engine_identity_from_results(
        materialized
    )
    protocol_fp = _validate_hash(
        outcome_protocol_fingerprint,
        label="outcome protocol fingerprint",
    )
    methodology_fp = _validate_hash(
        capture_methodology_fingerprint,
        label="capture methodology fingerprint",
    )
    normalized = _normalize_results(
        materialized,
        outcome_as_of_trade_date=outcome_as_of_trade_date,
        outcome_protocol_id=outcome_protocol_id,
        outcome_protocol_fingerprint=protocol_fp,
        capture_methodology_fingerprint=methodology_fp,
        outcome_engine_contract_version=engine_version,
        outcome_engine_fingerprint=engine_fingerprint,
    )
    snapshot_id = outcome_snapshot_id(
        outcome_as_of_trade_date=outcome_as_of_trade_date,
        outcome_protocol_id=outcome_protocol_id,
        outcome_protocol_fingerprint=protocol_fp,
        capture_methodology_fingerprint=methodology_fp,
        outcome_engine_contract_version=engine_version,
        outcome_engine_fingerprint=engine_fingerprint,
        results=normalized,
    )
    return OutcomeSnapshot(
        snapshot_id=snapshot_id,
        outcome_as_of_trade_date=outcome_as_of_trade_date,
        outcome_protocol_id=outcome_protocol_id,
        outcome_protocol_fingerprint=protocol_fp,
        capture_methodology_fingerprint=methodology_fp,
        outcome_engine_contract_version=engine_version,
        outcome_engine_fingerprint=engine_fingerprint,
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
    if (
        int(payload.get("outcome_engine_contract_version") or 0)
        != snapshot.outcome_engine_contract_version
    ):
        raise ValueError("outcome snapshot engine contract mismatch")
    if (
        str(payload.get("outcome_engine_fingerprint") or "")
        != snapshot.outcome_engine_fingerprint
    ):
        raise ValueError("outcome snapshot engine fingerprint mismatch")
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


def _chain_identity(
    snapshot: dict[str, Any],
) -> tuple[object, ...]:
    return (
        snapshot.get("outcome_protocol_id"),
        snapshot.get("outcome_protocol_fingerprint"),
        snapshot.get("capture_methodology_fingerprint"),
        snapshot.get("outcome_engine_contract_version"),
        snapshot.get("outcome_engine_fingerprint"),
    )


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

    chain = read_outcome_snapshots(directory)
    if chain:
        expected_identity = _chain_identity(chain[0])
        if _chain_identity(payload) != expected_identity:
            raise ValueError(
                "outcome chain identity drift; start an explicitly "
                "versioned outcome epoch instead of mixing evidence"
            )

    existing_same_date = [
        item
        for item in chain
        if str(item.get("outcome_as_of_trade_date") or "")
        == date_value
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
    if existing_same_date:
        prior_payload = existing_same_date[0]
        raise ValueError(
            "outcome data drift for same as-of date: "
            f"existing={prior_payload['snapshot_id']} "
            f"new={payload['snapshot_id']}"
        )
    if chain:
        latest_date = str(chain[-1]["outcome_as_of_trade_date"])
        if date_value < latest_date:
            raise ValueError(
                "outcome snapshot chain forbids historical backfill"
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
