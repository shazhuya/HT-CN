from __future__ import annotations

import json
from pathlib import Path
import subprocess

from htcn.app.main_real_closeout import (
    verify_main_real_closeout,
    write_main_real_closeout_report,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "reports" / "m5-main-real-closeout.json"


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _git_state() -> tuple[str | None, str | None, bool]:
    branch_result = _git("symbolic-ref", "--quiet", "--short", "HEAD")
    head_result = _git("rev-parse", "HEAD")
    status_result = _git("status", "--porcelain")
    branch = (
        branch_result.stdout.strip()
        if branch_result.returncode == 0
        else None
    )
    head = (
        head_result.stdout.strip()
        if head_result.returncode == 0
        else None
    )
    clean = status_result.returncode == 0 and not status_result.stdout.strip()
    return branch or None, head or None, clean


def main() -> int:
    branch, head, clean = _git_state()
    checked = verify_main_real_closeout(
        root=ROOT,
        current_branch=branch,
        current_head=head,
        worktree_clean=clean,
    )
    write_main_real_closeout_report(
        output=OUTPUT,
        verification=checked,
    )
    print(
        json.dumps(
            checked.as_payload(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
    )
    if checked.status == "invalid":
        print(
            "[HT-CN M5 MAIN REAL CLOSEOUT] FAILED -> "
            f"{OUTPUT.relative_to(ROOT)}",
            flush=True,
        )
        return 2
    print(
        "[HT-CN M5 MAIN REAL CLOSEOUT] STRUCTURAL READY"
        + (" WITH WARNINGS" if checked.warning_count else "")
        + f" -> {OUTPUT.relative_to(ROOT)}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
