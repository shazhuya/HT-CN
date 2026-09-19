from __future__ import annotations

SUPPORTED_INITIAL_DAILY_PREFIXES = ("SSE.", "SZSE.")


def select_initial_daily_candidates(
    candidates: list[str],
    *,
    limit: int = 0,
) -> tuple[list[str], int]:
    """Select the current HT-CN daily-history universe.

    The active M1 scope is Shanghai + Shenzhen only. Beijing Stock Exchange securities are
    intentionally out of scope for now and must not block, consume validation-batch slots,
    or distort completion percentages. BSE support can be added later as an independent
    adapter/milestone without changing the SSE/SZSE data path.

    The limit is applied *after* filtering.
    """

    deferred_bse = sum(instrument_id.startswith("BSE.") for instrument_id in candidates)
    selected = [
        instrument_id
        for instrument_id in candidates
        if instrument_id.startswith(SUPPORTED_INITIAL_DAILY_PREFIXES)
    ]
    if limit > 0:
        selected = selected[:limit]
    return selected, deferred_bse
