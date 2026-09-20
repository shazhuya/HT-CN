from htcn.research.m7_accumulation import build_m7_accumulation_status


def _health(*, captures: int = 1, blockers: int = 0):
    dates = [] if captures == 0 else ["2026-09-21"]
    return {
        "status": "not_ready" if blockers else "ready",
        "blocker_count": blockers,
        "committed_capture_count": captures,
        "committed_capture_dates": dates,
        "latest_committed_capture_date": dates[-1] if dates else None,
        "zero_candidate_capture_dates": [],
    }


def _observations(*, candidates: int = 1):
    summaries = []
    if candidates:
        summaries = [{
            "candidate_key": "c1",
            "captured_snapshot_count": 3,
            "absent_snapshot_count": 1,
            "price_basis_drift_snapshot_count": 0,
            "first_source_terminal_trade_date": "2026-09-22",
        }]
    return {
        "prospective_candidate_count": candidates,
        "observation_count": 3 if candidates else 0,
        "candidate_summaries": summaries,
    }


def _outcome_snapshot():
    return {
        "outcome_as_of_trade_date": "2026-09-23",
        "results": [{
            "candidate_key": "c1",
            "status": "right_censored_ongoing",
            "market_path_traded_bar_count": 2,
        }],
    }


def test_m7_status_waits_for_first_future_capture() -> None:
    payload = build_m7_accumulation_status(
        evidence_health=_health(captures=0),
        observation_report=_observations(candidates=0),
    )
    assert payload["status"] == "waiting_first_future_capture"
    assert payload["committed_capture_count"] == 0


def test_m7_status_does_not_relax_rules_when_no_cohort() -> None:
    payload = build_m7_accumulation_status(
        evidence_health=_health(),
        observation_report=_observations(candidates=0),
    )
    assert payload["status"] == "accumulating_no_outcome_cohort"
    assert "do not relax enrollment rules" in payload["next_action"]


def test_m7_status_summarizes_factual_accumulation() -> None:
    payload = build_m7_accumulation_status(
        evidence_health=_health(),
        observation_report=_observations(),
        outcome_snapshots=[_outcome_snapshot()],
    )
    assert payload["status"] == "accumulating"
    assert payload["source_terminal_observed_candidate_count"] == 1
    assert payload["scanner_absent_ever_candidate_count"] == 1
    assert payload["max_captured_snapshot_depth"] == 3
    assert payload["outcome_snapshot_count"] == 1
    assert payload["latest_outcome_status_counts"] == {
        "right_censored_ongoing": 1,
    }
    assert payload["latest_market_path_traded_bar_depth"] == {
        "min": 2,
        "max": 2,
    }


def test_m7_status_fails_closed_on_evidence_blocker() -> None:
    payload = build_m7_accumulation_status(
        evidence_health=_health(blockers=1),
        observation_report=_observations(),
        outcome_snapshots=[_outcome_snapshot()],
    )
    assert payload["status"] == "blocked"
    assert payload["blocker_count"] == 1


def test_m7_status_never_authorizes_statistical_or_trade_claims() -> None:
    payload = build_m7_accumulation_status(
        evidence_health=_health(),
        observation_report=_observations(),
        outcome_snapshots=[_outcome_snapshot()],
    )
    assert payload["issue_gate"] == "ISSUE-0066"
    assert payload["inference_boundary"] == {
        "statistical_inference_allowed": False,
        "alpha_inference_allowed": False,
        "win_rate_inference_allowed": False,
        "profitability_inference_allowed": False,
        "is_trade_instruction": False,
    }
