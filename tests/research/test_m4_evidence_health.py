from htcn.research.capture_transaction import (
    build_committed_capture,
    commit_capture_transaction,
    freeze_legacy_baseline,
)
from htcn.research.evidence_health import build_evidence_chain_health
from htcn.research.mirror_recovery import repair_compatibility_mirrors


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


def _store(tmp_path):
    root = tmp_path / "captures"
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
    return root


def test_health_ready_even_when_compatibility_mirrors_need_repair(tmp_path) -> None:
    root = _store(tmp_path)
    health = build_evidence_chain_health(
        transaction_root=root,
        journal_path=tmp_path / "journal.jsonl",
        manifest_path=tmp_path / "manifest.jsonl",
    )
    assert health["status"] == "ready_with_warnings"
    assert health["blocker_count"] == 0
    assert health["transition_evidence_chain_ready"] is True
    assert health["warnings"][0]["code"] == "compatibility_mirror_repair_needed"


def test_health_ready_after_mirror_repair(tmp_path) -> None:
    root = _store(tmp_path)
    journal = tmp_path / "journal.jsonl"
    manifest = tmp_path / "manifest.jsonl"
    repair_compatibility_mirrors(
        transaction_root=root, journal_path=journal, manifest_path=manifest
    )
    health = build_evidence_chain_health(
        transaction_root=root, journal_path=journal, manifest_path=manifest
    )
    assert health["status"] == "ready"
    assert health["warning_count"] == 0
    assert health["authoritative_evidence_source"] == (
        "frozen_baseline_plus_committed_transactions"
    )


def test_legacy_only_health_does_not_claim_transaction_readiness(tmp_path) -> None:
    health = build_evidence_chain_health(
        transaction_root=tmp_path / "captures",
        journal_path=tmp_path / "journal.jsonl",
        manifest_path=tmp_path / "manifest.jsonl",
    )
    assert health["status"] == "legacy_only"
    assert health["transition_evidence_chain_ready"] is False
    assert health["interpretation"]["uses_score"] is False


def test_empty_frozen_baseline_marker_does_not_block_health(tmp_path) -> None:
    root = tmp_path / "captures"
    freeze_legacy_baseline(root, [])
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
    health = build_evidence_chain_health(
        transaction_root=root,
        journal_path=tmp_path / "journal.jsonl",
        manifest_path=tmp_path / "manifest.jsonl",
    )
    assert health["blocker_count"] == 0
    assert health["frozen_legacy_baseline_present"] is True
    assert health["transition_evidence_chain_ready"] is True
