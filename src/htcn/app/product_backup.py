from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from htcn.app.evidence_identity import read_code_identity
from htcn.app.release_identity import sha256_bytes, sha256_file

BACKUP_MANIFEST_NAME = "_HTCN_BACKUP_MANIFEST.json"
DEFAULT_BACKUP_ENTRIES = (
    "data/research",
    "data/product",
    "data/market/catalog.duckdb",
)
ALLOWED_RESTORE_PREFIXES = (
    "data/research/",
    "data/product/",
    "data/market/catalog.duckdb",
)


def _safe_relative(value: str) -> str:
    text = str(value).replace("\\", "/").strip()
    path = PurePosixPath(text)
    if not text or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe backup path: {value!r}")
    return path.as_posix()


def _allowed_restore_path(relative: str) -> bool:
    return any(
        relative == prefix.rstrip("/") or relative.startswith(prefix)
        for prefix in ALLOWED_RESTORE_PREFIXES
    )


def _collect(root: Path, entries: tuple[str, ...]) -> tuple[str, ...]:
    rows: list[str] = []
    for raw in entries:
        target = root / raw
        if target.is_file():
            rows.append(target.relative_to(root).as_posix())
        elif target.is_dir():
            for path in sorted(item for item in target.rglob("*") if item.is_file()):
                relative = path.relative_to(root)
                if "runtime" in relative.parts or relative.suffix == ".lock":
                    continue
                rows.append(relative.as_posix())
    return tuple(sorted(set(rows)))


def _zip_write_bytes(archive: zipfile.ZipFile, name: str, value: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, value)


def create_product_backup(
    *,
    root: str | Path,
    output: str | Path | None = None,
    entries: tuple[str, ...] = DEFAULT_BACKUP_ENTRIES,
    label: str = "manual",
    now: datetime | None = None,
) -> dict[str, object]:
    base = Path(root)
    timestamp = now or datetime.now(UTC)
    output_path = Path(output) if output is not None else (
        base / "backups" / f"htcn-{timestamp.strftime('%Y%m%dT%H%M%SZ')}-{label}.zip"
    )
    files = _collect(base, entries)
    records = [
        {
            "path": relative,
            "sha256": sha256_file(base / relative),
            "size": (base / relative).stat().st_size,
        }
        for relative in files
    ]
    identity = read_code_identity(base)
    core: dict[str, Any] = {
        "schema_version": 1,
        "created_at_utc": timestamp.isoformat(),
        "label": label,
        "source_head": identity.head,
        "source_identity": identity.source,
        "entries": list(entries),
        "files": records,
    }
    core["inventory_fingerprint"] = sha256_bytes(
        json.dumps(
            core,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    )
    manifest_bytes = (
        json.dumps(core, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for relative in files:
            _zip_write_bytes(archive, relative, (base / relative).read_bytes())
        _zip_write_bytes(archive, BACKUP_MANIFEST_NAME, manifest_bytes)

    return {
        "schema_version": 1,
        "status": "created",
        "path": str(output_path),
        "file_count": len(files),
        "archive_sha256": sha256_file(output_path),
        "source_head": identity.head,
    }


def verify_product_backup(path: str | Path) -> dict[str, object]:
    archive_path = Path(path)
    errors: list[str] = []
    with zipfile.ZipFile(archive_path, "r") as archive:
        names: list[str] = []
        for info in archive.infolist():
            if info.is_dir():
                continue
            try:
                safe = _safe_relative(info.filename)
            except ValueError:
                errors.append("unsafe_archive_member")
                continue
            names.append(safe)
        if BACKUP_MANIFEST_NAME not in names:
            return {
                "verified": False,
                "status": "invalid",
                "errors": ["backup_manifest_missing", *errors],
            }
        try:
            manifest = json.loads(archive.read(BACKUP_MANIFEST_NAME).decode("utf-8"))
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError):
            return {
                "verified": False,
                "status": "invalid",
                "errors": ["backup_manifest_unreadable", *errors],
            }
        if not isinstance(manifest, dict):
            return {
                "verified": False,
                "status": "invalid",
                "errors": ["backup_manifest_invalid", *errors],
            }
        core = dict(manifest)
        fingerprint = str(core.pop("inventory_fingerprint", "") or "")
        expected = sha256_bytes(
            json.dumps(
                core,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        )
        if fingerprint != expected:
            errors.append("backup_manifest_fingerprint_mismatch")

        declared: set[str] = set()
        for row in manifest.get("files") or []:
            if not isinstance(row, dict):
                errors.append("backup_file_record_invalid")
                continue
            try:
                relative = _safe_relative(str(row.get("path") or ""))
            except ValueError:
                errors.append("backup_file_record_unsafe")
                continue
            if not _allowed_restore_path(relative):
                errors.append(f"backup_path_not_allowed:{relative}")
                continue
            declared.add(relative)
            try:
                data = archive.read(relative)
            except KeyError:
                errors.append(f"backup_file_missing:{relative}")
                continue
            if len(data) != int(row.get("size") or -1):
                errors.append(f"backup_file_size_mismatch:{relative}")
            if sha256_bytes(data) != str(row.get("sha256") or ""):
                errors.append(f"backup_file_hash_mismatch:{relative}")

        actual = set(names) - {BACKUP_MANIFEST_NAME}
        if actual != declared:
            errors.append("backup_archive_inventory_mismatch")

    return {
        "schema_version": 1,
        "verified": not errors,
        "status": "verified" if not errors else "invalid",
        "archive_sha256": sha256_file(archive_path),
        "file_count": len(declared),
        "errors": errors,
        "manifest": manifest,
    }


def restore_product_backup(
    *,
    root: str | Path,
    archive_path: str | Path,
    create_pre_restore: bool = True,
) -> dict[str, object]:
    base = Path(root)
    verification = verify_product_backup(archive_path)
    if not verification.get("verified"):
        raise RuntimeError(f"backup verification failed: {verification.get('errors')}")

    pre_restore = None
    if create_pre_restore:
        pre_restore = create_product_backup(
            root=base,
            label="pre-restore",
        )

    with tempfile.TemporaryDirectory(prefix="htcn-restore-") as temp:
        stage = Path(temp)
        with zipfile.ZipFile(archive_path, "r") as archive:
            for row in (verification.get("manifest") or {}).get("files") or []:
                relative = _safe_relative(str(row["path"]))
                target = stage / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(relative, "r") as source, target.open("wb") as handle:
                    shutil.copyfileobj(source, handle)

        for row in (verification.get("manifest") or {}).get("files") or []:
            relative = _safe_relative(str(row["path"]))
            source = stage / relative
            target = base / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(target.suffix + ".restore.tmp")
            shutil.copy2(source, temporary)
            temporary.replace(target)

    return {
        "schema_version": 1,
        "status": "restored",
        "archive": str(Path(archive_path)),
        "file_count": verification["file_count"],
        "pre_restore_backup": None if pre_restore is None else pre_restore["path"],
    }


def prune_backups(root: str | Path, *, keep: int = 7) -> list[str]:
    backup_root = Path(root) / "backups"
    if not backup_root.is_dir():
        return []
    archives = sorted(
        backup_root.glob("htcn-*.zip"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    removed: list[str] = []
    for path in archives[max(0, int(keep)):]:
        path.unlink()
        removed.append(str(path))
    return removed
