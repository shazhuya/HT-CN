from __future__ import annotations

import json
from pathlib import Path
import subprocess

from htcn.research.outcome_engine_identity import (
    OUTCOME_ENGINE_CONTRACT_VERSION,
    OUTCOME_ENGINE_RELATIVE_PATHS,
    build_outcome_engine_identity,
)
from htcn.research.outcome_protocol import (
    ACTIVE_OUTCOME_PROTOCOL_ID,
    OUTCOME_PROTOCOL_V2_CANONICAL_SHA256,
    load_outcome_protocol,
)


FROZEN_OUTCOME_ENGINE_COMMIT = "9cbc0d3d30ac5f0a87748a39788cbee04a44bcc8"
EXPECTED_ENGINE_CONTRACT_VERSION = 1
EXPECTED_ENGINE_COMPONENT_COUNT = 4
EXPECTED_ACTIVE_OUTCOME_PROTOCOL_ID = "m4-outcome-v2"
EXPECTED_ACTIVE_OUTCOME_PROTOCOL_FINGERPRINT = (
    "5822b302e11d197682dc4bb6d835fb0a3b2d62fc97f788c7a323ecda2770555b"
)


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )


def build_outcome_engine_freeze_guard() -> dict[str, object]:
    errors: list[str] = []

    if OUTCOME_ENGINE_CONTRACT_VERSION != EXPECTED_ENGINE_CONTRACT_VERSION:
        errors.append(
            "outcome_engine_contract_version_drift:"
            f"{OUTCOME_ENGINE_CONTRACT_VERSION}!="
            f"{EXPECTED_ENGINE_CONTRACT_VERSION}"
        )
    if len(OUTCOME_ENGINE_RELATIVE_PATHS) != EXPECTED_ENGINE_COMPONENT_COUNT:
        errors.append(
            "outcome_engine_component_count_drift:"
            f"{len(OUTCOME_ENGINE_RELATIVE_PATHS)}!="
            f"{EXPECTED_ENGINE_COMPONENT_COUNT}"
        )
    if ACTIVE_OUTCOME_PROTOCOL_ID != EXPECTED_ACTIVE_OUTCOME_PROTOCOL_ID:
        errors.append(
            "active_outcome_protocol_id_drift:"
            f"{ACTIVE_OUTCOME_PROTOCOL_ID}!="
            f"{EXPECTED_ACTIVE_OUTCOME_PROTOCOL_ID}"
        )
    if (
        OUTCOME_PROTOCOL_V2_CANONICAL_SHA256
        != EXPECTED_ACTIVE_OUTCOME_PROTOCOL_FINGERPRINT
    ):
        errors.append("outcome_protocol_v2_constant_drift")

    try:
        protocol, protocol_identity = load_outcome_protocol()
    except Exception as exc:
        protocol = None
        protocol_identity = None
        errors.append(
            "active_outcome_protocol_validation_failed:"
            f"{type(exc).__name__}:{exc}"
        )
    else:
        if protocol_identity.protocol_id != EXPECTED_ACTIVE_OUTCOME_PROTOCOL_ID:
            errors.append("active_outcome_protocol_loaded_id_drift")
        if (
            protocol_identity.fingerprint
            != EXPECTED_ACTIVE_OUTCOME_PROTOCOL_FINGERPRINT
        ):
            errors.append(
                "active_outcome_protocol_loaded_fingerprint_drift"
            )
        if protocol.get("status") != (
            "preregistered_frozen_before_first_prospective_outcome"
        ):
            errors.append("active_outcome_protocol_status_drift")

    try:
        engine_identity = build_outcome_engine_identity()
    except Exception as exc:
        engine_identity = None
        errors.append(
            "outcome_engine_identity_build_failed:"
            f"{type(exc).__name__}:{exc}"
        )

    ancestor = _git(
        "merge-base",
        "--is-ancestor",
        FROZEN_OUTCOME_ENGINE_COMMIT,
        "HEAD",
    )
    if ancestor.returncode != 0:
        errors.append("frozen_outcome_engine_commit_is_not_ancestor")

    root = Path(__file__).resolve().parents[1]
    missing = [
        relative
        for relative in OUTCOME_ENGINE_RELATIVE_PATHS
        if not (root / relative).is_file()
    ]
    if missing:
        errors.append(
            "outcome_engine_component_missing:"
            + ",".join(sorted(missing))
        )

    changed: list[str] = []
    if not missing and ancestor.returncode == 0:
        diff = _git(
            "diff",
            "--name-only",
            FROZEN_OUTCOME_ENGINE_COMMIT,
            "HEAD",
            "--",
            *OUTCOME_ENGINE_RELATIVE_PATHS,
        )
        if diff.returncode != 0:
            errors.append("outcome_engine_component_diff_failed")
        else:
            changed = sorted(
                line.strip()
                for line in diff.stdout.splitlines()
                if line.strip()
            )
            if changed:
                errors.append(
                    "outcome_engine_components_changed_since_freeze:"
                    + ",".join(changed)
                )

    return {
        "schema_version": 1,
        "status": "frozen_match" if not errors else "blocked",
        "frozen_outcome_engine_commit": FROZEN_OUTCOME_ENGINE_COMMIT,
        "outcome_engine_contract_version": OUTCOME_ENGINE_CONTRACT_VERSION,
        "outcome_engine_component_count": len(
            OUTCOME_ENGINE_RELATIVE_PATHS
        ),
        "outcome_engine_fingerprint": (
            None
            if engine_identity is None
            else engine_identity.fingerprint
        ),
        "active_outcome_protocol_id": (
            None
            if protocol_identity is None
            else protocol_identity.protocol_id
        ),
        "active_outcome_protocol_fingerprint": (
            None
            if protocol_identity is None
            else protocol_identity.fingerprint
        ),
        "changed_outcome_engine_components": changed,
        "error_count": len(errors),
        "errors": errors,
        "alpha_inference_allowed": False,
        "is_trade_instruction": False,
    }


def main() -> int:
    payload = build_outcome_engine_freeze_guard()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "frozen_match" else 1


if __name__ == "__main__":
    raise SystemExit(main())
