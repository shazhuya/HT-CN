from scripts.m4_audit_t0_baseline import render_markdown


def test_t0_markdown_separates_transition_from_outcome_readiness() -> None:
    payload = {
        "status": "pass_with_warnings",
        "baseline_trade_date": "2026-09-17",
        "journal_row_count": 87,
        "unique_candidate_count": 87,
        "candidate_bearing_instrument_count": 44,
        "blocker_count": 0,
        "warning_count": 1,
        "blockers": [],
        "warnings": [{"code": "pattern_concentration", "detail": "ABCD concentrated"}],
        "transition_ready": True,
        "prospective_outcome_ready": False,
        "prospective_outcome_reason": "T0 is baseline inventory.",
        "pattern_counts": {"abcd": 56},
        "schema_counts": {"ABCD": 56},
        "direction_counts": {"bullish": 39, "bearish": 48},
        "scale_counts": {"13": 30},
        "lifecycle_counts": {"approaching_source_prz": 50},
        "action_counts": {"waiting": 65},
        "source_terminal_age_buckets": {},
    }
    text = render_markdown(payload)
    assert "T1 transition ready：**True**" in text
    assert "Prospective outcome ready：**False**" in text
    assert "不使用综合评分" in text
    assert "不产生 alpha / 胜率 / 买卖结论" in text
