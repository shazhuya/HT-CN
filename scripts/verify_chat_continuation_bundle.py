from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_NAME = "MANIFEST.json"
REQUIRED_MEMBERS = {
    "START_HERE.md",
    "HTCN_NEW_CHAT_PROMPT.md",
    "HTCN_RESUME_PACK.md",
    "canonical/AGENTS.md",
    "canonical/CHAT_CONTINUATION.md",
    "canonical/PROJECT_BLUEPRINT.md",
    "canonical/governance/PROJECT_STATE.json",
}
FORBIDDEN_PREFIXES = (
    "canonical/data/",
    "canonical/artifacts/",
    "canonical/logs/",
    "canonical/.git/",
)


class BundleVerificationError(RuntimeError):
    pass


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _safe_member(name: str) -> bool:
    if not name or "\\" in name:
        return False
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts and "." not in path.parts


def _manifest_entries(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = manifest.get("entries")
    if not isinstance(raw, list):
        raise BundleVerificationError("manifest.entries must be a list")
    entries: dict[str, dict[str, Any]] = {}
    for row in raw:
        if not isinstance(row, dict):
            raise BundleVerificationError("manifest entry must be an object")
        path = row.get("path")
        if not isinstance(path, str) or not _safe_member(path):
            raise BundleVerificationError(f"unsafe manifest path: {path!r}")
        if path in entries:
            raise BundleVerificationError(f"duplicate manifest path: {path}")
        entries[path] = row
    return entries


def verify_bundle(bundle: Path, *, current_root: Path | None = None) -> dict[str, Any]:
    bundle = bundle.resolve()
    if not bundle.is_file():
        raise BundleVerificationError(f"bundle missing: {bundle}")

    with zipfile.ZipFile(bundle) as archive:
        infos = archive.infolist()
        names = [row.filename for row in infos]
        if len(names) != len(set(names)):
            raise BundleVerificationError("bundle contains duplicate ZIP members")
        unsafe = [name for name in names if not _safe_member(name)]
        if unsafe:
            raise BundleVerificationError(f"bundle contains unsafe members: {unsafe}")
        if MANIFEST_NAME not in names:
            raise BundleVerificationError("MANIFEST.json missing")

        try:
            manifest = json.loads(archive.read(MANIFEST_NAME).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BundleVerificationError(f"invalid manifest: {exc}") from exc
        if manifest.get("schema") != 1:
            raise BundleVerificationError("unsupported manifest schema")
        if manifest.get("kind") != "htcn_chat_continuation_bundle":
            raise BundleVerificationError("unexpected manifest kind")

        entries = _manifest_entries(manifest)
        expected_names = {MANIFEST_NAME, *entries}
        if set(names) != expected_names:
            missing = sorted(expected_names - set(names))
            extra = sorted(set(names) - expected_names)
            raise BundleVerificationError(
                f"bundle member set mismatch: missing={missing} extra={extra}"
            )
        missing_required = sorted(REQUIRED_MEMBERS - set(entries))
        if missing_required:
            raise BundleVerificationError(f"required members missing: {missing_required}")
        forbidden = [name for name in entries if name.lower().startswith(FORBIDDEN_PREFIXES)]
        if forbidden:
            raise BundleVerificationError(f"private/runtime paths are forbidden: {forbidden}")

        for name, row in entries.items():
            payload = archive.read(name)
            if row.get("size") != len(payload):
                raise BundleVerificationError(f"size mismatch: {name}")
            if row.get("sha256") != _sha256(payload):
                raise BundleVerificationError(f"sha256 mismatch: {name}")

        try:
            state = json.loads(
                archive.read("canonical/governance/PROJECT_STATE.json").decode("utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BundleVerificationError(f"invalid bundled PROJECT_STATE: {exc}") from exc
        project = manifest.get("project") or {}
        if state.get("state_id") != project.get("state_id"):
            raise BundleVerificationError("manifest state_id does not match PROJECT_STATE")
        current = state.get("current") or {}
        for key in ("phase", "status", "active_change", "active_spec"):
            if current.get(key) != project.get(key):
                raise BundleVerificationError(
                    f"manifest project.{key} does not match PROJECT_STATE"
                )

    if current_root is not None:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=current_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if proc.returncode != 0:
            raise BundleVerificationError("cannot resolve current repository HEAD")
        current_head = proc.stdout.strip()
        manifest_head = str((manifest.get("git") or {}).get("head") or "")
        if current_head != manifest_head:
            raise BundleVerificationError(
                f"bundle HEAD differs from current repository: bundle={manifest_head} "
                f"current={current_head}"
            )

    return {
        "status": "valid",
        "bundle": str(bundle),
        "entry_count": len(entries),
        "head": (manifest.get("git") or {}).get("head"),
        "phase": (manifest.get("project") or {}).get("phase"),
        "project_status": (manifest.get("project") or {}).get("status"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify HT-CN portable chat continuation bundle")
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--require-current-head", action="store_true")
    args = parser.parse_args()
    try:
        report = verify_bundle(
            args.bundle,
            current_root=ROOT if args.require_current_head else None,
        )
    except (BundleVerificationError, zipfile.BadZipFile, OSError) as exc:
        print(f"[HT-CN CHAT CONTINUITY] FATAL: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
