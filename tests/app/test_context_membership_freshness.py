from htcn.app.context_integrity import build_context_integrity


def test_old_membership_marks_industry_and_concept_stale_even_with_current_snapshots() -> None:
    result = build_context_integrity(
        as_of_trade_date="2026-09-18",
        execution_context={
            "as_of_trade_date": "2026-09-18",
            "special_event_exceptions_unresolved": False,
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
            "mapping_observed_on": "2026-09-01",
            "snapshot_trade_date": "2026-09-18",
            "mapping_source": "industry",
            "total_member_count": 100,
            "return_20d_count": 90,
        },
        concept_context={
            "status": "resolved",
            "mapping_observed_on": "2026-09-01",
            "mapping_source": "concept",
            "membership_count": 1,
            "resolved_count": 1,
            "concepts": [{"snapshot_trade_date": "2026-09-18"}],
        },
        membership_max_age_days=7,
    )
    states = {item.layer: item.state for item in result.layers}
    assert states["industry"] == "stale"
    assert states["concept"] == "stale"
