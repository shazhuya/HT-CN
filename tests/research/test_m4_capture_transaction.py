from htcn.research.capture_transaction import (
    build_committed_capture,
    capture_transaction_id,
    commit_capture_transaction,
    committed_capture_view,
    read_committed_captures,
)


def _row(key: str, *, date: str = "2026-09-18", head: str = "h"):
    return {
        "code_head": head,
        "instrument_id": "SSE.600000",
        "as_of_trade_date": date,
        "candidate_key": key,
        "pattern_id": "abcd",
        "schema": "ABCD",
        "direction": "bullish",
        "scale": 5,
        "pattern_state": "forming",
        "source_lifecycle_state": "waiting_terminal",
        "action_state": "waiting",
        "next_key_price": 90.0,
        "next_key_price_role": "source_prz_terminal_side",
        "execution_context_gate": "tradable",
        "context_integrity_summary": "complete",
        "source_prz_low": 90.0,
        "source_prz_high": 92.0,
        "source_terminal_trade_date": None,
        "eligible_for_validation": True,
        "evidence_only": True,
        "is_trade_instruction": False,
        "alpha_inference_allowed": False,
    }


def _capture(rows, *, date="2026-09-18", head="h"):
    return build_committed_capture(
        code_head=head,
        as_of_trade_date=date,
        captured_at_utc="2026-09-18T09:00:00+00:00",
        instrument_count=55,
        successful_instruments=55,
        failed_instruments=0,
        worktree_clean=True,
        journal_rows=rows,
    )


def test_transaction_id_is_deterministic_across_capture_time() -> None:
    a = _capture([_row("a"), _row("b")])
    b = build_committed_capture(
        code_head="h",
        as_of_trade_date="2026-09-18",
        captured_at_utc="2026-09-18T10:00:00+00:00",
        instrument_count=55,
        successful_instruments=55,
        failed_instruments=0,
        worktree_clean=True,
        journal_rows=[_row("b"), _row("a")],
    )
    assert a.transaction_id == b.transaction_id


def test_single_file_commit_is_idempotent(tmp_path) -> None:
    capture = _capture([_row("a")])
    first = commit_capture_transaction(tmp_path, capture)
    second = commit_capture_transaction(tmp_path, capture)
    assert first["status"] == "committed"
    assert second["status"] == "already_committed"
    assert len(read_committed_captures(tmp_path)) == 1


def test_same_date_fact_drift_fails_closed(tmp_path) -> None:
    commit_capture_transaction(tmp_path, _capture([_row("a")]))
    try:
        commit_capture_transaction(tmp_path, _capture([_row("b")]))
    except ValueError as exc:
        assert "another committed transaction" in str(exc)
    else:
        raise AssertionError("same-date transaction drift must fail")


def test_zero_candidate_capture_commits(tmp_path) -> None:
    capture = _capture([])
    commit_capture_transaction(tmp_path, capture)
    rows = read_committed_captures(tmp_path)
    assert rows[0]["candidate_count"] == 0
    assert rows[0]["journal_rows"] == []


def test_uncommitted_tmp_file_is_ignored(tmp_path) -> None:
    (tmp_path / ".2026-09-18__broken.json.tmp").write_text("partial", encoding="utf-8")
    assert read_committed_captures(tmp_path) == []


def test_view_uses_legacy_only_before_transaction_activation() -> None:
    legacy = [
        _row("legacy", date="2026-09-17", head="old"),
        _row("stale-mirror", date="2026-09-18", head="stale"),
    ]
    capture = _capture([_row("new")]).as_payload()
    journal, manifest = committed_capture_view(
        legacy_journal_rows=legacy,
        capture_rows=[capture],
    )
    assert [row["candidate_key"] for row in journal] == ["legacy", "new"]
    assert manifest[0]["capture_transaction_id"] == capture["transaction_id"]


def test_transaction_rejects_partial_instrument_coverage() -> None:
    try:
        build_committed_capture(
            code_head="h",
            as_of_trade_date="2026-09-18",
            captured_at_utc="x",
            instrument_count=55,
            successful_instruments=54,
            failed_instruments=1,
            worktree_clean=True,
            journal_rows=[],
        )
    except ValueError as exc:
        assert "complete instrument coverage" in str(exc)
    else:
        raise AssertionError("partial instrument capture must fail")
