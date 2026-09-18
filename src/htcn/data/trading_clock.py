from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time as clock_time, timedelta
from zoneinfo import ZoneInfo

from htcn.data.provider import MarketDataProvider


SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
POST_CLOSE_CUTOFF = clock_time(16, 30)


@dataclass(frozen=True, slots=True)
class ClosedTradeClock:
    target: date
    previous: date | None
    same_day_closed: bool
    calendar_source: str | None


def latest_closed_trade_clock(
    provider: MarketDataProvider,
    *,
    now: datetime | None = None,
    lookback_days: int = 40,
) -> ClosedTradeClock:
    sh_now = (
        datetime.now(SHANGHAI_TZ)
        if now is None
        else now.replace(tzinfo=SHANGHAI_TZ)
        if now.tzinfo is None
        else now.astimezone(SHANGHAI_TZ)
    )
    after_cutoff = sh_now.timetz().replace(tzinfo=None) >= POST_CLOSE_CUTOFF
    candidate = sh_now.date() if after_cutoff else sh_now.date() - timedelta(days=1)
    days = sorted(
        set(
            provider.get_trade_calendar(
                candidate - timedelta(days=max(lookback_days, 7)),
                candidate,
            )
        )
    )
    if not days:
        raise RuntimeError(f"no trading day found before {candidate}")
    target = days[-1]
    previous = days[-2] if len(days) >= 2 else None
    source = getattr(provider, "last_provider", None) or getattr(provider, "name", None)
    return ClosedTradeClock(
        target=target,
        previous=previous,
        same_day_closed=after_cutoff and target == sh_now.date(),
        calendar_source=None if source is None else str(source),
    )
