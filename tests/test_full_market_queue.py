from datetime import date

from htcn.data.catalog import DataCatalog
from htcn.data.models import Board, Exchange, Security


def securities() -> list[Security]:
    return [
        Security("SSE.600001", "600001", Exchange.SSE, "A", Board.MAIN),
        Security("SZSE.000001", "000001", Exchange.SZSE, "B", Board.MAIN),
        Security("SSE.688001", "688001", Exchange.SSE, "C", Board.STAR),
    ]


def record_dataset(catalog: DataCatalog, instrument_id: str) -> None:
    catalog.record_daily(
        instrument_id=instrument_id,
        source="test",
        parquet_path=f"{instrument_id}.parquet",
        row_count=10,
        first_trade_date=date(2026, 1, 1).isoformat(),
        last_trade_date=date(2026, 1, 10).isoformat(),
    )


def test_queue_skips_completed_dataset_and_resumes_interrupted(tmp_path) -> None:
    catalog = DataCatalog(tmp_path / "catalog.duckdb")
    catalog.upsert_securities(securities(), source="test")

    catalog.begin_task("SSE.600001")
    record_dataset(catalog, "SSE.600001")
    catalog.finish_task("SSE.600001", "COMPLETED")

    catalog.begin_task("SZSE.000001")
    catalog.finish_task("SZSE.000001", "INTERRUPTED", "stopped")

    candidates = catalog.sync_candidates(max_attempts=5)
    assert "SSE.600001" not in candidates
    assert "SZSE.000001" in candidates
    assert "SSE.688001" in candidates


def test_attempt_count_increments_once_per_run(tmp_path) -> None:
    catalog = DataCatalog(tmp_path / "catalog.duckdb")
    catalog.upsert_securities(securities(), source="test")

    catalog.begin_task("SSE.688001")
    catalog.finish_task("SSE.688001", "FAILED", "network")
    first = catalog.task_status("SSE.688001")
    assert first is not None
    assert first["attempt_count"] == 1

    catalog.begin_task("SSE.688001")
    catalog.finish_task("SSE.688001", "FAILED", "network again")
    second = catalog.task_status("SSE.688001")
    assert second is not None
    assert second["attempt_count"] == 2


def test_queue_respects_max_attempts_and_limit(tmp_path) -> None:
    catalog = DataCatalog(tmp_path / "catalog.duckdb")
    catalog.upsert_securities(securities(), source="test")

    for _ in range(2):
        catalog.begin_task("SSE.688001")
        catalog.finish_task("SSE.688001", "FAILED", "network")

    candidates = catalog.sync_candidates(max_attempts=2)
    assert "SSE.688001" not in candidates

    limited = catalog.sync_candidates(max_attempts=5, limit=1)
    assert len(limited) == 1
