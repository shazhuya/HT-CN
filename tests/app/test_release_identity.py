from __future__ import annotations

import subprocess
from pathlib import Path

from htcn.app.evidence_identity import read_code_identity
from htcn.app.release_identity import (
    build_release_manifest,
    verify_release_identity,
    write_release_manifest,
)
from htcn.app.release_package import build_release_package, verify_release_package


def _init_git(root: Path) -> str:
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "HTCN Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "release"], cwd=root, check=True, capture_output=True)
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def _minimal_release_tree(root: Path) -> None:
    (root / "src").mkdir(parents=True)
    (root / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "apps" / "web" / "dist").mkdir(parents=True)
    (root / "apps" / "web" / "dist" / "index.html").write_text("<html></html>\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname="ht-cn-test"\nversion="1.2.3"\n',
        encoding="utf-8",
    )
    (root / "启动HT-CN.bat").write_text("@echo off\n", encoding="utf-8")


def test_packaged_identity_verifies_without_git(tmp_path) -> None:
    _minimal_release_tree(tmp_path)
    files = ("src/app.py", "apps/web/dist/index.html", "pyproject.toml", "启动HT-CN.bat")
    manifest = build_release_manifest(
        root=tmp_path,
        release_head="a" * 40,
        release_version="1.2.3",
        relative_files=files,
        protected_roots=("src", "apps/web/dist"),
        attestations={"m4_methodology": {"status": "frozen_match"}},
    )
    write_release_manifest(tmp_path, manifest)

    verification = verify_release_identity(tmp_path)
    identity = read_code_identity(tmp_path)

    assert verification.verified is True
    assert identity.source == "release_manifest"
    assert identity.head == "a" * 40
    assert identity.worktree_clean is True


def test_changed_packaged_code_fails_closed(tmp_path) -> None:
    _minimal_release_tree(tmp_path)
    manifest = build_release_manifest(
        root=tmp_path,
        release_head="b" * 40,
        release_version="1.2.3",
        relative_files=("src/app.py",),
        protected_roots=("src",),
        attestations={},
    )
    write_release_manifest(tmp_path, manifest)
    (tmp_path / "src" / "app.py").write_text("VALUE = 2\n", encoding="utf-8")

    verification = verify_release_identity(tmp_path)
    identity = read_code_identity(tmp_path)

    assert verification.verified is False
    assert verification.changed_files == ("src/app.py",)
    assert identity.source == "release_manifest"
    assert identity.worktree_clean is False
    assert identity.dirty_paths == ("src/app.py",)


def test_unexpected_packaged_python_file_fails_closed(tmp_path) -> None:
    _minimal_release_tree(tmp_path)
    manifest = build_release_manifest(
        root=tmp_path,
        release_head="c" * 40,
        release_version="1.2.3",
        relative_files=("src/app.py",),
        protected_roots=("src",),
        attestations={},
    )
    write_release_manifest(tmp_path, manifest)
    (tmp_path / "src" / "injected.py").write_text("BAD = True\n", encoding="utf-8")

    verification = verify_release_identity(tmp_path)

    assert verification.verified is False
    assert verification.unexpected_files == ("src/injected.py",)


def test_dirty_git_checkout_cannot_be_laundered_by_release_manifest(tmp_path) -> None:
    _minimal_release_tree(tmp_path)
    head = _init_git(tmp_path)
    manifest = build_release_manifest(
        root=tmp_path,
        release_head=head,
        release_version="1.2.3",
        relative_files=("src/app.py",),
        protected_roots=("src",),
        attestations={},
    )
    write_release_manifest(tmp_path, manifest)
    subprocess.run(["git", "add", "HTCN_RELEASE_IDENTITY.json"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "manifest"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "src" / "app.py").write_text("VALUE = 99\n", encoding="utf-8")

    identity = read_code_identity(tmp_path)

    assert identity.source == "git"
    assert identity.worktree_clean is False
    assert "src/app.py" in identity.dirty_paths


def test_release_package_is_deterministic_and_contains_no_data(tmp_path) -> None:
    root = tmp_path / "source"
    root.mkdir()
    _minimal_release_tree(root)
    head = _init_git(root)
    attestations = {
        "m4_methodology": {"status": "frozen_match"},
        "m4_outcome_engine": {"status": "frozen_match"},
    }
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    kwargs = {
        "root": root,
        "release_head": head,
        "release_version": "1.2.3",
        "attestations": attestations,
        "include_roots": ("src", "apps/web/dist"),
        "include_files": ("pyproject.toml", "启动HT-CN.bat"),
    }
    build_release_package(output=first, **kwargs)
    build_release_package(output=second, **kwargs)

    assert first.read_bytes() == second.read_bytes()
    verified = verify_release_package(first)
    assert verified["verified"] is True
    assert verified["release_head"] == head
    assert verified["file_count"] == 4
