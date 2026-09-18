from htcn.research.capture_transaction import (
    build_committed_capture,
    commit_capture_transaction,
    freeze_legacy_baseline,
)
from htcn.research.mirror_recovery import (
    inspect_compatibility_mirrors,
    repair_compatibility_mirrors,
)


def _row(key: str, date: str, head: str):
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


def _activate_store(root):
    freeze_legacy_baseline(
        root,
        [_row("legacy", "2026-09-17", "old")],
        baseline_through_trade_date="2026-09-17",
    )
    capture = build_committed_capture(
        code_head="h",
        as_of_trade_date="2026-09-18",
        captured_at_utc="t",
        instrument_count=55,
        successful_instruments=55,
        failed_instruments=0,
        worktree_clean=True,
        journal_rows=[_row("new", "2026-09-18", "h")],
    )
    commit_capture_transaction(root, capture)


def test_missing_mirrors_are_repair_needed_not_evidence_failure(tmp_path) -> None:
    root = tmp_path / "captures"
    _activate_store(root)
    integrity = inspect_compatibility_mirrors(
        transaction_root=root,
        journal_path=tmp_path / "journal.jsonl",
        manifest_path=tmp_path / "manifest.jsonl",
    )
    assert integrity.authoritative_evidence_intact is True
    assert integrity.repair_needed is True
    assert integrity.journal_mirror_status == "missing"


def test_corrupt_mirror_can_be_rebuilt_from_authoritative_store(tmp_path) -> None:
    root = tmp_path / "captures"
    _activate_store(root)
    journal = tmp_path / "journal.jsonl"
    manifest = tmp_path / "manifest.jsonl"
    journal.write_text("{broken", encoding="utf-8")
    manifest.write_text("{broken", encoding="utf-8")
    before = inspect_compatibility_mirrors(
        transaction_root=root, journal_path=journal, manifest_path=manifest
    )
    assert before.repair_needed is True
    result = repair_compatibility_mirrors(
        transaction_root=root, journal_path=journal, manifest_path=manifest
    )
    assert result["status"] == "repaired"
    assert result["authoritative_evidence_modified"] is False
    after = inspect_compatibility_mirrors(
        transaction_root=root, journal_path=journal, manifest_path=manifest
    )
    assert after.repair_needed is False


def test_transaction_store_inactive_does_not_rewrite_legacy_files(tmp_path) -> None:
    journal = tmp_path / "journal.jsonl"
    journal.write_text("legacy\n", encoding="utf-8")
    result = repair_compatibility_mirrors(
        transaction_root=tmp_path / "captures",
        journal_path=journal,
        manifest_path=tmp_path / "manifest.jsonl",
    )
    assert result["status"] == "not_applicable"
    assert journal.read_text(encoding="utf-8") == "legacy\n"
