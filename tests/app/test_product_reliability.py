from __future__ import annotations

from datetime import UTC, datetime

import pytest

from htcn.app.product_backup import (
    create_product_backup,
    restore_product_backup,
    verify_product_backup,
)
from htcn.app.product_migration import (
    CURRENT_PRODUCT_STATE_SCHEMA,
    ensure_product_state_schema,
)
from htcn.app.product_supervisor import (
    ChildRuntime,
    RestartPolicy,
    aggregate_supervisor_state,
    child_restart_due,
    mark_child_running,
    record_child_exit,
)


def test_product_state_migration_is_idempotent_and_future_schema_fails(tmp_path) -> None:
    first = ensure_product_state_schema(tmp_path)
    second = ensure_product_state_schema(tmp_path)
    assert first == second
    assert first["schema_version"] == CURRENT_PRODUCT_STATE_SCHEMA

    state = tmp_path / "data/product/PRODUCT_STATE_VERSION.json"
    state.write_text('{"schema_version": 99}\n', encoding="utf-8")
    with pytest.raises(RuntimeError, match="future product state schema"):
        ensure_product_state_schema(tmp_path)


def test_supervisor_backoff_and_crash_loop_are_bounded() -> None:
    policy = RestartPolicy(
        base_delay_seconds=2,
        max_delay_seconds=8,
        max_restarts_in_window=3,
        window_seconds=60,
    )
    child = ChildRuntime(name="api", critical=True)
    mark_child_running(child, pid=100)
    assert child.status == "running"

    record_child_exit(child, exit_code=1, now_monotonic=10, policy=policy)
    assert child.status == "backoff"
    assert child.next_restart_at_monotonic == 12
    assert child_restart_due(child, now_monotonic=11) is False
    assert child_restart_due(child, now_monotonic=12) is True

    mark_child_running(child, pid=101)
    record_child_exit(child, exit_code=1, now_monotonic=20, policy=policy)
    mark_child_running(child, pid=102)
    record_child_exit(child, exit_code=1, now_monotonic=30, policy=policy)
    assert child.status == "crash_loop"
    assert aggregate_supervisor_state([child]) == "blocked"


def test_supervisor_noncritical_backoff_is_degraded() -> None:
    api = ChildRuntime(name="api", critical=True)
    market = ChildRuntime(name="market", critical=False, status="backoff")
    mark_child_running(api, pid=1)
    assert aggregate_supervisor_state([api, market]) == "degraded"


def test_backup_round_trip_and_tamper_rejection(tmp_path) -> None:
    (tmp_path / "data/research/m4").mkdir(parents=True)
    (tmp_path / "data/product").mkdir(parents=True)
    (tmp_path / "data/research/m4/evidence.json").write_text("one\n", encoding="utf-8")
    (tmp_path / "data/product/state.json").write_text("state\n", encoding="utf-8")

    backup = create_product_backup(
        root=tmp_path,
        now=datetime(2026, 9, 22, tzinfo=UTC),
    )
    assert verify_product_backup(backup["path"])["verified"] is True

    (tmp_path / "data/research/m4/evidence.json").write_text("changed\n", encoding="utf-8")
    restore_product_backup(
        root=tmp_path,
        archive_path=backup["path"],
        create_pre_restore=False,
    )
    assert (tmp_path / "data/research/m4/evidence.json").read_text(encoding="utf-8") == "one\n"


def test_restore_rejects_path_traversal_archive(tmp_path) -> None:
    import zipfile

    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("../evil.txt", b"x")
        handle.writestr("_HTCN_BACKUP_MANIFEST.json", b"{}")
    result = verify_product_backup(archive)
    assert result["verified"] is False
    assert "unsafe_archive_member" in result["errors"]
