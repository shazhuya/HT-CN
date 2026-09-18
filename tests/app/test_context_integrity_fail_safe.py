from htcn.app.context_integrity import build_context_integrity


def test_missing_execution_payload_is_not_marked_current() -> None:
    result = build_context_integrity(
        as_of_trade_date="2026-09-18",
        execution_context=None,
        market_context=None,
        sector_context=None,
        concept_context=None,
    )
    layer = next(item for item in result.layers if item.layer == "execution")
    assert layer.state == "missing"
    assert result.summary_state == "issues_present"


def test_execution_context_date_mismatch_is_stale() -> None:
    result = build_context_integrity(
        as_of_trade_date="2026-09-18",
        execution_context={
            "as_of_trade_date": "2026-09-17",
            "special_event_exceptions_unresolved": False,
            "bse_deferred": False,
        },
        market_context=None,
        sector_context=None,
        concept_context=None,
    )
    layer = next(item for item in result.layers if item.layer == "execution")
    assert layer.state == "stale"
