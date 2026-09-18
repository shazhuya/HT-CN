from datetime import datetime
from zoneinfo import ZoneInfo

from htcn.data.trading_clock import latest_closed_trade_clock


class _Provider:
    name = "mock"

    def __init__(self, days):
        self.days = days
        self.last_provider = "mock_calendar"

    def get_trade_calendar(self, start, end):
        return [day for day in self.days if start <= day <= end]


def test_before_close_uses_previous_closed_trade_day() -> None:
    from datetime import date
    provider = _Provider([date(2026, 9, 17), date(2026, 9, 18)])
    clock = latest_closed_trade_clock(
        provider,
        now=datetime(2026, 9, 18, 11, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
    )
    assert clock.target.isoformat() == "2026-09-17"
    assert clock.same_day_closed is False


def test_after_close_can_use_same_day() -> None:
    from datetime import date
    provider = _Provider([date(2026, 9, 17), date(2026, 9, 18)])
    clock = latest_closed_trade_clock(
        provider,
        now=datetime(2026, 9, 18, 17, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
    )
    assert clock.target.isoformat() == "2026-09-18"
    assert clock.same_day_closed is True
