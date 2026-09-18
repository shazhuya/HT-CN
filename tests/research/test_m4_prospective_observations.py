from htcn.research.prospective_observations import build_prospective_observation_report


def _row(date: str, key: str, *, state: str = "waiting_terminal"):
    return {
        "code_head": "h",
        "instrument_id": "SSE.600000",
        "as_of_trade_date": date,
        "candidate_key": key,
        "pattern_id": "abcd",
        "pattern_state": "forming",
        "schema": "ABCD",
        "direction": "bullish",
        "scale": 5,
        "source_lifecycle_state": state,
        "action_state": "waiting" if state != "type_i_confirmed" else "execution_evaluation",
        "next_key_price": 100.0,
        "next_key_price_role": (
            "source_prz_terminal_side" if state == "waiting_terminal" else "type_i_61_8_target"
        ),
        "execution_context_gate": "tradable",
        "context_integrity_summary": "complete",
        "source_prz_low": 90.0,
        "source_prz_high": 92.0,
        "source_terminal_trade_date": None,
        "as_of_open": 100.0,
        "as_of_high": 102.0,
        "as_of_low": 99.0,
        "as_of_close": 101.0,
        "as_of_volume": 1000.0,
    }


def test_t0_baseline_has_no_prospective_outcome_cohort() -> None:
    report = build_prospective_observation_report([_row("2026-09-17", "baseline")])
    assert report["status"] == "no_outcome_cohort"
    assert report["prospective_candidate_count"] == 0
    assert report["observation_count"] == 0
    assert report["interpretation"]["return_metrics_computed"] is False


def test_enrolled_candidate_tracks_present_snapshots_and_milestones() -> None:
    t2 = _row("2026-09-19", "new", state="type_i_confirmed")
    t2["source_terminal_trade_date"] = "2026-09-18"
    rows = [
        _row("2026-09-17", "baseline"),
        _row("2026-09-18", "new"),
        t2,
    ]
    report = build_prospective_observation_report(rows)
    assert report["status"] == "observations_available"
    assert report["prospective_candidate_count"] == 1
    observations = report["observations"]
    assert [item["captured_snapshot_index"] for item in observations] == [0, 1]
    assert all(item["scanner_presence"] == "present" for item in observations)
    summary = report["candidate_summaries"][0]
    assert summary["outcome_enrollment_trade_date"] == "2026-09-18"
    assert summary["first_source_terminal_trade_date"] == "2026-09-18"
    assert summary["first_lifecycle_state_observed"]["type_i_confirmed"] == "2026-09-19"


def test_scanner_gap_is_recorded_without_invalidation_and_can_reappear() -> None:
    rows = [
        _row("2026-09-17", "baseline"),
        _row("2026-09-18", "new"),
        _row("2026-09-19", "other"),
        _row("2026-09-20", "new", state="type_i_confirmed"),
        _row("2026-09-20", "other"),
    ]
    report = build_prospective_observation_report(rows)
    observations = [
        item for item in report["observations"] if item["candidate_key"] == "new"
    ]
    assert [item["scanner_presence"] for item in observations] == [
        "present", "absent", "present"
    ]
    assert observations[1]["consecutive_absent_snapshots"] == 1
    summary = next(
        item for item in report["candidate_summaries"] if item["candidate_key"] == "new"
    )
    assert summary["first_scanner_absent_date"] == "2026-09-19"
    assert summary["first_scanner_reappeared_date"] == "2026-09-20"
    assert report["interpretation"]["scanner_absence_is_invalidation"] is False


def test_backdated_source_terminal_after_enrollment_fails_closed() -> None:
    later = _row("2026-09-19", "new", state="type_i_confirmed")
    later["source_terminal_trade_date"] = "2026-09-17"
    rows = [
        _row("2026-09-17", "baseline"),
        _row("2026-09-18", "new"),
        later,
    ]
    try:
        build_prospective_observation_report(rows)
    except ValueError as exc:
        assert "predates outcome enrollment" in str(exc)
    else:
        raise AssertionError("backdated Source Terminal must fail closed")


def test_observation_schema_does_not_compute_return_or_profit_fields() -> None:
    rows = [_row("2026-09-17", "baseline"), _row("2026-09-18", "new")]
    report = build_prospective_observation_report(rows)
    observation = report["observations"][0]
    assert "return_pct" not in observation
    assert "profit" not in observation
    assert report["interpretation"]["profit_threshold_defined"] is False
