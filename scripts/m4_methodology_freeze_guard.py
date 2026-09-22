from __future__ import annotations

import json
import subprocess
from pathlib import Path

from htcn.app.evidence_identity import read_code_identity
from htcn.app.release_identity import verify_release_identity
from htcn.research.methodology_identity import (
    METHODOLOGY_CONTRACT_VERSION,
    METHODOLOGY_RELATIVE_PATHS,
)

FROZEN_METHODOLOGY_COMMIT = "c774c54928c33361952bf1a612a8555633449625"
EXPECTED_CONTRACT_VERSION = 4
EXPECTED_COMPONENT_COUNT = 37


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )


def _release_attestation_errors(payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return ["release_methodology_attestation_missing"]
    errors: list[str] = []
    if payload.get("status") != "frozen_match":
        errors.append("release_methodology_attestation_not_frozen_match")
    if payload.get("frozen_methodology_commit") != FROZEN_METHODOLOGY_COMMIT:
        errors.append("release_methodology_frozen_commit_mismatch")
    if payload.get("methodology_contract_version") != EXPECTED_CONTRACT_VERSION:
        errors.append("release_methodology_contract_version_mismatch")
    if payload.get("methodology_component_count") != EXPECTED_COMPONENT_COUNT:
        errors.append("release_methodology_component_count_mismatch")
    if payload.get("changed_methodology_components") not in ([], ()):
        errors.append("release_methodology_changed_components_not_empty")
    return errors


def build_freeze_guard() -> dict[str, object]:
    errors: list[str] = []
    root = Path(__file__).resolve().parents[1]

    if METHODOLOGY_CONTRACT_VERSION != EXPECTED_CONTRACT_VERSION:
        errors.append(
            "methodology_contract_version_drift:"
            f"{METHODOLOGY_CONTRACT_VERSION}!={EXPECTED_CONTRACT_VERSION}"
        )
    if len(METHODOLOGY_RELATIVE_PATHS) != EXPECTED_COMPONENT_COUNT:
        errors.append(
            "methodology_component_count_drift:"
            f"{len(METHODOLOGY_RELATIVE_PATHS)}!={EXPECTED_COMPONENT_COUNT}"
        )

    missing = [
        relative
        for relative in METHODOLOGY_RELATIVE_PATHS
        if not (root / relative).is_file()
    ]
    if missing:
        errors.append("methodology_component_missing:" + ",".join(sorted(missing)))

    changed: list[str] = []
    identity = read_code_identity(root)
    if identity.source == "release_manifest":
        release = verify_release_identity(root)
        if not release.verified or not identity.worktree_clean:
            errors.append("release_identity_invalid_for_methodology_guard")
        errors.extend(
            _release_attestation_errors(
                release.attestations.get("m4_methodology")
            )
        )
    else:
        ancestor = _git(
            "merge-base",
            "--is-ancestor",
            FROZEN_METHODOLOGY_COMMIT,
            "HEAD",
        )
        if ancestor.returncode != 0:
            errors.append("frozen_methodology_commit_is_not_ancestor")
        if not missing and ancestor.returncode == 0:
            diff = _git(
                "diff",
                "--name-only",
                FROZEN_METHODOLOGY_COMMIT,
                "HEAD",
                "--",
                *METHODOLOGY_RELATIVE_PATHS,
            )
            if diff.returncode != 0:
                errors.append("methodology_component_diff_failed")
            else:
                changed = sorted(
                    line.strip()
                    for line in diff.stdout.splitlines()
                    if line.strip()
                )
                if changed:
                    errors.append(
                        "methodology_components_changed_since_freeze:"
                        + ",".join(changed)
                    )

    return {
        "schema_version": 1,
        "status": "frozen_match" if not errors else "blocked",
        "frozen_methodology_commit": FROZEN_METHODOLOGY_COMMIT,
        "methodology_contract_version": METHODOLOGY_CONTRACT_VERSION,
        "methodology_component_count": len(METHODOLOGY_RELATIVE_PATHS),
        "changed_methodology_components": changed,
        "error_count": len(errors),
        "errors": errors,
        "alpha_inference_allowed": False,
        "is_trade_instruction": False,
    }


def main() -> int:
    payload = build_freeze_guard()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "frozen_match" else 1


if __name__ == "__main__":
    raise SystemExit(main())
