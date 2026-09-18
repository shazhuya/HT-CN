from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True, slots=True)
class CodeIdentity:
    head: str | None
    worktree_clean: bool
    dirty_paths: tuple[str, ...]

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


def read_code_identity(root: str | Path | None = None) -> CodeIdentity:
    repo = Path(root) if root is not None else REPO_ROOT
    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        head = None

    try:
        output = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=normal"],
            cwd=str(repo),
            text=True,
            stderr=subprocess.DEVNULL,
        )
        dirty = tuple(
            line[3:].strip() if len(line) >= 4 else line.strip()
            for line in output.splitlines()
            if line.strip()
        )
    except Exception:
        dirty = ("<git-status-unavailable>",)

    return CodeIdentity(
        head=head,
        worktree_clean=not dirty,
        dirty_paths=dirty,
    )
