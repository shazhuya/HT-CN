from __future__ import annotations

import subprocess

from htcn.app.evidence_identity import read_code_identity


def test_code_identity_detects_clean_then_dirty_worktree(tmp_path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "HTCN Test"], cwd=tmp_path, check=True)
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    subprocess.run(["git", "add", "a.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)

    clean = read_code_identity(tmp_path)
    assert clean.head is not None
    assert clean.worktree_clean is True
    assert clean.dirty_paths == ()

    (tmp_path / "a.txt").write_text("changed", encoding="utf-8")
    dirty = read_code_identity(tmp_path)
    assert dirty.head == clean.head
    assert dirty.worktree_clean is False
    assert dirty.dirty_paths == ("a.txt",)
