from __future__ import annotations

from htcn.app.context_integrity import build_context_integrity


def test_context_integrity_reports_states_without_score() -> None:
    result = build_context_integrity(
        as_of_trade_date="2026-09-18",
        execution_context={
            "special_event_exceptions_unresolved": True,
            "daily_event_source": "partial_event_source",
            "bse_deferred": False,
        },
        market_context={
            "status": "complete",
            "benchmarks": [
                {"available": True, "as_of_trade_date": "2026-09-18"},
                {"available": True, "as_of_trade_date": "2026-09-18"},
                {"available": True, "as_of_trade_date": "2026-09-17"},
                {"available": True, "as_of_trade_date": "2026-09-18"},
            ],
        },
        sector_context={
            "status": "membership_ambiguous",
            "mapping_observed_on": "2026-09-18",
            "mapping_source": "industry",
        },
        concept_context={
            "status": "resolved",
            "mapping_source": "concept",
            "membership_count": 2,
            "resolved_count": 2,
            "concepts": [
                {"snapshot_trade_date": "2026-09-18"},
                {"snapshot_trade_date": "2026-09-18"},
            ],
        },
    )
    payload = result.as_payload()
    assert payload["summary_state"] == "issues_present"
    assert payload["is_score"] is False
    states = {item["layer"]: item["state"] for item in payload["layers"]}
    assert states == {
        "execution": "unresolved",
        "market": "stale",
        "industry": "conflicted",
        "concept": "current",
    }
    assert "score" not in payload


def test_context_integrity_can_be_all_current() -> None:
    result = build_context_integrity(
        as_of_trade_date="2026-09-18",
        execution_context={
            "special_event_exceptions_unresolved": False,
            "daily_event_source": "complete_event",
            "bse_deferred": False,
        },
        market_context={
            "status": "complete",
            "benchmarks": [
                {"available": True, "as_of_trade_date": "2026-09-18"},
                {"available": True, "as_of_trade_date": "2026-09-18"},
                {"available": True, "as_of_trade_date": "2026-09-18"},
                {"available": True, "as_of_trade_date": "2026-09-18"},
            ],
        },
        sector_context={
            "status": "resolved",
            "snapshot_trade_date": "2026-09-18",
            "mapping_source": "industry",
            "total_member_count": 100,
            "return_20d_count": 95,
        },
        concept_context={
            "status": "resolved",
            "mapping_source": "concept",
            "membership_count": 1,
            "resolved_count": 1,
            "concepts": [{"snapshot_trade_date": "2026-09-18"}],
        },
    )
    assert result.summary_state == "all_current"
    assert all(item.state == "current" for item in result.layers)
