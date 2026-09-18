from scripts.m4_build_transition_report import render_markdown


def test_markdown_keeps_disappearance_and_alpha_boundaries_explicit() -> None:
    payload = {
        "status": "transitions_available",
        "baseline_trade_date": "2026-09-17",
        "latest_trade_date": "2026-09-18",
        "date_count": 2,
        "journal_row_count": 4,
        "latest_candidate_count": 2,
        "cohort_counts": {
            "baseline_existing": 3,
            "prospective_new": 1,
        },
        "transition_counts": {
            "scanner_disappeared": 1,
            "new_candidate": 1,
        },
        "latest_lifecycle_state_counts": {
            "waiting_terminal": 2,
        },
        "lifecycle_pair_counts": {},
    }
    text = render_markdown(payload)
    assert "不等于 invalidated" in text
    assert "不使用线性 lifecycle 排名" in text
    assert "不计算胜率、收益率、alpha 或交易评分" in text
    assert "`prospective_new`：1" in text


def test_baseline_only_markdown_does_not_claim_transition() -> None:
    payload = {
        "status": "baseline_only",
        "baseline_trade_date": "2026-09-17",
        "latest_trade_date": "2026-09-17",
        "date_count": 1,
        "journal_row_count": 87,
        "latest_candidate_count": 87,
        "cohort_counts": {"baseline_existing": 87},
        "transition_counts": {"baseline_observed": 87},
        "latest_lifecycle_state_counts": {"approaching_source_prz": 50},
        "lifecycle_pair_counts": {},
    }
    text = render_markdown(payload)
    assert "baseline_existing" in text
    assert "当前没有可比较的跨交易日 lifecycle change" in text
