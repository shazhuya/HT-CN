from __future__ import annotations

FORMAL_BASIS = "qfq:" + "1" * 64
SOURCE_SIGNAL_DATE = "2026-09-16"
SOURCE_CLOCK_BASIS = "last_frontier_pivot_confirmed_at=index+scale"

from htcn.research.lifecycle_journal import (
    LifecycleJournalEntry,
    append_entries,
    candidate_key,
    entries_from_analysis,
    prospective_outcome_gate,
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
        "execution_clock": {
            "signal_bar": 0,
            "signal_clock_basis": SOURCE_CLOCK_BASIS,
            "reaction_anchor_label": "B" if schema == "0XABC" else "A",
            "reaction_anchor_price": 101.0,
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
        "price_mode": "qfq",
        "price_basis_id": FORMAL_BASIS,
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
        price_mode="qfq",
        price_basis_id=FORMAL_BASIS,
        source_prz_low=99.0,
        source_prz_high=101.0,
        source_terminal_trade_date=None,
        eligible_for_validation=True,
        source_signal_trade_date=SOURCE_SIGNAL_DATE,
        source_signal_clock_basis=SOURCE_CLOCK_BASIS,
        source_reaction_anchor_label="A",
        source_reaction_anchor_price=101.0,
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


def test_first_capture_is_baseline_existing(tmp_path) -> None:
    path = tmp_path / "journal.jsonl"
    result = append_entries(path, [_entry("2026-09-18", key="baseline")])
    rows = path.read_text(encoding="utf-8").splitlines()
    import json
    payload = json.loads(rows[0])
    assert result["baseline_existing_appended"] == 1
    assert result["prospective_new_appended"] == 0
    assert payload["enrollment_state"] == "baseline_existing"
    assert payload["first_observed_trade_date"] == "2026-09-18"
    assert payload["prospective_outcome_eligible"] is False


def test_candidate_first_seen_after_baseline_is_prospective_new(tmp_path) -> None:
    path = tmp_path / "journal.jsonl"
    append_entries(path, [_entry("2026-09-18", key="baseline")])
    result = append_entries(path, [_entry("2026-09-19", key="new")])
    import json
    payloads = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
    ]
    latest = payloads[-1]
    assert result["baseline_existing_appended"] == 0
    assert result["prospective_new_appended"] == 1
    assert latest["enrollment_state"] == "prospective_new"
    assert latest["first_observed_trade_date"] == "2026-09-19"
    assert latest["prospective_outcome_eligible"] is True


def test_existing_baseline_candidate_stays_baseline_on_later_capture(tmp_path) -> None:
    path = tmp_path / "journal.jsonl"
    append_entries(path, [_entry("2026-09-18", key="same")])
    append_entries(path, [_entry("2026-09-19", key="same", head="h2")])
    import json
    payloads = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
    ]
    latest = payloads[-1]
    assert latest["enrollment_state"] == "baseline_existing"
    assert latest["first_observed_trade_date"] == "2026-09-18"


def test_legacy_t0_row_without_enrollment_fields_is_treated_as_baseline(tmp_path) -> None:
    import json
    path = tmp_path / "journal.jsonl"
    legacy = _entry("2026-09-18", key="legacy").as_payload()
    legacy.pop("enrollment_state", None)
    legacy.pop("first_observed_trade_date", None)
    path.write_text(json.dumps(legacy, ensure_ascii=False) + "\n", encoding="utf-8")

    append_entries(path, [_entry("2026-09-19", key="legacy", head="h2")])
    payloads = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
    ]
    latest = payloads[-1]
    assert latest["enrollment_state"] == "baseline_existing"
    assert latest["first_observed_trade_date"] == "2026-09-18"


def test_prospective_outcome_gate_blocks_alternate_bat() -> None:
    eligible, reason = prospective_outcome_gate(
        {
            "pattern_id": "alternate_bat",
            "eligible_for_validation": True,
            "price_mode": "qfq",
            "price_basis_id": FORMAL_BASIS,
            "source_signal_trade_date": SOURCE_SIGNAL_DATE,
            "source_signal_clock_basis": SOURCE_CLOCK_BASIS,
            "source_reaction_anchor_label": "A",
            "source_reaction_anchor_price": 101.0,
            "pattern_state": "forming",
            "source_lifecycle_state": "waiting_terminal",
            "source_prz_low": 90.0,
            "source_prz_high": 92.0,
            "source_terminal_trade_date": None,
        },
        enrollment_state="prospective_new",
    )
    assert eligible is False
    assert reason == "pattern_source_fidelity_blocked"


