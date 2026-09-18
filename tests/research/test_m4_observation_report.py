from scripts.m4_build_observation_report import render_markdown


def test_no_cohort_report_does_not_claim_outcomes() -> None:
    payload = {
        "status": "no_outcome_cohort",
        "captured_dates": ["2026-09-17"],
        "prospective_candidate_count": 0,
        "observation_count": 0,
        "scanner_presence_counts": {},
        "lifecycle_observation_counts": {},
        "candidate_summaries": [],
        "interpretation": {
            "capture_timeline_source": "journal_fallback",
        },
    }
    text = render_markdown(payload)
    assert "当前没有 prospective outcome cohort" in text
    assert "不计算 return / profit / win rate / alpha" in text


def test_candidate_summary_is_factual_not_scored() -> None:
    payload = {
        "status": "observations_available",
        "captured_dates": ["2026-09-18", "2026-09-19"],
        "prospective_candidate_count": 1,
        "observation_count": 2,
        "scanner_presence_counts": {"present": 2},
        "lifecycle_observation_counts": {"waiting_terminal": 1, "type_i_confirmed": 1},
        "candidate_summaries": [{
            "candidate_key": "k",
            "outcome_enrollment_trade_date": "2026-09-18",
            "captured_snapshot_count": 2,
            "present_snapshot_count": 2,
            "absent_snapshot_count": 0,
            "first_source_terminal_trade_date": "2026-09-19",
        }],
        "interpretation": {"capture_timeline_source": "manifest"},
    }
    text = render_markdown(payload)
    assert "enroll=2026-09-18" in text
    assert "买卖评分" in text
    assert "score" not in payload


def test_report_exposes_suspension_as_non_traded_continuity() -> None:
    payload = {
        "status": "observations_available",
        "captured_dates": ["2026-09-18", "2026-09-19"],
        "prospective_candidate_count": 1,
        "observation_count": 2,
        "scanner_presence_counts": {"present": 2},
        "market_observation_counts": {
            "traded": 1,
            "confirmed_full_day_suspended": 1,
        },
        "lifecycle_observation_counts": {"waiting_terminal": 2},
        "candidate_summaries": [{
            "candidate_key": "k",
            "outcome_enrollment_trade_date": "2026-09-18",
            "captured_snapshot_count": 2,
            "present_snapshot_count": 2,
            "absent_snapshot_count": 0,
            "confirmed_full_day_suspended_snapshot_count": 1,
            "first_source_terminal_trade_date": None,
        }],
        "interpretation": {"capture_timeline_source": "manifest"},
    }
    text = render_markdown(payload)
    assert "confirmed_full_day_suspended" in text
    assert "suspended=1" in text
    assert "不是 traded observation" in text
    assert "不伪造当日 OHLC" in text
