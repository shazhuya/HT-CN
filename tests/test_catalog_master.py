from datetime import date

from htcn.data.catalog import DataCatalog
from htcn.data.models import Board, Exchange, Security


def test_catalog_persists_security_master_and_calendar(tmp_path) -> None:
    catalog = DataCatalog(tmp_path / "catalog.duckdb")
    securities = [
        Security(
            instrument_id="SSE.688256",
            symbol="688256",
            exchange=Exchange.SSE,
            name="寒武纪",
            board=Board.STAR,
            list_date=date(2020, 7, 20),
        ),
        Security(
            instrument_id="SZSE.300820",
            symbol="300820",
            exchange=Exchange.SZSE,
            name="英杰电气",
            board=Board.CHINEXT,
        ),
    ]

    assert catalog.upsert_securities(securities, source="test") == 2
    assert catalog.security_count() == 2
    assert catalog.record_trade_calendar(
        [date(2026, 9, 14), date(2026, 9, 15)], source="test"
    ) == 2
    assert catalog.calendar_count() == 2

    # Upserts must remain idempotent.
    catalog.upsert_securities(securities, source="test")
    catalog.record_trade_calendar([date(2026, 9, 15)], source="test")
    assert catalog.security_count() == 2
    assert catalog.calendar_count() == 2


def test_sync_task_state_is_resumable(tmp_path) -> None:
    catalog = DataCatalog(tmp_path / "catalog.duckdb")
    instrument_id = "SSE.688256"

    # One RUNNING -> terminal transition is one attempt. Finishing a task must not
    # inflate attempt_count; only starting a new attempt increments the counter.
    catalog.mark_task(instrument_id, "RUNNING")
    catalog.mark_task(instrument_id, "FAILED", "temporary provider error")
    state = catalog.task_status(instrument_id)
    assert state is not None
    assert state["status"] == "FAILED"
    assert state["attempt_count"] == 1

    # A resumed retry is a second attempt.
    catalog.mark_task(instrument_id, "RUNNING")
    state = catalog.task_status(instrument_id)
    assert state is not None
    assert state["status"] == "RUNNING"
    assert state["attempt_count"] == 2

    catalog.mark_task(instrument_id, "COMPLETED")
    state = catalog.task_status(instrument_id)
    assert state is not None
    assert state["status"] == "COMPLETED"
    assert state["attempt_count"] == 2
