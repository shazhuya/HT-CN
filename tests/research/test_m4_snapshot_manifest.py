from htcn.research.snapshot_manifest import (
    SnapshotManifestEntry,
    append_snapshot_manifest,
    read_snapshot_manifest,
    resolve_capture_timeline,
)


def _entry(date: str, *, head: str = "h", candidates: int = 2):
    return SnapshotManifestEntry(
        code_head=head,
        as_of_trade_date=date,
        captured_at_utc="2026-09-18T00:00:00+00:00",
        instrument_count=55,
        successful_instruments=55,
        failed_instruments=0,
        candidate_count=candidates,
        worktree_clean=True,
        status="pass",
    )


def test_manifest_records_zero_candidate_capture(tmp_path) -> None:
    path = tmp_path / "manifest.jsonl"
    append_snapshot_manifest(path, _entry("2026-09-18", candidates=0))
    rows = read_snapshot_manifest(path)
    assert len(rows) == 1
    assert rows[0]["candidate_count"] == 0


def test_manifest_same_head_same_facts_is_idempotent(tmp_path) -> None:
    path = tmp_path / "manifest.jsonl"
    first = append_snapshot_manifest(path, _entry("2026-09-18"))
    second = append_snapshot_manifest(path, _entry("2026-09-18"))
    assert first["appended"] == 1
    assert second["appended"] == 0


def test_manifest_forbids_mixed_code_heads_same_day(tmp_path) -> None:
    path = tmp_path / "manifest.jsonl"
    append_snapshot_manifest(path, _entry("2026-09-18", head="h1"))
    try:
        append_snapshot_manifest(path, _entry("2026-09-18", head="h2"))
    except ValueError as exc:
        assert "mixed code heads" in str(exc)
    else:
        raise AssertionError("same date mixed head must fail closed")


def test_manifest_forbids_same_day_fact_drift(tmp_path) -> None:
    path = tmp_path / "manifest.jsonl"
    append_snapshot_manifest(path, _entry("2026-09-18", candidates=2))
    try:
        append_snapshot_manifest(path, _entry("2026-09-18", candidates=3))
    except ValueError as exc:
        assert "changed capture facts" in str(exc)
    else:
        raise AssertionError("same date capture fact drift must fail closed")


def test_manifest_forbids_historical_backfill(tmp_path) -> None:
    path = tmp_path / "manifest.jsonl"
    append_snapshot_manifest(path, _entry("2026-09-18"))
    try:
        append_snapshot_manifest(path, _entry("2026-09-17"))
    except ValueError as exc:
        assert "forbids backfill" in str(exc)
    else:
        raise AssertionError("manifest backfill must fail closed")


def _manifest_row(date: str, *, head: str = "h", candidates: int = 1):
    return _entry(date, head=head, candidates=candidates).as_payload()


def test_capture_timeline_allows_legacy_t0_before_manifest_activation() -> None:
    journal = [
        {"as_of_trade_date": "2026-09-17", "code_head": "old"},
        {"as_of_trade_date": "2026-09-18", "code_head": "h"},
    ]
    manifest = [_manifest_row("2026-09-18", head="h")]
    timeline = resolve_capture_timeline(journal, manifest)
    assert timeline.dates == ("2026-09-17", "2026-09-18")
    assert timeline.source == "manifest_plus_legacy_journal"
    assert timeline.legacy_pre_manifest_dates == ("2026-09-17",)


def test_capture_timeline_keeps_zero_candidate_manifest_date() -> None:
    journal = [{"as_of_trade_date": "2026-09-17", "code_head": "old"}]
    manifest = [
        _manifest_row("2026-09-18", candidates=0),
        _manifest_row("2026-09-19", candidates=2),
    ]
    timeline = resolve_capture_timeline(journal, manifest)
    assert timeline.dates == ("2026-09-17", "2026-09-18", "2026-09-19")


def test_capture_timeline_rejects_journal_date_missing_manifest_after_activation() -> None:
    journal = [
        {"as_of_trade_date": "2026-09-17", "code_head": "old"},
        {"as_of_trade_date": "2026-09-19", "code_head": "h"},
    ]
    manifest = [_manifest_row("2026-09-18", candidates=0)]
    try:
        resolve_capture_timeline(journal, manifest)
    except ValueError as exc:
        assert "missing required snapshot manifest" in str(exc)
    else:
        raise AssertionError("post-activation journal date without manifest must fail")


def test_capture_timeline_rejects_manifest_journal_head_mismatch() -> None:
    journal = [{"as_of_trade_date": "2026-09-18", "code_head": "h1"}]
    manifest = [_manifest_row("2026-09-18", head="h2")]
    try:
        resolve_capture_timeline(journal, manifest)
    except ValueError as exc:
        assert "code-head mismatch" in str(exc)
    else:
        raise AssertionError("manifest/journal head mismatch must fail")
