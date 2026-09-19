from __future__ import annotations

import json
import subprocess
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

MAIN_RELEASE_INTEGRITY_SCHEMA_VERSION = 1

REQUIRED_RELEASE_ANCESTORS: tuple[tuple[str, str], ...] = (
    ("m2_31_source_fidelity", "fbf964fb2230df2dd21138d2d99f037d3b5a382f"),
    ("m3_merge", "edec5e21fb9e873daf8fb77fceaa0d89dbbd5b25"),
    ("m4_methodology_freeze", "c774c54928c33361952bf1a612a8555633449625"),
    ("m4_outcome_engine_anchor", "9cbc0d3d30ac5f0a87748a39788cbee04a44bcc8"),
    ("m5_phase20_main_merge", "7ed0c56c2fe631f687a16cb8d4922030a21bc80a"),
    ("m5_phase21_main_merge", "d8687f2bcc8d4a9d9b37eeac1430f6f88ff563d3"),
)


@dataclass(frozen=True, slots=True)
class MainReleaseIntegrityContract:
    version: int = 1
    semantics: str = "formal_main_release_integrity"
    runs_on_main_push: bool = True
    runs_on_pull_request_to_main: bool = True
    full_history_required: bool = True
    deterministic_tests_must_pass_first: bool = True
    existing_browser_acceptance_required: bool = True
    phase18_browser_acceptance_required: bool = True
    phase21_browser_acceptance_required: bool = True
    m4_methodology_freeze_required: bool = True
    m4_outcome_engine_freeze_required: bool = True
    provenance_ancestry_required: bool = True
    authoritative_evidence: bool = False
    writes_m4_evidence: bool = False
    mutates_harmonic_identity: bool = False
    mutates_source_raw_prz: bool = False
    mutates_source_lifecycle: bool = False
    is_trade_instruction: bool = False

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MainReleaseSnapshot:
    head: str
    worktree_clean: bool
    checkpoint_ancestry: dict[str, bool]

    def as_payload(self) -> dict[str, Any]:
        return {
            "head": self.head,
            "worktree_clean": self.worktree_clean,
            "checkpoint_ancestry": dict(self.checkpoint_ancestry),
        }


def evaluate_main_release_snapshot(
    snapshot: MainReleaseSnapshot,
) -> dict[str, Any]:
    errors: list[str] = []

    if len(snapshot.head) != 40:
        errors.append("head_sha_invalid")
    if not snapshot.worktree_clean:
        errors.append("tracked_worktree_not_clean")

    expected_names = {name for name, _ in REQUIRED_RELEASE_ANCESTORS}
    actual_names = set(snapshot.checkpoint_ancestry)
    if actual_names != expected_names:
        errors.append(
            "checkpoint_set_mismatch:"
            f"missing={','.join(sorted(expected_names - actual_names))}:"
            f"extra={','.join(sorted(actual_names - expected_names))}"
        )

    missing = sorted(
        name
        for name, is_ancestor in snapshot.checkpoint_ancestry.items()
        if not is_ancestor
    )
    if missing:
        errors.append(
            "required_release_checkpoint_not_ancestor:"
            + ",".join(missing)
        )

    return {
        "schema_version": MAIN_RELEASE_INTEGRITY_SCHEMA_VERSION,
        "status": "ready" if not errors else "blocked",
        "contract": MainReleaseIntegrityContract().as_payload(),
        "snapshot": snapshot.as_payload(),
        "errors": errors,
        "warnings": [],
        "release_gate_claim": (
            "repository_lineage_integrity_only; browser and M4 freeze "
            "results are enforced by sibling CI steps"
        ),
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "is_trade_instruction": False,
    }


def _git(
    repo: Path,
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            "git_failed:"
            + " ".join(args)
            + ":"
            + result.stderr.strip()
        )
    return result


def _checkpoint_ancestry(
    repo: Path,
    checkpoints: Iterable[tuple[str, str]],
    *,
    head: str,
) -> dict[str, bool]:
    result: dict[str, bool] = {}
    for name, commit in checkpoints:
        proc = _git(
            repo,
            "merge-base",
            "--is-ancestor",
            commit,
            head,
            check=False,
        )
        if proc.returncode not in (0, 1):
            raise RuntimeError(
                f"git_ancestor_check_failed:{name}:{proc.stderr.strip()}"
            )
        result[name] = proc.returncode == 0
    return result


def collect_main_release_snapshot(
    repo: str | Path,
) -> MainReleaseSnapshot:
    root = Path(repo).resolve()
    head = _git(root, "rev-parse", "HEAD").stdout.strip()
    tracked_status = _git(
        root,
        "status",
        "--porcelain",
        "--untracked-files=no",
    ).stdout.strip()

    return MainReleaseSnapshot(
        head=head,
        worktree_clean=not tracked_status,
        checkpoint_ancestry=_checkpoint_ancestry(
            root,
            REQUIRED_RELEASE_ANCESTORS,
            head=head,
        ),
    )


def write_main_release_integrity_report(
    *,
    repo: str | Path,
    output: str | Path,
) -> tuple[dict[str, Any], int]:
    root = Path(repo).resolve()
    payload = evaluate_main_release_snapshot(
        collect_main_release_snapshot(root)
    )

    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return payload, 0 if payload["status"] == "ready" else 2
