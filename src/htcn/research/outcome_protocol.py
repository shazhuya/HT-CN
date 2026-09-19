from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

OUTCOME_PROTOCOL_V1_ID = "m4-outcome-v1"
OUTCOME_PROTOCOL_V1_SCHEMA_VERSION = 1
OUTCOME_PROTOCOL_V1_CANONICAL_SHA256 = (
    "e9e1ee4b302eb5fc8ef71e9ea9b93289aaf26abd775200aa80737fb3efd882e1"
)

OUTCOME_PROTOCOL_V2_ID = "m4-outcome-v2"
OUTCOME_PROTOCOL_V2_SCHEMA_VERSION = 1
OUTCOME_PROTOCOL_V2_CANONICAL_SHA256 = (
    "5822b302e11d197682dc4bb6d835fb0a3b2d62fc97f788c7a323ecda2770555b"
)

ACTIVE_OUTCOME_PROTOCOL_ID = OUTCOME_PROTOCOL_V2_ID


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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_outcome_protocol_v1_path() -> Path:
    return _repo_root() / "research" / "m4-outcome-protocol-v1.json"


def default_outcome_protocol_v2_path() -> Path:
    return _repo_root() / "research" / "m4-outcome-protocol-v2.json"


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


def _validate_capture_contract(payload: dict[str, Any]) -> None:
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


def _validate_protocol(
    payload: dict[str, Any],
    *,
    expected_id: str,
    expected_schema: int,
    expected_fingerprint: str,
) -> OutcomeProtocolIdentity:
    protocol_id = str(payload.get("protocol_id") or "")
    schema_version = int(payload.get("schema_version") or 0)
    if protocol_id != expected_id:
        raise ValueError(
            f"unexpected M4 outcome protocol id: {protocol_id!r}"
        )
    if schema_version != expected_schema:
        raise ValueError(
            f"unexpected M4 outcome protocol schema: {schema_version}"
        )
    _validate_capture_contract(payload)

    fingerprint = canonical_outcome_protocol_fingerprint(payload)
    if fingerprint != expected_fingerprint:
        raise ValueError(
            f"M4 outcome protocol {expected_id} changed after preregistration: "
            f"{fingerprint} != {expected_fingerprint}"
        )

    return OutcomeProtocolIdentity(
        protocol_id=protocol_id,
        schema_version=schema_version,
        fingerprint=fingerprint,
    )


def validate_outcome_protocol_v1(
    payload: dict[str, Any],
) -> OutcomeProtocolIdentity:
    return _validate_protocol(
        payload,
        expected_id=OUTCOME_PROTOCOL_V1_ID,
        expected_schema=OUTCOME_PROTOCOL_V1_SCHEMA_VERSION,
        expected_fingerprint=OUTCOME_PROTOCOL_V1_CANONICAL_SHA256,
    )


def validate_outcome_protocol_v2(
    payload: dict[str, Any],
) -> OutcomeProtocolIdentity:
    identity = _validate_protocol(
        payload,
        expected_id=OUTCOME_PROTOCOL_V2_ID,
        expected_schema=OUTCOME_PROTOCOL_V2_SCHEMA_VERSION,
        expected_fingerprint=OUTCOME_PROTOCOL_V2_CANONICAL_SHA256,
    )
    if payload.get("supersedes_protocol_id") != OUTCOME_PROTOCOL_V1_ID:
        raise ValueError("M4 outcome protocol v2 supersession boundary drift")
    metrics = payload.get("descriptive_path_metrics")
    if not isinstance(metrics, dict):
        raise ValueError("M4 outcome protocol v2 missing descriptive metrics")
    if metrics.get("excursion_representation") != "nonnegative_magnitude":
        raise ValueError("M4 outcome protocol v2 excursion representation drift")
    if metrics.get("zero_floor") is not True:
        raise ValueError("M4 outcome protocol v2 requires zero-floor excursions")
    return identity


def validate_outcome_protocol(
    payload: dict[str, Any],
) -> OutcomeProtocolIdentity:
    protocol_id = str(payload.get("protocol_id") or "")
    if protocol_id == OUTCOME_PROTOCOL_V1_ID:
        return validate_outcome_protocol_v1(payload)
    if protocol_id == OUTCOME_PROTOCOL_V2_ID:
        return validate_outcome_protocol_v2(payload)
    raise ValueError(f"unsupported M4 outcome protocol: {protocol_id!r}")


def _load(
    target: Path,
    validator,
) -> tuple[dict[str, Any], OutcomeProtocolIdentity]:
    if not target.is_file():
        raise FileNotFoundError(f"missing M4 outcome protocol: {target}")
    payload = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("M4 outcome protocol must be a JSON object")
    identity = validator(payload)
    return payload, identity


def load_outcome_protocol_v1(
    path: str | Path | None = None,
) -> tuple[dict[str, Any], OutcomeProtocolIdentity]:
    target = (
        default_outcome_protocol_v1_path()
        if path is None
        else Path(path)
    )
    return _load(target, validate_outcome_protocol_v1)


def load_outcome_protocol_v2(
    path: str | Path | None = None,
) -> tuple[dict[str, Any], OutcomeProtocolIdentity]:
    target = (
        default_outcome_protocol_v2_path()
        if path is None
        else Path(path)
    )
    return _load(target, validate_outcome_protocol_v2)


def load_outcome_protocol(
    protocol_id: str = ACTIVE_OUTCOME_PROTOCOL_ID,
) -> tuple[dict[str, Any], OutcomeProtocolIdentity]:
    if protocol_id == OUTCOME_PROTOCOL_V1_ID:
        return load_outcome_protocol_v1()
    if protocol_id == OUTCOME_PROTOCOL_V2_ID:
        return load_outcome_protocol_v2()
    raise ValueError(f"unsupported M4 outcome protocol: {protocol_id!r}")
