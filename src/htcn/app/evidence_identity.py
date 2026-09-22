from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from htcn.app.release_identity import verify_release_identity

REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True, slots=True)
class CodeIdentity:
    head: str | None
    worktree_clean: bool
    dirty_paths: tuple[str, ...]
    source: str = "git"
    release_manifest_sha256: str | None = None

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


def _git_head(repo: Path) -> str | None:
    try:
        value = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return None
    return value or None


def _git_dirty_paths(repo: Path) -> tuple[str, ...]:
    try:
        output = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=normal"],
            cwd=str(repo),
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return ("<git-status-unavailable>",)
    return tuple(
        line[3:].strip() if len(line) >= 4 else line.strip()
        for line in output.splitlines()
        if line.strip()
    )


def read_code_identity(root: str | Path | None = None) -> CodeIdentity:
    repo = Path(root) if root is not None else REPO_ROOT
    head = _git_head(repo)
    if head is not None:
        dirty = _git_dirty_paths(repo)
        return CodeIdentity(
            head=head,
            worktree_clean=not dirty,
            dirty_paths=dirty,
            source="git",
        )

    release = verify_release_identity(repo)
    if release.verified:
        return CodeIdentity(
            head=release.release_head,
            worktree_clean=True,
            dirty_paths=(),
            source="release_manifest",
            release_manifest_sha256=release.manifest_sha256,
        )
    if release.status != "missing":
        paths = sorted(
            {
                *release.changed_files,
                *release.missing_files,
                *release.unexpected_files,
            }
        )
        dirty = tuple(paths or ["<release-identity-invalid>"])
        return CodeIdentity(
            head=release.release_head,
            worktree_clean=False,
            dirty_paths=dirty,
            source="release_manifest",
            release_manifest_sha256=release.manifest_sha256,
        )
    return CodeIdentity(
        head=None,
        worktree_clean=False,
        dirty_paths=("<git-status-unavailable>",),
        source="unavailable",
    )