def test_prospective_outcome_gate_requires_pre_terminal_forming_state() -> None:
    eligible, reason = prospective_outcome_gate(
        {
            "pattern_id": "abcd",
            "eligible_for_validation": True,
            "price_mode": "qfq",
            "price_basis_id": FORMAL_BASIS,
            "source_signal_trade_date": SOURCE_SIGNAL_DATE,
            "source_signal_clock_basis": SOURCE_CLOCK_BASIS,
            "source_reaction_anchor_label": "A",
            "source_reaction_anchor_price": 101.0,
            "pattern_state": "completed",
            "source_lifecycle_state": "type_i_confirmed",
            "source_prz_low": 90.0,
            "source_prz_high": 92.0,
            "source_terminal_trade_date": "2026-09-18",
        },
        enrollment_state="prospective_new",
    )
    assert eligible is False
    assert reason == "first_observed_not_forming"


def test_prospective_outcome_gate_allows_resolved_pre_terminal_candidate() -> None:
    eligible, reason = prospective_outcome_gate(
        {
            "pattern_id": "abcd",
            "eligible_for_validation": True,
            "price_mode": "qfq",
            "price_basis_id": FORMAL_BASIS,
            "source_signal_trade_date": SOURCE_SIGNAL_DATE,
            "source_signal_clock_basis": SOURCE_CLOCK_BASIS,
            "source_reaction_anchor_label": "A",
            "source_reaction_anchor_price": 101.0,
            "pattern_state": "forming",
            "source_lifecycle_state": "waiting_terminal",
            "source_prz_low": 90.0,
            "source_prz_high": 92.0,
            "source_terminal_trade_date": None,
        },
        enrollment_state="prospective_new",
    )
    assert eligible is True
    assert reason == "prospective_new_pre_terminal_source_resolved"


def test_entries_from_analysis_captures_latest_raw_market_facts() -> None:
    pattern = _pattern("ABCD")
    analysis = {
        "instrument_id": "SSE.600000",
        "last_trade_date": "2026-09-18",
        "price_mode": "qfq",
        "price_basis_id": FORMAL_BASIS,
        "bars": [
            {
                "index": 0,
                "trade_date": "2026-09-17",
                "open": 9.8,
                "high": 10.1,
                "low": 9.7,
                "close": 10.0,
                "volume": 1000,
            },
            {
                "index": 1,
                "trade_date": "2026-09-18",
                "open": 10.0,
                "high": 10.5,
                "low": 9.9,
                "close": 10.4,
                "volume": 1200,
            },
        ],
        "context_integrity": {"summary_state": "complete"},
        "completed": [],
        "forming": [pattern],
    }
    rows = entries_from_analysis(analysis, code_head="abc")
    assert len(rows) == 1
    row = rows[0]
    assert row.as_of_open == 10.0
    assert row.as_of_high == 10.5
    assert row.as_of_low == 9.9
    assert row.as_of_close == 10.4
    assert row.as_of_volume == 1200.0


def test_manifest_baseline_date_prevents_first_later_candidate_becoming_baseline(tmp_path) -> None:
    path = tmp_path / "journal.jsonl"
    result = append_entries(
        path,
        [_entry("2026-09-19", key="first-visible")],
        baseline_trade_date="2026-09-18",
    )
    import json
    payload = json.loads(path.read_text(encoding="utf-8").strip())
    assert result["prospective_new_appended"] == 1
    assert payload["enrollment_state"] == "prospective_new"
    assert payload["first_observed_trade_date"] == "2026-09-19"


def test_confirmed_suspension_carry_forward_has_no_fake_market_bar() -> None:
    pattern = _pattern("ABCD")
    analysis = {
        "instrument_id": "SSE.600000",
        "last_trade_date": "2026-09-17",
        "price_mode": "qfq",
        "price_basis_id": FORMAL_BASIS,
        "bars": [
            {
                "index": 0,
                "trade_date": "2026-09-17",
                "open": 10.0,
                "high": 10.5,
                "low": 9.9,
                "close": 10.4,
                "volume": 1200,
            }
        ],
        "context_integrity": {"summary_state": "complete"},
        "completed": [],
        "forming": [pattern],
    }
    rows = entries_from_analysis(
        analysis,
        code_head="abc",
        capture_trade_date="2026-09-18",
        market_observation_status="confirmed_full_day_suspended",
        execution_context_gate_override="blocked_suspended",
        include_latest_bar_facts=False,
        daily_event_source="akshare_stock_tfp_em",
        daily_event_reason="重大事项",
    )
    row = rows[0]
    assert row.as_of_trade_date == "2026-09-18"
    assert row.underlying_last_trade_date == "2026-09-17"
    assert row.market_observation_status == "confirmed_full_day_suspended"
    assert row.execution_context_gate == "blocked_suspended"
    assert row.daily_event_source == "akshare_stock_tfp_em"
    assert row.as_of_open is None
    assert row.as_of_high is None
    assert row.as_of_low is None
    assert row.as_of_close is None
    assert row.as_of_volume is None


