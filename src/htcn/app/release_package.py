from __future__ import annotations

import json
import shutil
import tempfile
import tomllib
import zipfile
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from htcn.app.evidence_identity import read_code_identity
from htcn.app.release_identity import (
    RELEASE_MANIFEST_NAME,
    build_release_manifest,
    sha256_file,
    verify_release_identity,
    write_release_manifest,
)

DEFAULT_INCLUDE_ROOTS = (
    "src",
    "scripts",
    "services",
    "research",
    "governance/acceptance",
    "apps/web/dist",
)
DEFAULT_INCLUDE_FILES = (
    "pyproject.toml",
    "requirements-dev.lock",
    "uv.lock",
    "README.md",
    "OPERATOR_GUIDE.md",
    "RECOVERY_CONTRACT.md",
    "governance/STABLE_RELEASE.json",
    "governance/OPEN_ISSUES.json",
    "governance/PROJECT_STATE.json",
    "governance/MILESTONES.json",
    "governance/SOURCE_COVERAGE.json",
    "governance/PRODUCT_COMPLETION_POLICY.json",
    "governance/QUALITY_BASELINE.json",
    "启动HT-CN.bat",
    "安装HT-CN.bat",
    "停止HT-CN.bat",
    "更新HT-CN.bat",
    "备份HT-CN.bat",
    "恢复HT-CN.bat",
)
IGNORED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


def _ignored(path: Path) -> bool:
    return (
        any(part in IGNORED_PARTS or part.endswith(".egg-info") for part in path.parts)
        or path.suffix.lower() in IGNORED_SUFFIXES
        or path.name == ".DS_Store"
    )


def _safe_member(name: str) -> str:
    text = str(name).replace("\\", "/").strip()
    path = PurePosixPath(text)
    if not text or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe package member: {name!r}")
    return path.as_posix()


def project_version(root: str | Path) -> str:
    payload = tomllib.loads((Path(root) / "pyproject.toml").read_text(encoding="utf-8"))
    value = str((payload.get("project") or {}).get("version") or "").strip()
    if not value:
        raise ValueError("project.version missing from pyproject.toml")
    return value


def collect_release_files(
    root: str | Path,
    *,
    include_roots: Sequence[str] = DEFAULT_INCLUDE_ROOTS,
    include_files: Sequence[str] = DEFAULT_INCLUDE_FILES,
) -> tuple[str, ...]:
    base = Path(root)
    rows: list[str] = []
    for raw in include_roots:
        target = base / raw
        if not target.exists():
            if raw == "apps/web/dist":
                raise FileNotFoundError("apps/web/dist missing; build Web before release packaging")
            continue
        for path in sorted(item for item in target.rglob("*") if item.is_file()):
            relative = path.relative_to(base)
            if _ignored(relative):
                continue
            rows.append(relative.as_posix())
    for raw in include_files:
        target = base / raw
        if target.is_file():
            rows.append(target.relative_to(base).as_posix())
    return tuple(sorted(set(rows)))


def _write_deterministic_zip(root: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            relative = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())


def build_release_package(
    *,
    root: str | Path,
    output: str | Path,
    release_head: str,
    attestations: Mapping[str, Any],
    release_version: str | None = None,
    include_roots: Sequence[str] = DEFAULT_INCLUDE_ROOTS,
    include_files: Sequence[str] = DEFAULT_INCLUDE_FILES,
) -> dict[str, object]:
    base = Path(root)
    identity = read_code_identity(base)
    if identity.head != release_head:
        raise RuntimeError(
            f"release source HEAD mismatch: identity={identity.head} requested={release_head}"
        )
    if not identity.worktree_clean:
        raise RuntimeError(f"release source is not clean: {list(identity.dirty_paths)}")

    version = release_version or project_version(base)
    relative_files = collect_release_files(
        base,
        include_roots=include_roots,
        include_files=include_files,
    )

    with tempfile.TemporaryDirectory(prefix="htcn-release-") as temp:
        stage = Path(temp)
        for relative in relative_files:
            source = base / relative
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

        manifest = build_release_manifest(
            root=stage,
            release_head=release_head,
            release_version=version,
            relative_files=relative_files,
            protected_roots=include_roots,
            attestations=attestations,
        )
        manifest_path = write_release_manifest(stage, manifest)
        verified = verify_release_identity(stage, manifest_path)
        if not verified.verified:
            raise RuntimeError(
                "staged release identity verification failed: "
                + ",".join(verified.errors)
            )
        _write_deterministic_zip(stage, Path(output))

    return {
        "schema_version": 1,
        "status": "built",
        "release_head": release_head,
        "release_version": version,
        "file_count": len(relative_files),
        "identity_fingerprint": manifest["identity_fingerprint"],
        "package_path": str(Path(output)),
        "package_sha256": sha256_file(output),
        "private_market_data_included": False,
        "mutable_data_included": False,
    }


def verify_release_package(path: str | Path) -> dict[str, object]:
    package = Path(path)
    with tempfile.TemporaryDirectory(prefix="htcn-release-verify-") as temp:
        stage = Path(temp)
        with zipfile.ZipFile(package, "r") as archive:
            members = [_safe_member(info.filename) for info in archive.infolist() if not info.is_dir()]
            if len(members) != len(set(members)):
                raise ValueError("duplicate package member")
            for info in archive.infolist():
                if info.is_dir():
                    continue
                safe = _safe_member(info.filename)
                target = stage / safe
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info, "r") as source, target.open("wb") as handle:
                    shutil.copyfileobj(source, handle)

        verification = verify_release_identity(stage)
        if not verification.verified:
            return {
                "schema_version": 1,
                "status": "invalid",
                "verified": False,
                "package_sha256": sha256_file(package),
                "identity": verification.as_payload(),
            }
        manifest = json.loads((stage / RELEASE_MANIFEST_NAME).read_text(encoding="utf-8"))
        expected_members = {
            RELEASE_MANIFEST_NAME,
            *[
                str(row["path"])
                for row in manifest.get("protected_files") or []
                if isinstance(row, dict) and row.get("path")
            ],
        }
        actual_members = set(members)
        extra = sorted(actual_members - expected_members)
        missing = sorted(expected_members - actual_members)
        verified = not extra and not missing
        return {
            "schema_version": 1,
            "status": "verified" if verified else "invalid",
            "verified": verified,
            "package_sha256": sha256_file(package),
            "release_head": verification.release_head,
            "release_version": verification.release_version,
            "identity_fingerprint": verification.identity_fingerprint,
            "file_count": len(expected_members) - 1,
            "extra_members": extra,
            "missing_members": missing,
        }
