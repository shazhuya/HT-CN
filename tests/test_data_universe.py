from htcn.data.universe import select_initial_daily_candidates


def test_bse_is_deferred_and_limit_is_applied_after_filtering() -> None:
    candidates = [
        "BSE.920000",
        "BSE.920001",
        "SSE.600000",
        "SZSE.000001",
        "SSE.688256",
    ]

    selected, deferred_bse = select_initial_daily_candidates(candidates, limit=2)

    assert selected == ["SSE.600000", "SZSE.000001"]
    assert deferred_bse == 2


def test_zero_limit_keeps_all_currently_supported_candidates() -> None:
    candidates = ["BSE.920000", "SZSE.300820", "SSE.688300"]

    selected, deferred_bse = select_initial_daily_candidates(candidates, limit=0)

    assert selected == ["SZSE.300820", "SSE.688300"]
    assert deferred_bse == 1