def test_suspension_carry_forward_requires_later_capture_date() -> None:
    analysis = {
        "instrument_id": "SSE.600000",
        "last_trade_date": "2026-09-18",
        "price_mode": "qfq",
        "price_basis_id": FORMAL_BASIS,
        "bars": [],
        "context_integrity": {"summary_state": "complete"},
        "completed": [],
        "forming": [_pattern("ABCD")],
    }
    try:
        entries_from_analysis(
            analysis,
            code_head="abc",
            capture_trade_date="2026-09-18",
            market_observation_status="confirmed_full_day_suspended",
            execution_context_gate_override="blocked_suspended",
            include_latest_bar_facts=False,
        )
    except ValueError as exc:
        assert "requires capture date after underlying last trade date" in str(exc)
    else:
        raise AssertionError("same-day suspension carry-forward must fail closed")


def test_first_seen_suspension_row_cannot_enter_outcome_cohort() -> None:
    eligible, reason = prospective_outcome_gate(
        {
            "pattern_id": "abcd",
            "eligible_for_validation": True,
            "price_mode": "qfq",
            "price_basis_id": FORMAL_BASIS,
            "source_signal_trade_date": SOURCE_SIGNAL_DATE,
            "source_signal_clock_basis": SOURCE_CLOCK_BASIS,
            "source_reaction_anchor_label": "A",
            "source_reaction_anchor_price": 101.0,
            "pattern_state": "forming",
            "source_lifecycle_state": "waiting_terminal",
            "source_prz_low": 90.0,
            "source_prz_high": 92.0,
            "source_terminal_trade_date": None,
            "market_observation_status": "confirmed_full_day_suspended",
        },
        enrollment_state="prospective_new",
    )
    assert eligible is False
    assert reason == "first_observed_not_traded_session"



def test_prospective_outcome_gate_blocks_raw_fallback_basis() -> None:
    eligible, reason = prospective_outcome_gate(
        {
            "pattern_id": "abcd",
            "eligible_for_validation": False,
            "price_mode": "raw",
            "price_basis_id": "raw",
            "pattern_state": "forming",
            "source_lifecycle_state": "waiting_terminal",
            "source_prz_low": 90.0,
            "source_prz_high": 92.0,
            "source_terminal_trade_date": None,
        },
        enrollment_state="prospective_new",
    )
    assert eligible is False
    assert reason == "candidate_not_formal_validation_eligible"


def test_entries_from_analysis_marks_raw_fallback_ineligible() -> None:
    analysis = {
        "instrument_id": "SSE.600000",
        "last_trade_date": "2026-09-18",
        "price_mode": "raw",
        "price_basis_id": "raw",
        "bars": [],
        "context_integrity": {"summary_state": "complete"},
        "completed": [],
        "forming": [_pattern("ABCD")],
    }
    rows = entries_from_analysis(analysis, code_head="abc")
    assert len(rows) == 1
    assert rows[0].eligible_for_validation is False
    assert rows[0].price_mode == "raw"
    assert rows[0].price_basis_id == "raw"



def test_prospective_outcome_gate_requires_complete_source_clock_seed() -> None:
    payload = {
        "as_of_trade_date": "2026-09-18",
        "pattern_id": "abcd",
        "eligible_for_validation": True,
        "price_mode": "qfq",
        "price_basis_id": FORMAL_BASIS,
        "pattern_state": "forming",
        "source_lifecycle_state": "waiting_terminal",
        "source_prz_low": 90.0,
        "source_prz_high": 92.0,
        "source_terminal_trade_date": None,
    }
    eligible, reason = prospective_outcome_gate(
        payload,
        enrollment_state="prospective_new",
    )
    assert eligible is False
    assert reason == "source_clock_seed_unresolved"


def test_entries_from_analysis_freezes_source_clock_seed() -> None:
    pattern = _pattern("ABCD")
    analysis = {
        "instrument_id": "SSE.600000",
        "last_trade_date": "2026-09-18",
        "price_mode": "qfq",
        "price_basis_id": FORMAL_BASIS,
        "bars": [{
            "index": 0,
            "trade_date": SOURCE_SIGNAL_DATE,
            "open": 10.0,
            "high": 10.5,
            "low": 9.9,
            "close": 10.4,
            "volume": 1200,
        }],
        "context_integrity": {"summary_state": "complete"},
        "completed": [],
        "forming": [pattern],
    }
    rows = entries_from_analysis(analysis, code_head="abc")
    assert len(rows) == 1
    row = rows[0]
    assert row.source_signal_trade_date == SOURCE_SIGNAL_DATE
    assert row.source_signal_clock_basis == SOURCE_CLOCK_BASIS
    assert row.source_reaction_anchor_label == "A"
    assert row.source_reaction_anchor_price == 101.0
