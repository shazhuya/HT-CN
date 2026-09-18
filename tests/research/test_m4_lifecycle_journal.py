from __future__ import annotations

from htcn.research.lifecycle_journal import (
    LifecycleJournalEntry,
    append_entries,
    candidate_key,
    entries_from_analysis,
)


def _pattern(schema="XABCD", shift=0):
    labels = {
        "XABCD": ["X", "A", "B", "C", "D"],
        "ABCD": ["A", "B", "C", "D"],
        "0XABC": ["0", "X", "A", "B"],
    }[schema]
    dates = {
        "0": "2026-09-10",
        "X": "2026-09-11",
        "A": "2026-09-12",
        "B": "2026-09-15",
        "C": "2026-09-16",
        "D": "2026-09-17",
    }
    return {
        "pattern_id": "shark" if schema == "0XABC" else "gartley",
        "schema": schema,
        "direction": "bullish",
        "state": "forming",
        "scale": 5,
        "points": [
            {"label": label, "index": i + shift, "trade_date": dates[label], "price": 100 + i}
            for i, label in enumerate(labels)
        ],
        "prz": {
            "source_prz": {
                "available": True,
                "price_low": 95.0,
                "price_high": 97.0,
            }
        },
        "source_lifecycle": {
            "state": "waiting_terminal",
            "next_key_price": 95.0,
            "next_key_price_role": "source_prz_terminal_side",
            "source_terminal_bar": None,
        },
        "decision_narrative": {
            "action_state": "waiting",
            "execution_context_gate": "tradable",
        },
    }


def test_candidate_key_is_stable_across_rolling_window_index_shift() -> None:
    first = candidate_key("SSE.688256", _pattern("XABCD", shift=0))
    shifted = candidate_key("SSE.688256", _pattern("XABCD", shift=17))
    assert first == shifted


def test_shark_candidate_key_uses_0xab_anchors_without_inventing_c_or_d() -> None:
    key = candidate_key("SSE.688300", _pattern("0XABC"))
    assert "0:2026-09-10" in key
    assert "B:2026-09-15" in key
    assert "C:" not in key
    assert "D:" not in key


def test_entries_from_analysis_excludes_five_zero_and_preserves_source_state() -> None:
    shark = _pattern("0XABC")
    five_zero = {
        **_pattern("XABCD"),
        "pattern_id": "five_zero",
        "schema": "FIVE_ZERO",
    }
    analysis = {
        "instrument_id": "SSE.688300",
        "last_trade_date": "2026-09-18",
        "bars": [],
        "context_integrity": {"summary_state": "partial"},
        "completed": [],
        "forming": [shark, five_zero],
    }
    rows = entries_from_analysis(analysis, code_head="abc")
    assert len(rows) == 1
    assert rows[0].pattern_id == "shark"
    assert rows[0].source_lifecycle_state == "waiting_terminal"
    assert rows[0].alpha_inference_allowed is False


def _entry(date: str, key: str = "k", head: str = "h") -> LifecycleJournalEntry:
    return LifecycleJournalEntry(
        code_head=head,
        instrument_id="SSE.688256",
        as_of_trade_date=date,
        candidate_key=key,
        pattern_id="gartley",
        schema="XABCD",
        direction="bullish",
        scale=5,
        pattern_state="forming",
        source_lifecycle_state="waiting_terminal",
        action_state="waiting",
        next_key_price=100.0,
        next_key_price_role="source_prz_terminal_side",
        execution_context_gate="tradable",
        context_integrity_summary="complete",
        source_prz_low=99.0,
        source_prz_high=101.0,
        source_terminal_trade_date=None,
        eligible_for_validation=True,
    )


def test_append_is_idempotent_for_same_head_date_and_candidate(tmp_path) -> None:
    path = tmp_path / "journal.jsonl"
    first = append_entries(path, [_entry("2026-09-18")])
    second = append_entries(path, [_entry("2026-09-18")])
    assert first["appended"] == 1
    assert second["appended"] == 0


def test_append_forbids_historical_backfill(tmp_path) -> None:
    path = tmp_path / "journal.jsonl"
    append_entries(path, [_entry("2026-09-18")])
    try:
        append_entries(path, [_entry("2026-09-17", key="other")])
    except ValueError as exc:
        assert "forbids backfill" in str(exc)
    else:
        raise AssertionError("backfill must fail closed")
