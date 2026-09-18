from htcn.research.snapshot_manifest import (
    SnapshotManifestEntry,
    append_snapshot_manifest,
    read_snapshot_manifest,
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
