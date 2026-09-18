from __future__ import annotations

from datetime import date

import duckdb
import pytest

from htcn.data.trading_events import (
    SecurityDailyEventRecord,
    sync_daily_trading_events,
    upsert_security_daily_events,
)


class _Provider:
    name = "fake"
    event_source = "fake_positive_events"

    def __init__(self, records=None, error: Exception | None = None) -> None:
        self.records = records or []
        self.error = error

    def get_daily_trading_events(self, trade_date: date):
        if self.error is not None:
            raise self.error
        return list(self.records)


def _record(*, complete: bool, status: str, source: str) -> SecurityDailyEventRecord:
    return SecurityDailyEventRecord(
        instrument_id="SSE.600000",
        trade_date=date(2026, 9, 18),
        trading_status=status,
        no_price_limit=False if complete else None,
        price_limit_pct_override=10.0 if complete else None,
        resolution_complete=complete,
        source=source,
        reason=source,
    )


def test_partial_event_cannot_downgrade_complete_event(tmp_path) -> None:
    catalog = tmp_path / "catalog.duckdb"
    upsert_security_daily_events(
        catalog, [_record(complete=True, status="normal", source="complete")]
    )
    upsert_security_daily_events(
        catalog, [_record(complete=False, status="suspended", source="partial")]
    )

    with duckdb.connect(str(catalog), read_only=True) as con:
        row = con.execute(
            """SELECT trading_status, resolution_complete, source,
                      no_price_limit, price_limit_pct_override
               FROM security_daily_event"""
        ).fetchone()
    assert row == ("normal", True, "complete", False, 10.0)


def test_successful_empty_positive_feed_is_audited_but_does_not_invent_normal_rows(
    tmp_path,
) -> None:
    catalog = tmp_path / "catalog.duckdb"
    stored = sync_daily_trading_events(
        catalog_path=catalog,
        provider=_Provider(),
        trade_date=date(2026, 9, 18),
    )
    assert stored == 0

    with duckdb.connect(str(catalog), read_only=True) as con:
        event_count = con.execute("SELECT COUNT(*) FROM security_daily_event").fetchone()[0]
        audit = con.execute(
            """SELECT status, record_count, coverage_scope
               FROM security_daily_event_sync"""
        ).fetchone()
    assert event_count == 0
    assert audit == ("success", 0, "positive_evidence_only")


def test_failed_feed_is_audited_and_re_raised(tmp_path) -> None:
    catalog = tmp_path / "catalog.duckdb"
    with pytest.raises(RuntimeError, match="provider down"):
        sync_daily_trading_events(
            catalog_path=catalog,
            provider=_Provider(error=RuntimeError("provider down")),
            trade_date=date(2026, 9, 18),
        )

    with duckdb.connect(str(catalog), read_only=True) as con:
        row = con.execute(
            "SELECT status, coverage_scope, error_message FROM security_daily_event_sync"
        ).fetchone()
    assert row[0] == "failed"
    assert row[1] == "positive_evidence_only"
    assert "provider down" in row[2]
