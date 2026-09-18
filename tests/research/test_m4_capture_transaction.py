from htcn.research.capture_transaction import (
    build_committed_capture,
    capture_transaction_id,
    commit_capture_transaction,
    committed_capture_view,
    freeze_legacy_baseline,
    read_committed_captures,
    read_frozen_legacy_baseline,
)


TEST_METHODOLOGY_CONTRACT_VERSION = 1
TEST_METHODOLOGY_FINGERPRINT = "a" * 64


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
        methodology_contract_version=TEST_METHODOLOGY_CONTRACT_VERSION,
        methodology_fingerprint=TEST_METHODOLOGY_FINGERPRINT,
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
        methodology_contract_version=TEST_METHODOLOGY_CONTRACT_VERSION,
        methodology_fingerprint=TEST_METHODOLOGY_FINGERPRINT,
        journal_rows=[_row("b"), _row("a")],
    )
    assert a.transaction_id == b.transaction_id


def test_transaction_id_changes_when_methodology_changes() -> None:
    first = _capture([_row("a")])
    second = build_committed_capture(
        code_head="h",
        as_of_trade_date="2026-09-18",
        captured_at_utc="2026-09-18T09:00:00+00:00",
        instrument_count=55,
        successful_instruments=55,
        failed_instruments=0,
        worktree_clean=True,
        methodology_contract_version=TEST_METHODOLOGY_CONTRACT_VERSION,
        methodology_fingerprint="b" * 64,
        journal_rows=[_row("a")],
    )
    assert first.transaction_id != second.transaction_id


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
            methodology_contract_version=TEST_METHODOLOGY_CONTRACT_VERSION,
            methodology_fingerprint=TEST_METHODOLOGY_FINGERPRINT,
            journal_rows=[],
        )
    except ValueError as exc:
        assert "complete instrument coverage" in str(exc)
    else:
        raise AssertionError("partial instrument capture must fail")


def test_same_facts_different_capture_time_is_idempotent(tmp_path) -> None:
    first = _capture([_row("a")])
    second = build_committed_capture(
        code_head="h",
        as_of_trade_date="2026-09-18",
        captured_at_utc="2026-09-18T11:00:00+00:00",
        instrument_count=55,
        successful_instruments=55,
        failed_instruments=0,
        worktree_clean=True,
        methodology_contract_version=TEST_METHODOLOGY_CONTRACT_VERSION,
        methodology_fingerprint=TEST_METHODOLOGY_FINGERPRINT,
        journal_rows=[_row("a")],
    )
    assert first.transaction_id == second.transaction_id
    commit_capture_transaction(tmp_path, first)
    result = commit_capture_transaction(tmp_path, second)
    assert result["status"] == "already_committed"


def test_legacy_baseline_is_atomic_and_immutable(tmp_path) -> None:
    rows = [_row("legacy", date="2026-09-17", head="old")]
    first = freeze_legacy_baseline(tmp_path, rows)
    second = freeze_legacy_baseline(tmp_path, rows)
    assert first["status"] == "frozen"
    assert second["status"] == "already_frozen"
    assert read_frozen_legacy_baseline(tmp_path) == rows


def test_legacy_baseline_drift_fails_closed(tmp_path) -> None:
    freeze_legacy_baseline(
        tmp_path,
        [_row("legacy", date="2026-09-17", head="old")],
    )
    try:
        freeze_legacy_baseline(
            tmp_path,
            [_row("changed", date="2026-09-17", head="old")],
        )
    except ValueError as exc:
        assert "already frozen with different evidence" in str(exc)
    else:
        raise AssertionError("frozen legacy baseline must be immutable")


def test_reader_rejects_renamed_transaction_file(tmp_path) -> None:
    capture = _capture([_row("a")])
    result = commit_capture_transaction(tmp_path, capture)
    from pathlib import Path
    original = Path(result["path"])
    renamed = original.with_name("2026-09-18__wrong.json")
    original.rename(renamed)
    try:
        read_committed_captures(tmp_path)
    except ValueError as exc:
        assert "filename mismatch" in str(exc)
    else:
        raise AssertionError("renamed committed transaction must fail")


def test_reader_rejects_row_transaction_id_tamper(tmp_path) -> None:
    import json
    capture = _capture([_row("a")])
    result = commit_capture_transaction(tmp_path, capture)
    from pathlib import Path
    path = Path(result["path"])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["journal_rows"][0]["capture_transaction_id"] = "tampered"
    path.write_text(json.dumps(payload), encoding="utf-8")
    try:
        read_committed_captures(tmp_path)
    except ValueError as exc:
        assert "row transaction-id mismatch" in str(exc)
    else:
        raise AssertionError("row transaction id tamper must fail")


