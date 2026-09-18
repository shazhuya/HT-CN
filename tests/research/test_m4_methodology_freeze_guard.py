from __future__ import annotations

import subprocess

import scripts.m4_methodology_freeze_guard as guard


def _completed(returncode: int = 0, stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["git"],
        returncode=returncode,
        stdout=stdout,
        stderr="",
    )


def test_freeze_guard_contract_is_v4_with_37_components(monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_git(*args: str):
        calls.append(args)
        if args[0] == "merge-base":
            return _completed()
        if args[0] == "diff":
            return _completed(stdout="")
        raise AssertionError(args)

    monkeypatch.setattr(guard, "_git", fake_git)
    payload = guard.build_freeze_guard()

    assert payload["status"] == "frozen_match"
    assert payload["methodology_contract_version"] == 4
    assert payload["methodology_component_count"] == 37
    assert payload["changed_methodology_components"] == []
    assert any(call[0] == "merge-base" for call in calls)
    assert any(call[0] == "diff" for call in calls)


def test_freeze_guard_blocks_any_methodology_component_drift(monkeypatch) -> None:
    def fake_git(*args: str):
        if args[0] == "merge-base":
            return _completed()
        if args[0] == "diff":
            return _completed(
                stdout="src/htcn/research/prospective_observations.py\n"
            )
        raise AssertionError(args)

    monkeypatch.setattr(guard, "_git", fake_git)
    payload = guard.build_freeze_guard()

    assert payload["status"] == "blocked"
    assert payload["changed_methodology_components"] == [
        "src/htcn/research/prospective_observations.py"
    ]
    assert any(
        item.startswith("methodology_components_changed_since_freeze:")
        for item in payload["errors"]
    )


def test_freeze_guard_blocks_missing_frozen_ancestor(monkeypatch) -> None:
    def fake_git(*args: str):
        if args[0] == "merge-base":
            return _completed(returncode=1)
        raise AssertionError(args)

    monkeypatch.setattr(guard, "_git", fake_git)
    payload = guard.build_freeze_guard()

    assert payload["status"] == "blocked"
    assert "frozen_methodology_commit_is_not_ancestor" in payload["errors"]
