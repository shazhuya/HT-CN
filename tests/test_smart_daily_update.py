from datetime import date, datetime
from zoneinfo import ZoneInfo

from scripts.m1_daily_update import latest_closed_trade_dates


class FakeCalendarProvider:
    def get_trade_calendar(self, start: date, end: date) -> list[date]:
        days = [date(2026, 9, 14), date(2026, 9, 15)]
        return [day for day in days if start <= day <= end]


def test_before_close_targets_previous_completed_trade_day() -> None:
    now = datetime(2026, 9, 15, 14, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    target, previous, snapshot = latest_closed_trade_dates(FakeCalendarProvider(), now=now)
    assert target == date(2026, 9, 14)
    assert previous is None
    assert snapshot is False


def test_after_close_targets_today_and_allows_bulk_snapshot() -> None:
    now = datetime(2026, 9, 15, 17, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    target, previous, snapshot = latest_closed_trade_dates(FakeCalendarProvider(), now=now)
    assert target == date(2026, 9, 15)
    assert previous == date(2026, 9, 14)
    assert snapshot is True
