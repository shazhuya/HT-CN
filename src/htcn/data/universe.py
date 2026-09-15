from __future__ import annotations


SUPPORTED_INITIAL_DAILY_PREFIXES = ("SSE.", "SZSE.")


def select_initial_daily_candidates(
    candidates: list[str],
    *,
    limit: int = 0,
) -> tuple[list[str], int]:
    """Select the currently supported initial daily-history universe.

    M1 initializes Shanghai and Shenzhen first. Beijing Stock Exchange securities are
    deliberately deferred until the dedicated 920-code continuity adapter is available,
    because the 2025 code migration requires old/new-code history stitching rather than a
    simple provider symbol substitution.

    The limit is applied *after* filtering so validation batches do not get consumed by
    deferred BSE symbols that sort before SSE/SZSE identifiers.
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