def test_reader_allows_frozen_baseline_and_committed_capture_to_coexist(tmp_path) -> None:
    freeze_legacy_baseline(
        tmp_path,
        [_row("legacy", date="2026-09-17", head="old")],
    )
    capture = _capture([_row("new")])
    commit_capture_transaction(tmp_path, capture)
    committed = read_committed_captures(tmp_path)
    assert len(committed) == 1
    assert committed[0]["transaction_id"] == capture.transaction_id
    assert len(read_frozen_legacy_baseline(tmp_path)) == 1


def test_zero_row_legacy_baseline_can_freeze_explicit_cutoff(tmp_path) -> None:
    result = freeze_legacy_baseline(
        tmp_path,
        [],
        baseline_through_trade_date="2026-09-17",
    )
    assert result["status"] == "frozen"
    from htcn.research.capture_transaction import frozen_legacy_baseline_through_date
    assert frozen_legacy_baseline_through_date(tmp_path) == "2026-09-17"


def test_transaction_must_be_after_frozen_legacy_cutoff(tmp_path) -> None:
    freeze_legacy_baseline(
        tmp_path,
        [],
        baseline_through_trade_date="2026-09-17",
    )
    same_day = _capture(
        [_row("a", date="2026-09-17")],
        date="2026-09-17",
    )
    try:
        commit_capture_transaction(tmp_path, same_day)
    except ValueError as exc:
        assert "after frozen legacy baseline" in str(exc)
    else:
        raise AssertionError("same-day capture must not replace frozen baseline")


def test_committed_transactions_forbid_backfill_after_newer_date(tmp_path) -> None:
    freeze_legacy_baseline(
        tmp_path,
        [],
        baseline_through_trade_date="2026-09-17",
    )
    newer = _capture(
        [_row("newer", date="2026-09-19")],
        date="2026-09-19",
    )
    older = _capture(
        [_row("older", date="2026-09-18")],
        date="2026-09-18",
    )
    commit_capture_transaction(tmp_path, newer)
    try:
        commit_capture_transaction(tmp_path, older)
    except ValueError as exc:
        assert "forbids backfill" in str(exc)
    else:
        raise AssertionError("transaction backfill must fail closed")


def test_tampered_baseline_cutoff_blocks_future_commit(tmp_path) -> None:
    import json
    freeze_legacy_baseline(
        tmp_path,
        [_row("legacy", date="2026-09-17", head="old")],
        baseline_through_trade_date="2026-09-17",
    )
    path = tmp_path / "legacy_baseline.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["baseline_through_trade_date"] = "2026-09-16"
    path.write_text(json.dumps(payload), encoding="utf-8")
    capture = _capture(
        [_row("new", date="2026-09-18")],
        date="2026-09-18",
    )
    try:
        commit_capture_transaction(tmp_path, capture)
    except ValueError as exc:
        assert "legacy baseline identity mismatch" in str(exc)
    else:
        raise AssertionError("tampered baseline must fail before future commit")


def test_empty_frozen_baseline_marker_is_valid_for_transaction_native_start(tmp_path) -> None:
    from htcn.research.capture_transaction import frozen_legacy_baseline_present

    freeze_legacy_baseline(tmp_path, [])
    assert frozen_legacy_baseline_present(tmp_path) is True
    capture = _capture([_row("t0")])
    result = commit_capture_transaction(tmp_path, capture)
    assert result["status"] == "committed"


def test_existing_transaction_nonidentity_tamper_rejected_on_rerun(tmp_path) -> None:
    import json
    from pathlib import Path

    capture = _capture([_row("a")])
    result = commit_capture_transaction(tmp_path, capture)
    path = Path(result["path"])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["worktree_clean"] = False
    path.write_text(json.dumps(payload), encoding="utf-8")
    try:
        commit_capture_transaction(tmp_path, capture)
    except ValueError as exc:
        assert "clean worktree" in str(exc)
    else:
        raise AssertionError("tampered nonidentity metadata must fail closed")


def test_legacy_baseline_rejects_alpha_boundary_pollution(tmp_path) -> None:
    row = _row("legacy", date="2026-09-17", head="old")
    row["alpha_inference_allowed"] = True
    try:
        freeze_legacy_baseline(
            tmp_path,
            [row],
            baseline_through_trade_date="2026-09-17",
        )
    except ValueError as exc:
        assert "permits alpha inference" in str(exc)
    else:
        raise AssertionError("polluted legacy baseline must not be frozen")


