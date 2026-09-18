from __future__ import annotations

import json
from pathlib import Path
import subprocess

from htcn.research.methodology_identity import (
    METHODOLOGY_CONTRACT_VERSION,
    METHODOLOGY_RELATIVE_PATHS,
)


FROZEN_METHODOLOGY_COMMIT = "084ddf649e031e8169a761fd3b8578f73b31b5c2"
EXPECTED_CONTRACT_VERSION = 2
EXPECTED_COMPONENT_COUNT = 37


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )


def build_freeze_guard() -> dict[str, object]:
    errors: list[str] = []

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

    ancestor = _git(
        "merge-base",
        "--is-ancestor",
        FROZEN_METHODOLOGY_COMMIT,
        "HEAD",
    )
    if ancestor.returncode != 0:
        errors.append("frozen_methodology_commit_is_not_ancestor")

    missing = [
        relative
        for relative in METHODOLOGY_RELATIVE_PATHS
        if not (Path(__file__).resolve().parents[1] / relative).is_file()
    ]
    if missing:
        errors.append("methodology_component_missing:" + ",".join(sorted(missing)))

    changed: list[str] = []
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
