from __future__ import annotations

from pathlib import Path

import duckdb

from htcn.research.capture_transaction import (
    build_committed_capture,
    commit_capture_transaction,
)
from scripts.m7_append_precheck import assess_append_need


def _catalog(path: Path, dates: list[str]) -> None:
    with duckdb.connect(str(path)) as con:
        con.execute("CREATE TABLE trade_calendar(trade_date DATE)")
        con.executemany(
            "INSERT INTO trade_calendar VALUES (?)",
            [(value,) for value in dates],
        )


def _commit(root: Path, trade_date: str) -> None:
    capture = build_committed_capture(
        code_head="head",
        as_of_trade_date=trade_date,
        captured_at_utc=f"{trade_date}T08:00:00+00:00",
        instrument_count=1,
        successful_instruments=1,
        failed_instruments=0,
        worktree_clean=True,
        methodology_contract_version=4,
        methodology_fingerprint="a" * 64,
        journal_rows=[],
    )
    commit_capture_transaction(root, capture)


def test_precheck_marks_same_closed_day_as_idempotent_noop(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.duckdb"
    _catalog(catalog, ["2026-09-18", "2026-09-21"])
    root = tmp_path / "captures"
    _commit(root, "2026-09-21")

    result = assess_append_need(catalog=catalog, transaction_root=root)

    assert result["status"] == "ready"
    assert result["action"] == "idempotent_noop"
    assert result["append_required"] is False
    assert result["pending_closed_trade_count"] == 0


def test_precheck_allows_exactly_one_new_closed_session(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.duckdb"
    _catalog(catalog, ["2026-09-21", "2026-09-22"])
    root = tmp_path / "captures"
    _commit(root, "2026-09-21")

    result = assess_append_need(catalog=catalog, transaction_root=root)

    assert result["status"] == "ready"
    assert result["action"] == "capture_due"
    assert result["pending_closed_trade_dates"] == ["2026-09-22"]


def test_precheck_fails_closed_when_multiple_sessions_were_missed(
    tmp_path: Path,
) -> None:
    catalog = tmp_path / "catalog.duckdb"
    _catalog(catalog, ["2026-09-21", "2026-09-22", "2026-09-23"])
    root = tmp_path / "captures"
    _commit(root, "2026-09-21")

    result = assess_append_need(catalog=catalog, transaction_root=root)

    assert result["status"] == "blocked"
    assert result["action"] == "blocked"
    assert result["reason"] == "missed_closed_sessions_no_backfill_allowed"
    assert result["pending_closed_trade_count"] == 2


def test_precheck_fails_closed_when_capture_is_not_in_local_calendar(
    tmp_path: Path,
) -> None:
    catalog = tmp_path / "catalog.duckdb"
    _catalog(catalog, ["2026-09-18", "2026-09-21"])
    root = tmp_path / "captures"
    _commit(root, "2026-09-22")

    result = assess_append_need(catalog=catalog, transaction_root=root)

    assert result["status"] == "blocked"
    assert result["action"] == "blocked"
    assert result["reason"] == "latest_committed_capture_not_in_local_trade_calendar"
