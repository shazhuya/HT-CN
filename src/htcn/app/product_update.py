from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path, PurePosixPath

from htcn.app.product_backup import create_product_backup
from htcn.app.release_identity import RELEASE_MANIFEST_NAME, verify_release_identity
from htcn.app.release_package import verify_release_package

DependencyRefresh = Callable[[Path], int]


def _safe_member(value: str) -> str:
    text = str(value).replace("\\", "/").strip()
    path = PurePosixPath(text)
    if not text or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe update member: {value!r}")
    return path.as_posix()


def _manifest_files(root: Path) -> set[str]:
    payload = json.loads((root / RELEASE_MANIFEST_NAME).read_text(encoding="utf-8"))
    return {
        str(row["path"])
        for row in payload.get("protected_files") or []
        if isinstance(row, dict) and row.get("path")
    }


def apply_verified_update(
    *,
    root: str | Path,
    package_path: str | Path,
    dependency_refresh: DependencyRefresh | None = None,
) -> dict[str, object]:
    base = Path(root)
    current = verify_release_identity(base)
    if not current.verified:
        raise RuntimeError("current installation release identity is not verified")
    package = verify_release_package(package_path)
    if not package.get("verified"):
        raise RuntimeError("pending update package is not verified")

    pre_update = create_product_backup(root=base, label="pre-update")
    with tempfile.TemporaryDirectory(prefix="htcn-update-") as temp:
        stage = Path(temp) / "new"
        rollback = Path(temp) / "old"
        stage.mkdir(parents=True)
        rollback.mkdir(parents=True)

        with zipfile.ZipFile(package_path, "r") as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                relative = _safe_member(info.filename)
                target = stage / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info, "r") as source, target.open("wb") as handle:
                    shutil.copyfileobj(source, handle)

        staged = verify_release_identity(stage)
        if not staged.verified:
            raise RuntimeError("staged update release identity is invalid")

        old_files = _manifest_files(base)
        new_files = _manifest_files(stage)
        for relative in sorted(old_files | {RELEASE_MANIFEST_NAME}):
            source = base / relative
            if source.is_file():
                target = rollback / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)

        try:
            for relative in sorted(old_files - new_files):
                target = base / relative
                if target.is_file():
                    target.unlink()
            for relative in sorted(new_files):
                source = stage / relative
                target = base / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_suffix(target.suffix + ".update.tmp")
                shutil.copy2(source, temporary)
                temporary.replace(target)
            shutil.copy2(
                stage / RELEASE_MANIFEST_NAME,
                base / RELEASE_MANIFEST_NAME,
            )

            after = verify_release_identity(base)
            if not after.verified:
                raise RuntimeError("installed update failed release identity verification")
            if dependency_refresh is not None:
                code = int(dependency_refresh(base))
                if code != 0:
                    raise RuntimeError(f"dependency refresh failed with exit code {code}")
        except Exception:
            for relative in sorted(new_files - old_files):
                target = base / relative
                if target.is_file():
                    target.unlink()
            for source in sorted(item for item in rollback.rglob("*") if item.is_file()):
                relative = source.relative_to(rollback)
                target = base / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            raise

    return {
        "schema_version": 1,
        "status": "updated",
        "previous_head": current.release_head,
        "release_head": package.get("release_head"),
        "pre_update_backup": pre_update["path"],
        "package_sha256": package.get("package_sha256"),
    }