def test_legacy_baseline_rejects_cutoff_before_last_row(tmp_path) -> None:
    row = _row("legacy", date="2026-09-18", head="old")
    try:
        freeze_legacy_baseline(
            tmp_path,
            [row],
            baseline_through_trade_date="2026-09-17",
        )
    except ValueError as exc:
        assert "after baseline_through_trade_date" in str(exc)
    else:
        raise AssertionError("baseline cutoff before row date must fail")


def test_transaction_rejects_suspended_row_with_fake_ohlc() -> None:
    row = _row("suspended")
    row.update({
        "underlying_last_trade_date": "2026-09-17",
        "market_observation_status": "confirmed_full_day_suspended",
        "execution_context_gate": "blocked_suspended",
        "daily_event_source": "feed",
        "as_of_close": 10.0,
    })
    try:
        _capture([row])
    except ValueError as exc:
        assert "must not contain synthetic" in str(exc)
    else:
        raise AssertionError("suspended fake OHLC must fail")


def test_transaction_accepts_valid_suspended_continuity_row() -> None:
    row = _row("suspended")
    row.update({
        "underlying_last_trade_date": "2026-09-17",
        "market_observation_status": "confirmed_full_day_suspended",
        "execution_context_gate": "blocked_suspended",
        "daily_event_source": "feed",
        "daily_event_reason": "full",
        "as_of_open": None,
        "as_of_high": None,
        "as_of_low": None,
        "as_of_close": None,
        "as_of_volume": None,
    })
    capture = _capture([row])
    assert capture.journal_rows[0]["market_observation_status"] == (
        "confirmed_full_day_suspended"
    )


def test_transaction_rejects_suspended_row_without_positive_event_source() -> None:
    row = _row("suspended")
    row.update({
        "underlying_last_trade_date": "2026-09-17",
        "market_observation_status": "confirmed_full_day_suspended",
        "execution_context_gate": "blocked_suspended",
        "daily_event_source": None,
    })
    try:
        _capture([row])
    except ValueError as exc:
        assert "positive daily_event_source" in str(exc)
    else:
        raise AssertionError("suspended row without event evidence must fail")


def test_committed_chain_rejects_methodology_drift(tmp_path) -> None:
    freeze_legacy_baseline(
        tmp_path,
        [],
        baseline_through_trade_date="2026-09-17",
    )
    first = _capture(
        [_row("first", date="2026-09-18")],
        date="2026-09-18",
    )
    commit_capture_transaction(tmp_path, first)
    changed = build_committed_capture(
        code_head="h2",
        as_of_trade_date="2026-09-19",
        captured_at_utc="2026-09-19T09:00:00+00:00",
        instrument_count=55,
        successful_instruments=55,
        failed_instruments=0,
        worktree_clean=True,
        methodology_contract_version=TEST_METHODOLOGY_CONTRACT_VERSION,
        methodology_fingerprint="b" * 64,
        journal_rows=[_row("changed", date="2026-09-19", head="h2")],
    )
    try:
        commit_capture_transaction(tmp_path, changed)
    except ValueError as exc:
        assert "methodology fingerprint drift" in str(exc)
    else:
        raise AssertionError("methodology drift must not mix into one prospective chain")


def test_reader_preserves_pre_fingerprint_schema_v1_for_explicit_migration(tmp_path) -> None:
    import json

    row = _row("legacy-v1")
    txid = capture_transaction_id(
        code_head="h",
        as_of_trade_date="2026-09-18",
        instrument_count=55,
        successful_instruments=55,
        failed_instruments=0,
        journal_rows=[row],
        schema_version=1,
    )
    stamped = {**row, "capture_transaction_id": txid}
    payload = {
        "transaction_id": txid,
        "code_head": "h",
        "as_of_trade_date": "2026-09-18",
        "captured_at_utc": "2026-09-18T09:00:00+00:00",
        "instrument_count": 55,
        "successful_instruments": 55,
        "failed_instruments": 0,
        "candidate_count": 1,
        "worktree_clean": True,
        "journal_rows": [stamped],
        "status": "committed",
        "schema_version": 1,
        "alpha_inference_allowed": False,
        "is_trade_instruction": False,
    }
    path = tmp_path / f"2026-09-18__{txid}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    committed = read_committed_captures(tmp_path)
    assert committed[0]["schema_version"] == 1
    assert committed[0].get("methodology_fingerprint") is None


