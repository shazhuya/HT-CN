from scripts.m4_build_outcome_report import render_markdown


def test_outcome_report_keeps_performance_boundaries_explicit() -> None:
    payload = {
        "status": "ready",
        "outcome_as_of_trade_date": "2026-09-28",
        "outcome_protocol_id": "m4-outcome-v2",
        "outcome_protocol_fingerprint": "a" * 64,
        "capture_methodology_fingerprint": "b" * 64,
        "candidate_count": 1,
        "outcome_snapshot_id": "abc",
        "status_counts": {"right_censored_ongoing": 1},
        "results": [{
            "candidate_key": "k",
            "status": "right_censored_ongoing",
            "market_path_traded_bar_count": 5,
            "market_path_sha256": "c" * 64,
            "source_events": {
                "source_terminal_trade_date": None,
                "type_i_early_result": "not_started",
                "type_ii_price_structure_status": (
                    "not_observed_right_censored"
                ),
            },
        }],
    }
    text = render_markdown(payload)
    assert "M1 base + daily_delta logical history" in text
    assert "Terminal 未出现属于 right-censored" in text
    assert "不计算 win rate / alpha" in text
    assert "不包含 Terminal bar" in text
