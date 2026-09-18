from __future__ import annotations

from htcn.research.lifecycle_transitions import (
    build_transition_report,
    build_transitions,
)


def _row(
    date: str,
    key: str,
    lifecycle: str = "approaching_source_prz",
    action: str = "waiting",
    *,
    enrollment: str | None = None,
    first_observed: str | None = None,
):
    row = {
        "code_head": "h",
        "instrument_id": "SSE.688256",
        "as_of_trade_date": date,
        "candidate_key": key,
        "pattern_id": "abcd",
        "schema": "ABCD",
        "direction": "bullish",
        "scale": 5,
        "source_lifecycle_state": lifecycle,
        "action_state": action,
        "next_key_price": 100.0,
    }
    if enrollment is not None:
        row["enrollment_state"] = enrollment
    if first_observed is not None:
        row["first_observed_trade_date"] = first_observed
    return row


def test_single_t0_snapshot_is_baseline_only() -> None:
    report = build_transition_report([
        _row("2026-09-17", "a"),
        _row("2026-09-17", "b", lifecycle="waiting_terminal"),
    ])
    assert report["status"] == "baseline_only"
    assert report["cohort_counts"] == {"baseline_existing": 2}
    assert report["transition_counts"] == {"baseline_observed": 2}
    assert report["interpretation"]["alpha_inference_allowed"] is False


def test_new_candidate_after_t0_is_prospective_new() -> None:
    rows = [
        _row("2026-09-17", "old"),
        _row("2026-09-18", "old"),
        _row("2026-09-18", "new", lifecycle="waiting_terminal"),
    ]
    transitions = build_transitions(rows)
    new = next(item for item in transitions if item.candidate_key == "new")
    assert new.transition_kind == "new_candidate"
    assert new.enrollment_state == "prospective_new"
    assert new.first_observed_trade_date == "2026-09-18"


def test_existing_baseline_candidate_never_becomes_prospective_new() -> None:
    rows = [
        _row("2026-09-17", "old"),
        _row("2026-09-18", "old", lifecycle="waiting_terminal"),
    ]
    transitions = build_transitions(rows)
    latest = [item for item in transitions if item.candidate_key == "old"][-1]
    assert latest.enrollment_state == "baseline_existing"
    assert latest.transition_kind == "lifecycle_changed"


def test_scanner_disappearance_is_not_invalidated() -> None:
    rows = [
        _row("2026-09-17", "gone", lifecycle="waiting_terminal"),
        _row("2026-09-18", "other"),
    ]
    transitions = build_transitions(rows)
    gone = next(item for item in transitions if item.candidate_key == "gone" and item.to_trade_date == "2026-09-18")
    assert gone.transition_kind == "scanner_disappeared"
    assert gone.to_lifecycle_state is None
    assert gone.scanner_presence == "absent"


def test_action_only_change_is_separate_from_lifecycle_change() -> None:
    rows = [
        _row("2026-09-17", "a", lifecycle="type_i_confirmed", action="waiting"),
        _row("2026-09-18", "a", lifecycle="type_i_confirmed", action="execution_evaluation"),
    ]
    latest = build_transitions(rows)[-1]
    assert latest.transition_kind == "action_changed_only"


def test_lifecycle_change_is_recorded_without_linear_rank_claim() -> None:
    rows = [
        _row("2026-09-17", "a", lifecycle="type_i_confirmed"),
        _row("2026-09-18", "a", lifecycle="type_i_failed"),
    ]
    report = build_transition_report(rows)
    assert report["lifecycle_pair_counts"] == {
        "type_i_confirmed->type_i_failed": 1
    }
    assert report["interpretation"]["linear_lifecycle_ranking_used"] is False


def test_duplicate_candidate_within_same_snapshot_fails_closed() -> None:
    rows = [
        _row("2026-09-17", "dup"),
        _row("2026-09-17", "dup"),
    ]
    try:
        build_transition_report(rows)
    except ValueError as exc:
        assert "duplicate candidate_key" in str(exc)
    else:
        raise AssertionError("duplicate same-day candidate must fail closed")


def test_explicit_first_observed_drift_fails_closed() -> None:
    rows = [
        _row("2026-09-17", "a"),
        _row(
            "2026-09-18",
            "a",
            enrollment="baseline_existing",
            first_observed="2026-09-18",
        ),
    ]
    try:
        build_transition_report(rows)
    except ValueError as exc:
        assert "first_observed_trade_date drift" in str(exc)
    else:
        raise AssertionError("first-observed drift must fail closed")


def test_candidate_reappearing_after_gap_is_not_new_candidate() -> None:
    rows = [
        _row("2026-09-17", "a", lifecycle="waiting_terminal"),
        _row("2026-09-18", "other"),
        _row("2026-09-19", "a", lifecycle="type_i_early_reaction"),
        _row("2026-09-19", "other"),
    ]
    transitions = build_transitions(rows)
    reappeared = next(
        item
        for item in transitions
        if item.candidate_key == "a"
        and item.to_trade_date == "2026-09-19"
    )
    assert reappeared.transition_kind == "scanner_reappeared"
    assert reappeared.enrollment_state == "baseline_existing"
    assert reappeared.first_observed_trade_date == "2026-09-17"
    assert reappeared.from_trade_date == "2026-09-17"
    assert reappeared.from_lifecycle_state == "waiting_terminal"
    assert reappeared.to_lifecycle_state == "type_i_early_reaction"