def test_v1_chain_blocks_v2_append_without_explicit_migration(tmp_path) -> None:
    import json

    freeze_legacy_baseline(
        tmp_path,
        [],
        baseline_through_trade_date="2026-09-17",
    )
    row = _row("legacy-v1")
    txid = capture_transaction_id(
        code_head="h",
        as_of_trade_date="2026-09-18",
        instrument_count=55,
        successful_instruments=55,
        failed_instruments=0,
        journal_rows=[row],
        schema_version=1,
    )
    payload = {
        "transaction_id": txid,
        "code_head": "h",
        "as_of_trade_date": "2026-09-18",
        "captured_at_utc": "2026-09-18T09:00:00+00:00",
        "instrument_count": 55,
        "successful_instruments": 55,
        "failed_instruments": 0,
        "candidate_count": 1,
        "worktree_clean": True,
        "journal_rows": [{**row, "capture_transaction_id": txid}],
        "status": "committed",
        "schema_version": 1,
        "alpha_inference_allowed": False,
        "is_trade_instruction": False,
    }
    (tmp_path / f"2026-09-18__{txid}.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    v2 = _capture(
        [_row("new-v2", date="2026-09-19", head="h2")],
        date="2026-09-19",
        head="h2",
    )
    try:
        commit_capture_transaction(tmp_path, v2)
    except ValueError as exc:
        assert "predates methodology fingerprint" in str(exc)
    else:
        raise AssertionError(
            "pre-fingerprint v1 chain must require explicit migration before v2 append"
        )



def _followup(
    key: str,
    *,
    date: str = "2026-09-19",
    head: str = "h2",
    enrollment: str = "2026-09-18",
):
    return {
        "code_head": head,
        "instrument_id": "SSE.600000",
        "as_of_trade_date": date,
        "candidate_key": key,
        "outcome_enrollment_trade_date": enrollment,
        "scanner_presence": "absent",
        "underlying_last_trade_date": date,
        "market_observation_status": "traded",
        "execution_context_gate": "followup_observation_only",
        "daily_event_source": None,
        "daily_event_reason": None,
        "as_of_open": 100.0,
        "as_of_high": 103.0,
        "as_of_low": 99.0,
        "as_of_close": 102.0,
        "as_of_volume": 1234.0,
        "evidence_only": True,
        "is_trade_instruction": False,
        "alpha_inference_allowed": False,
    }


def test_schema_v3_requires_followup_for_prior_enrolled_scanner_absence(tmp_path) -> None:
    freeze_legacy_baseline(
        tmp_path,
        [],
        baseline_through_trade_date="2026-09-17",
    )
    first = _capture(
        [_row("enrolled", date="2026-09-18", head="h")],
        date="2026-09-18",
        head="h",
    )
    commit_capture_transaction(tmp_path, first)

    missing = build_committed_capture(
        code_head="h2",
        as_of_trade_date="2026-09-19",
        captured_at_utc="2026-09-19T09:00:00+00:00",
        instrument_count=55,
        successful_instruments=55,
        failed_instruments=0,
        worktree_clean=True,
        methodology_contract_version=TEST_METHODOLOGY_CONTRACT_VERSION,
        methodology_fingerprint=TEST_METHODOLOGY_FINGERPRINT,
        journal_rows=[],
        cohort_followup_rows=[],
    )
    try:
        commit_capture_transaction(tmp_path, missing)
    except ValueError as exc:
        assert "cohort follow-up coverage mismatch" in str(exc)
        assert "enrolled" in str(exc)
    else:
        raise AssertionError(
            "schema v3 must fail closed when prior enrolled absent candidate lacks follow-up"
        )


def test_schema_v3_accepts_complete_followup_for_prior_enrolled_absence(tmp_path) -> None:
    freeze_legacy_baseline(
        tmp_path,
        [],
        baseline_through_trade_date="2026-09-17",
    )
    first = _capture(
        [_row("enrolled", date="2026-09-18", head="h")],
        date="2026-09-18",
        head="h",
    )
    commit_capture_transaction(tmp_path, first)

    second = build_committed_capture(
        code_head="h2",
        as_of_trade_date="2026-09-19",
        captured_at_utc="2026-09-19T09:00:00+00:00",
        instrument_count=55,
        successful_instruments=55,
        failed_instruments=0,
        worktree_clean=True,
        methodology_contract_version=TEST_METHODOLOGY_CONTRACT_VERSION,
        methodology_fingerprint=TEST_METHODOLOGY_FINGERPRINT,
        journal_rows=[],
        cohort_followup_rows=[
            _followup("enrolled", date="2026-09-19", head="h2")
        ],
    )
    result = commit_capture_transaction(tmp_path, second)
    assert result["status"] == "committed"
    captures = read_committed_captures(tmp_path)
    assert captures[-1]["cohort_followup_count"] == 1
    assert captures[-1]["cohort_followup_rows"][0]["scanner_presence"] == "absent"
