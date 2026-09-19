from __future__ import annotations

import json
import subprocess
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

INTEGRATION_READINESS_SCHEMA_VERSION = 1

EXPECTED_MAIN_HEAD = "e25fd9584008d35ec464c73f91854d12a66f79ff"
EXPECTED_MERGE_BASE = "edec5e21fb9e873daf8fb77fceaa0d89dbbd5b25"
EXPECTED_MAIN_ONLY_COMMITS = (EXPECTED_MAIN_HEAD,)
ALLOWED_MAIN_ONLY_PATHS = ("README.md",)
MINIMUM_LINEAGE_ONLY_COMMITS = 625

REQUIRED_ANCESTOR_CHECKPOINTS: tuple[tuple[str, str], ...] = (
    ("m2_31_source_fidelity", "fbf964fb2230df2dd21138d2d99f037d3b5a382f"),
    ("m3_merge_base", "edec5e21fb9e873daf8fb77fceaa0d89dbbd5b25"),
    ("m4_methodology_freeze", "c774c54928c33361952bf1a612a8555633449625"),
    ("m4_outcome_engine_anchor", "9cbc0d3d30ac5f0a87748a39788cbee04a44bcc8"),
    ("m5_phase14", "c9de28d959b64043663a2bceccb17cc87b8f3756"),
    ("m5_phase15", "cc6fc7dd230f3229f1882d4fb6c50476515af887"),
    ("m5_phase16", "364835c6661050cdda760c2c45a9488143b9a629"),
    ("m5_phase17", "71093b22c1f6efd4ce7faa740a9dd8b2c554db20"),
    ("m5_phase18", "476acfa239fe67111e87a0adce3bb25e085792a7"),
    ("m5_phase19", "03cd1acdf4c60e5e319a4e6d433d8e3336f8b93d"),
)


@dataclass(frozen=True, slots=True)
class IntegrationReadinessContract:
    version: int = 1
    semantics: str = "preserve_ancestry_merge_readiness"
    target_branch: str = "main"
    merge_method_required: str = "merge"
    squash_forbidden: bool = True
    rebase_forbidden: bool = True
    main_movement_requires_reaudit: bool = True
    methodology_provenance_must_remain_ancestor: bool = True
    outcome_engine_provenance_must_remain_ancestor: bool = True
    authoritative_evidence: bool = False
    writes_m4_evidence: bool = False
    mutates_harmonic_identity: bool = False
    mutates_source_raw_prz: bool = False
    mutates_source_lifecycle: bool = False
    is_trade_instruction: bool = False

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class IntegrationSnapshot:
    head: str
    main_ref: str
    main_head: str
    merge_base: str
    main_only_commit_count: int
    lineage_only_commit_count: int
    main_only_commits: tuple[str, ...]
    main_only_paths: tuple[str, ...]
    main_readme_line_count: int
    main_readme_sha256: str
    checkpoint_ancestry: dict[str, bool]
    worktree_clean: bool

    def as_payload(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "main_only_commits": list(self.main_only_commits),
            "main_only_paths": list(self.main_only_paths),
            "checkpoint_ancestry": dict(self.checkpoint_ancestry),
        }


