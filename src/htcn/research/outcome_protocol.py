from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


OUTCOME_PROTOCOL_V1_ID = "m4-outcome-v1"
OUTCOME_PROTOCOL_V1_SCHEMA_VERSION = 1
OUTCOME_PROTOCOL_V1_CANONICAL_SHA256 = (
    "e9e1ee4b302eb5fc8ef71e9ea9b93289aaf26abd775200aa80737fb3efd882e1"
)


@dataclass(frozen=True, slots=True)
class OutcomeProtocolIdentity:
    protocol_id: str
    schema_version: int
    fingerprint: str

    def as_payload(self) -> dict[str, object]:
        return {
            "protocol_id": self.protocol_id,
            "schema_version": self.schema_version,
            "fingerprint": self.fingerprint,
        }


def default_outcome_protocol_v1_path() -> Path:
    return (
        Path(__file__).resolve().parents[3]
        / "research"
        / "m4-outcome-protocol-v1.json"
    )


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_outcome_protocol_fingerprint(payload: dict[str, Any]) -> str:
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def validate_outcome_protocol_v1(payload: dict[str, Any]) -> OutcomeProtocolIdentity:
    protocol_id = str(payload.get("protocol_id") or "")
    schema_version = int(payload.get("schema_version") or 0)
    if protocol_id != OUTCOME_PROTOCOL_V1_ID:
        raise ValueError(
            f"unexpected M4 outcome protocol id: {protocol_id!r}"
        )
    if schema_version != OUTCOME_PROTOCOL_V1_SCHEMA_VERSION:
        raise ValueError(
            f"unexpected M4 outcome protocol schema: {schema_version}"
        )

    capture = payload.get("capture_contract")
    if not isinstance(capture, dict):
        raise ValueError("M4 outcome protocol missing capture_contract")
    expected_capture = {
        "methodology_contract_version": 4,
        "capture_transaction_schema_version": 5,
        "prospective_observation_schema_version": 4,
        "methodology_component_count": 37,
        "exact_methodology_freeze_commit": (
            "c774c54928c33361952bf1a612a8555633449625"
        ),
    }
    for key, expected in expected_capture.items():
        if capture.get(key) != expected:
            raise ValueError(
                f"M4 outcome protocol capture contract drift: "
                f"{key}={capture.get(key)!r} expected={expected!r}"
            )

    fingerprint = canonical_outcome_protocol_fingerprint(payload)
    if fingerprint != OUTCOME_PROTOCOL_V1_CANONICAL_SHA256:
        raise ValueError(
            "M4 outcome protocol v1 changed after preregistration: "
            f"{fingerprint} != {OUTCOME_PROTOCOL_V1_CANONICAL_SHA256}"
        )

    return OutcomeProtocolIdentity(
        protocol_id=protocol_id,
        schema_version=schema_version,
        fingerprint=fingerprint,
    )


def load_outcome_protocol_v1(
    path: str | Path | None = None,
) -> tuple[dict[str, Any], OutcomeProtocolIdentity]:
    target = (
        default_outcome_protocol_v1_path()
        if path is None
        else Path(path)
    )
    if not target.is_file():
        raise FileNotFoundError(f"missing M4 outcome protocol: {target}")
    payload = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("M4 outcome protocol must be a JSON object")
    identity = validate_outcome_protocol_v1(payload)
    return payload, identity
