from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date
from typing import Protocol

import pandas as pd

from .validation import normalize_daily


class AdjustedHistoryProvider(Protocol):
    name: str

    def get_daily_adjusted(
        self,
        instrument_id: str,
        start: date,
        end: date,
        *,
        mode: str = "qfq",
    ) -> pd.DataFrame: ...


@dataclass(slots=True)
class AdjustedFetchResult:
    frame: pd.DataFrame
    source: str
    attempts: int


def fetch_adjusted_history(
    *,
    instrument_id: str,
    start: date,
    end: date,
    providers: list[AdjustedHistoryProvider],
    mode: str = "qfq",
    retries_per_provider: int = 2,
    base_delay: float = 0.75,
) -> AdjustedFetchResult:
    """Fetch adjusted daily history with retry, validation and provider failover.

    Live free endpoints occasionally close connections, throttle requests, or return a
    provider-specific dtype layout. The fetch boundary therefore normalizes every
    successful response into HT-CN's canonical daily schema before the factor layer sees
    it. A malformed provider response is treated the same way as a transient provider
    failure so another source can take over.
    """
    if mode not in {"qfq", "hfq"}:
        raise ValueError("mode must be 'qfq' or 'hfq'")
    if not providers:
        raise ValueError("at least one adjusted-history provider is required")

    attempts = 0
    errors: list[str] = []
    tries = max(1, retries_per_provider + 1)

    for provider in providers:
        for retry in range(tries):
            attempts += 1
            try:
                frame = provider.get_daily_adjusted(
                    instrument_id,
                    start,
                    end,
                    mode=mode,
                )
                if frame is not None and not frame.empty:
                    normalized = normalize_daily(frame)
                    return AdjustedFetchResult(
                        frame=normalized,
                        source=f"{provider.name}_{mode}",
                        attempts=attempts,
                    )
                errors.append(f"{provider.name}: empty response")
            except Exception as exc:
                errors.append(f"{provider.name}: {type(exc).__name__}: {exc}")

            if retry < tries - 1 and base_delay > 0:
                time.sleep(min(6.0, base_delay * (2**retry)))

    tail = " | ".join(errors[-6:])
    raise RuntimeError(
        f"all adjusted-history providers failed for {instrument_id} {mode}; {tail}"
    )