def evaluate_integration_snapshot(
    snapshot: IntegrationSnapshot,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if snapshot.main_head != EXPECTED_MAIN_HEAD:
        errors.append(
            "main_head_moved:"
            f"expected={EXPECTED_MAIN_HEAD}:actual={snapshot.main_head}"
        )
    if snapshot.merge_base != EXPECTED_MERGE_BASE:
        errors.append(
            "merge_base_changed:"
            f"expected={EXPECTED_MERGE_BASE}:actual={snapshot.merge_base}"
        )
    if snapshot.main_only_commit_count != 1:
        errors.append(
            "main_only_commit_count_invalid:"
            f"{snapshot.main_only_commit_count}"
        )
    if snapshot.lineage_only_commit_count < MINIMUM_LINEAGE_ONLY_COMMITS:
        errors.append(
            "lineage_commit_count_too_small:"
            f"{snapshot.lineage_only_commit_count}"
        )
    if snapshot.main_only_commits != EXPECTED_MAIN_ONLY_COMMITS:
        errors.append(
            "main_only_commit_set_changed:"
            + ",".join(snapshot.main_only_commits)
        )
    if set(snapshot.main_only_paths) != set(ALLOWED_MAIN_ONLY_PATHS):
        errors.append(
            "main_only_paths_changed:"
            + ",".join(snapshot.main_only_paths)
        )
    if snapshot.main_readme_line_count != 1:
        errors.append(
            "main_readme_cleanup_shape_changed:"
            f"line_count={snapshot.main_readme_line_count}"
        )
    if not snapshot.worktree_clean:
        errors.append("tracked_worktree_not_clean")

    missing_ancestors = [
        name
        for name, is_ancestor in snapshot.checkpoint_ancestry.items()
        if not is_ancestor
    ]
    if missing_ancestors:
        errors.append(
            "required_checkpoint_not_ancestor:"
            + ",".join(sorted(missing_ancestors))
        )

    expected_names = {name for name, _ in REQUIRED_ANCESTOR_CHECKPOINTS}
    actual_names = set(snapshot.checkpoint_ancestry)
    if actual_names != expected_names:
        missing = sorted(expected_names.difference(actual_names))
        extra = sorted(actual_names.difference(expected_names))
        errors.append(
            "checkpoint_set_mismatch:"
            f"missing={','.join(missing)}:"
            f"extra={','.join(extra)}"
        )

    if snapshot.main_only_paths == ("README.md",):
        warnings.append(
            "main_has_one_allowed_readme_only_commit; "
            "integration must use merge commit so both ancestries survive"
        )

    return {
        "schema_version": INTEGRATION_READINESS_SCHEMA_VERSION,
        "status": "ready" if not errors else "blocked",
        "contract": IntegrationReadinessContract().as_payload(),
        "snapshot": snapshot.as_payload(),
        "errors": errors,
        "warnings": warnings,
        "merge_instruction": {
            "target": "main",
            "method": "merge",
            "squash": False,
            "rebase": False,
            "reason": (
                "Preserve exact M2/M4/M5 ancestry and include the one "
                "main-only README cleanup commit as the second lineage."
            ),
        },
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
        capture_output=True,
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


def _lines(value: str) -> tuple[str, ...]:
    return tuple(
        line.strip()
        for line in value.splitlines()
        if line.strip()
    )


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


def collect_integration_snapshot(
    repo: str | Path,
    *,
    main_ref: str = "origin/main",
) -> IntegrationSnapshot:
    root = Path(repo).resolve()
    head = _git(root, "rev-parse", "HEAD").stdout.strip()
    main_head = _git(root, "rev-parse", main_ref).stdout.strip()
    merge_base = _git(
        root,
        "merge-base",
        main_ref,
        head,
    ).stdout.strip()

    raw_counts = _git(
        root,
        "rev-list",
        "--left-right",
        "--count",
        f"{main_ref}...{head}",
    ).stdout.strip().split()
    if len(raw_counts) != 2:
        raise RuntimeError("git_left_right_count_invalid")
    main_only_count = int(raw_counts[0])
    lineage_only_count = int(raw_counts[1])

    main_only_commits = _lines(
        _git(
            root,
            "rev-list",
            "--reverse",
            f"{head}..{main_ref}",
        ).stdout
    )
    main_only_paths = _lines(
        _git(
            root,
            "diff",
            "--name-only",
            f"{merge_base}..{main_ref}",
        ).stdout
    )

    main_readme = _git(
        root,
        "show",
        f"{main_ref}:README.md",
    ).stdout
    main_readme_lines = [
        line
        for line in main_readme.splitlines()
        if line.strip()
    ]

    tracked_status = _git(
        root,
        "status",
        "--porcelain",
        "--untracked-files=no",
    ).stdout.strip()

    return IntegrationSnapshot(
        head=head,
        main_ref=main_ref,
        main_head=main_head,
        merge_base=merge_base,
        main_only_commit_count=main_only_count,
        lineage_only_commit_count=lineage_only_count,
        main_only_commits=main_only_commits,
        main_only_paths=main_only_paths,
        main_readme_line_count=len(main_readme_lines),
        main_readme_sha256=sha256(
            main_readme.encode("utf-8")
        ).hexdigest(),
        checkpoint_ancestry=_checkpoint_ancestry(
            root,
            REQUIRED_ANCESTOR_CHECKPOINTS,
            head=head,
        ),
        worktree_clean=not tracked_status,
    )


def write_integration_readiness_report(
    *,
    repo: str | Path,
    output: str | Path,
    main_ref: str = "origin/main",
) -> tuple[dict[str, Any], int]:
    snapshot = collect_integration_snapshot(
        repo,
        main_ref=main_ref,
    )
    payload = evaluate_integration_snapshot(snapshot)

    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = Path(repo).resolve() / output_path
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
