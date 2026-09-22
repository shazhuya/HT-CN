from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any

RELEASE_MANIFEST_NAME = "HTCN_RELEASE_IDENTITY.json"
IGNORED_PARTS = {
    ".git",
    ".venv",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


@dataclass(frozen=True, slots=True)
class ReleaseIdentityVerification:
    verified: bool
    status: str
    release_head: str | None
    release_version: str | None
    identity_fingerprint: str | None
    manifest_sha256: str | None
    changed_files: tuple[str, ...]
    missing_files: tuple[str, ...]
    unexpected_files: tuple[str, ...]
    errors: tuple[str, ...]
    attestations: dict[str, Any]

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: str | Path) -> str:
    target = Path(path)
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        dict(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _safe_relative(value: object) -> str | None:
    text = str(value or "").replace("\\", "/").strip()
    if not text:
        return None
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts:
        return None
    return path.as_posix()


def _ignored(relative: Path) -> bool:
    return (
        any(part in IGNORED_PARTS or part.endswith(".egg-info") for part in relative.parts)
        or relative.suffix.lower() in IGNORED_SUFFIXES
        or relative.name == ".DS_Store"
    )


def enumerate_protected_files(
    root: str | Path,
    protected_roots: Sequence[str],
) -> tuple[str, ...]:
    base = Path(root)
    rows: list[str] = []
    for raw in protected_roots:
        safe = _safe_relative(raw)
        if safe is None:
            continue
        target = base / safe
        if not target.exists():
            continue
        if target.is_file():
            relative = target.relative_to(base)
            if not _ignored(relative):
                rows.append(relative.as_posix())
            continue
        for path in sorted(item for item in target.rglob("*") if item.is_file()):
            relative = path.relative_to(base)
            if _ignored(relative):
                continue
            rows.append(relative.as_posix())
    return tuple(sorted(set(rows)))


def build_release_manifest(
    *,
    root: str | Path,
    release_head: str,
    release_version: str,
    relative_files: Sequence[str],
    protected_roots: Sequence[str],
    attestations: Mapping[str, Any],
) -> dict[str, Any]:
    base = Path(root)
    head = str(release_head).strip()
    version = str(release_version).strip()
    if not head:
        raise ValueError("release_head is required")
    if not version:
        raise ValueError("release_version is required")

    records: list[dict[str, object]] = []
    seen: set[str] = set()
    for raw in sorted(relative_files):
        safe = _safe_relative(raw)
        if safe is None:
            raise ValueError(f"unsafe release path: {raw!r}")
        if safe == RELEASE_MANIFEST_NAME:
            continue
        if safe in seen:
            continue
        path = base / safe
        if not path.is_file():
            raise FileNotFoundError(f"release file missing: {safe}")
        seen.add(safe)
        records.append(
            {
                "path": safe,
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
            }
        )

    roots = []
    for raw in protected_roots:
        safe = _safe_relative(raw)
        if safe is None:
            raise ValueError(f"unsafe protected root: {raw!r}")
        if safe not in roots:
            roots.append(safe)

    core: dict[str, Any] = {
        "schema_version": 1,
        "release_head": head,
        "release_version": version,
        "protected_roots": sorted(roots),
        "protected_files": records,
        "attestations": dict(attestations),
        "mutable_data_included": False,
        "private_market_data_included": False,
    }
    core["identity_fingerprint"] = sha256_bytes(_canonical_json(core))
    return core


def write_release_manifest(
    root: str | Path,
    payload: Mapping[str, Any],
    *,
    manifest_name: str = RELEASE_MANIFEST_NAME,
) -> Path:
    path = Path(root) / manifest_name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            dict(payload),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def verify_release_identity(
    root: str | Path,
    manifest_path: str | Path | None = None,
) -> ReleaseIdentityVerification:
    base = Path(root)
    path = (
        Path(manifest_path)
        if manifest_path is not None
        else base / RELEASE_MANIFEST_NAME
    )
    if not path.is_file():
        return ReleaseIdentityVerification(
            verified=False,
            status="missing",
            release_head=None,
            release_version=None,
            identity_fingerprint=None,
            manifest_sha256=None,
            changed_files=(),
            missing_files=(),
            unexpected_files=(),
            errors=("release_identity_manifest_missing",),
            attestations={},
        )

    try:
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return ReleaseIdentityVerification(
            verified=False,
            status="invalid",
            release_head=None,
            release_version=None,
            identity_fingerprint=None,
            manifest_sha256=None,
            changed_files=(),
            missing_files=(),
            unexpected_files=(),
            errors=(f"release_identity_unreadable:{type(exc).__name__}",),
            attestations={},
        )
    if not isinstance(payload, dict):
        return ReleaseIdentityVerification(
            verified=False,
            status="invalid",
            release_head=None,
            release_version=None,
            identity_fingerprint=None,
            manifest_sha256=sha256_bytes(raw),
            changed_files=(),
            missing_files=(),
            unexpected_files=(),
            errors=("release_identity_payload_not_object",),
            attestations={},
        )

    errors: list[str] = []
    changed: list[str] = []
    missing: list[str] = []
    declared: set[str] = set()
    release_head = str(payload.get("release_head") or "").strip() or None
    release_version = str(payload.get("release_version") or "").strip() or None
    fingerprint = str(payload.get("identity_fingerprint") or "").strip() or None
    attestations = payload.get("attestations")
    if not isinstance(attestations, dict):
        attestations = {}
        errors.append("release_identity_attestations_invalid")

    if payload.get("schema_version") != 1:
        errors.append("release_identity_schema_unsupported")
    if release_head is None:
        errors.append("release_identity_head_missing")
    if release_version is None:
        errors.append("release_identity_version_missing")

    core = dict(payload)
    core.pop("identity_fingerprint", None)
    expected_fingerprint = sha256_bytes(_canonical_json(core))
    if fingerprint != expected_fingerprint:
        errors.append("release_identity_fingerprint_mismatch")

    rows = payload.get("protected_files")
    if not isinstance(rows, list):
        rows = []
        errors.append("release_identity_file_inventory_invalid")
    for row in rows:
        if not isinstance(row, dict):
            errors.append("release_identity_file_record_invalid")
            continue
        safe = _safe_relative(row.get("path"))
        expected_sha = str(row.get("sha256") or "").strip()
        try:
            expected_size = int(row.get("size"))
        except (TypeError, ValueError):
            expected_size = -1
        if safe is None or not expected_sha or expected_size < 0:
            errors.append("release_identity_file_record_invalid")
            continue
        if safe in declared:
            errors.append(f"release_identity_duplicate_file:{safe}")
            continue
        declared.add(safe)
        target = base / safe
        if not target.is_file():
            missing.append(safe)
            continue
        if target.stat().st_size != expected_size or sha256_file(target) != expected_sha:
            changed.append(safe)

    roots = payload.get("protected_roots")
    protected_roots = [str(item) for item in roots] if isinstance(roots, list) else []
    actual = set(enumerate_protected_files(base, protected_roots))
    unexpected = sorted(actual - declared)

    if missing:
        errors.append("release_identity_files_missing")
    if changed:
        errors.append("release_identity_files_changed")
    if unexpected:
        errors.append("release_identity_unexpected_protected_files")

    verified = not errors
    return ReleaseIdentityVerification(
        verified=verified,
        status="verified" if verified else "invalid",
        release_head=release_head,
        release_version=release_version,
        identity_fingerprint=fingerprint,
        manifest_sha256=sha256_bytes(raw),
        changed_files=tuple(sorted(changed)),
        missing_files=tuple(sorted(missing)),
        unexpected_files=tuple(unexpected),
        errors=tuple(errors),
        attestations=dict(attestations),
    )
