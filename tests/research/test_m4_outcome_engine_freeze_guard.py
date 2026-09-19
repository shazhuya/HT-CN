from __future__ import annotations

import subprocess

import scripts.m4_outcome_engine_freeze_guard as guard


def _completed(
    returncode: int = 0,
    stdout: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["git"],
        returncode=returncode,
        stdout=stdout,
        stderr="",
    )


def test_outcome_engine_freeze_guard_contract(monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_git(*args: str):
        calls.append(args)
        if args[0] == "merge-base":
            return _completed()
        if args[0] == "diff":
            return _completed(stdout="")
        raise AssertionError(args)

    monkeypatch.setattr(guard, "_git", fake_git)
    payload = guard.build_outcome_engine_freeze_guard()

    assert payload["status"] == "frozen_match"
    assert payload["frozen_outcome_engine_commit"] == (
        "9cbc0d3d30ac5f0a87748a39788cbee04a44bcc8"
    )
    assert payload["outcome_engine_contract_version"] == 1
    assert payload["outcome_engine_component_count"] == 4
    assert payload["active_outcome_protocol_id"] == "m4-outcome-v2"
    assert payload["changed_outcome_engine_components"] == []
    assert any(call[0] == "merge-base" for call in calls)
    assert any(call[0] == "diff" for call in calls)


def test_outcome_engine_guard_blocks_component_drift(monkeypatch) -> None:
    def fake_git(*args: str):
        if args[0] == "merge-base":
            return _completed()
        if args[0] == "diff":
            return _completed(
                stdout="src/htcn/research/outcome_evaluator.py\n"
            )
        raise AssertionError(args)

    monkeypatch.setattr(guard, "_git", fake_git)
    payload = guard.build_outcome_engine_freeze_guard()

    assert payload["status"] == "blocked"
    assert payload["changed_outcome_engine_components"] == [
        "src/htcn/research/outcome_evaluator.py"
    ]
    assert any(
        item.startswith(
            "outcome_engine_components_changed_since_freeze:"
        )
        for item in payload["errors"]
    )


def test_outcome_engine_guard_blocks_missing_anchor(monkeypatch) -> None:
    def fake_git(*args: str):
        if args[0] == "merge-base":
            return _completed(returncode=1)
        raise AssertionError(args)

    monkeypatch.setattr(guard, "_git", fake_git)
    payload = guard.build_outcome_engine_freeze_guard()

    assert payload["status"] == "blocked"
    assert (
        "frozen_outcome_engine_commit_is_not_ancestor"
        in payload["errors"]
    )
