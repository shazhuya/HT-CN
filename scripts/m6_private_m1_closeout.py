from __future__ import annotations

import json
import subprocess
from pathlib import Path

from htcn.app.private_m1_closeout import (
    build_private_m1_evidence_bundle,
    verify_private_m1_closeout,
    verify_private_m1_evidence_bundle,
)

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "artifacts" / "reports" / "m6-private-m1-closeout.json"
BUNDLE = (
    ROOT
    / "artifacts"
    / "reports"
    / "htcn-m6-private-m1-closeout-evidence.zip"
)
BUNDLE_VERIFY = (
    ROOT
    / "artifacts"
    / "reports"
    / "m6-private-m1-closeout-bundle-verification.json"
)


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
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


def _remote_main_head() -> str | None:
    result = _git("ls-remote", "origin", "refs/heads/main")
    if result.returncode != 0:
        return None
    line = result.stdout.strip().splitlines()
    if len(line) != 1:
        return None
    fields = line[0].split()
    if len(fields) < 1:
        return None
    return fields[0].strip() or None


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(
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
    tmp.replace(path)


def main() -> int:
    branch, head, clean = _git_state()
    remote = _remote_main_head()
    checked = verify_private_m1_closeout(
        root=ROOT,
        current_branch=branch,
        current_head=head,
        worktree_clean=clean,
        remote_main_head=remote,
    )
    _write_json(REPORT, checked.as_payload())
    print(
        json.dumps(
            checked.as_payload(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
    )

    if checked.full_closeout_ready is not True:
        print(
            "[HT-CN M6.2] PRIVATE-M1 CLOSEOUT INVALID -> "
            f"{REPORT.relative_to(ROOT)}",
            flush=True,
        )
        return 2

    bundle = build_private_m1_evidence_bundle(
        root=ROOT,
        verification_report=REPORT,
        output=BUNDLE,
    )
    verified = verify_private_m1_evidence_bundle(BUNDLE)
    _write_json(BUNDLE_VERIFY, verified)
    if verified["status"] != "valid":
        print(
            "[HT-CN M6.2] EVIDENCE BUNDLE INVALID -> "
            f"{BUNDLE_VERIFY.relative_to(ROOT)}",
            flush=True,
        )
        return 2

    print(flush=True)
    print("============================================================", flush=True)
    print("[HT-CN M6.2] PRIVATE-M1 FULL CLOSEOUT READY", flush=True)
    print(
        f"[HT-CN M6.2] trade_date={checked.trade_date} "
        f"main={checked.main_head}",
        flush=True,
    )
    print(
        "[HT-CN M6.2] upload this ONE file for independent acceptance:",
        flush=True,
    )
    print(str(BUNDLE.relative_to(ROOT)), flush=True)
    print(
        f"[HT-CN M6.2] evidence_zip_sha256={bundle['bundle_sha256']}",
        flush=True,
    )
    print("============================================================", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
