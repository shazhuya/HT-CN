from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import duckdb

from htcn.app.universe_coverage import (
    build_universe_coverage,
    load_catalog_universes,
    universe_hash,
)


def test_coverage_contract_separates_every_universe_layer() -> None:
    payload = build_universe_coverage(
        listed_ids=[
            "SSE.600001",
            "SSE.600002",
            "SZSE.000001",
            "BSE.920001",
        ],
        initialized_ids=[
            "SSE.600001",
            "SZSE.000001",
            "BSE.920001",
        ],
        qfq_ready_ids=["SSE.600001", "BSE.920001"],
        operator_ids=["SSE.600001", "SZSE.000001"],
    )

    layers = payload["layers"]
    assert layers["listed_universe"]["instrument_ids"] == [
        "SSE.600001",
        "SSE.600002",
        "SZSE.000001",
    ]
    assert layers["initialized_universe"]["instrument_ids"] == [
        "SSE.600001",
        "SZSE.000001",
    ]
    assert layers["formal_qfq_ready_universe"]["instrument_ids"] == [
        "SSE.600001",
    ]
    assert layers["scanner_universe"] == layers["operator_universe"]
    assert layers["research_scanner_universe"] == (
        layers["formal_qfq_ready_universe"]
    )
    assert payload["gaps"]["listed_not_initialized"]["instrument_ids"] == [
        "SSE.600002"
    ]
    assert payload["gaps"]["deferred_bse"]["instrument_ids"] == [
        "BSE.920001"
    ]
    assert payload["coverage_claim"]["may_claim_full_a_share_coverage"] is False
    assert payload["coverage_claim"]["initialized_may_be_called_full_a_share"] is False
    assert payload["invariants"]["operator_equals_scanner"] is True
    assert payload["invariants"]["bse_excluded_from_default_scope"] is True
    assert payload["status"] == "valid"


def test_same_exchange_invalid_parentage_fails_closed() -> None:
    payload = build_universe_coverage(
        listed_ids=["SSE.600001", "SZSE.000001"],
        initialized_ids=[
            "SSE.600001",
            "SZSE.000001",
            "SSE.699999",
        ],
        qfq_ready_ids=[
            "SSE.600001",
            "SZSE.399999",
        ],
        operator_ids=["SSE.600001", "SZSE.000001"],
    )

    assert payload["status"] == "invalid"
    assert payload["invariants"]["initialized_subset_of_listed"] is False
    assert payload["invariants"]["formal_qfq_subset_of_initialized"] is False
    assert payload["gaps"]["invalid_initialized_not_listed"]["instrument_ids"] == [
        "SSE.699999"
    ]
    assert payload["gaps"]["invalid_formal_qfq_not_initialized"]["instrument_ids"] == [
        "SZSE.399999"
    ]


def test_operator_mismatch_fails_the_contract() -> None:
    payload = build_universe_coverage(
        listed_ids=["SSE.600001", "SZSE.000001"],
        initialized_ids=["SSE.600001", "SZSE.000001"],
        qfq_ready_ids=["SSE.600001"],
        operator_ids=["SSE.600001"],
    )

    assert payload["invariants"]["operator_equals_scanner"] is False
    assert payload["status"] == "invalid"


def test_universe_hash_is_order_and_duplicate_stable() -> None:
    left = universe_hash(["SZSE.000001", "SSE.600001", "SSE.600001"])
    right = universe_hash(["SSE.600001", "SZSE.000001"])
    assert left == right


def _init_catalog(path: Path) -> None:
    with duckdb.connect(str(path)) as con:
        con.execute(
            """
            CREATE TABLE security_master (
                instrument_id VARCHAR PRIMARY KEY,
                symbol VARCHAR NOT NULL,
                exchange VARCHAR NOT NULL,
                name VARCHAR NOT NULL,
                board VARCHAR NOT NULL,
                list_date DATE,
                delist_date DATE,
                is_st BOOLEAN NOT NULL,
                status VARCHAR NOT NULL,
                source VARCHAR NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            """
        )
        con.execute(
            """
            CREATE TABLE daily_dataset (
                instrument_id VARCHAR PRIMARY KEY,
                source VARCHAR NOT NULL,
                parquet_path VARCHAR NOT NULL,
                row_count BIGINT NOT NULL,
                first_trade_date DATE,
                last_trade_date DATE,
                updated_at TIMESTAMP NOT NULL
            )
            """
        )


def test_catalog_universe_excludes_bse_delisted_and_orphan_files(
    tmp_path: Path,
) -> None:
    root = tmp_path / "data" / "market"
    daily = root / "daily"
    daily.mkdir(parents=True)
    catalog = root / "catalog.duckdb"
    _init_catalog(catalog)
    now = datetime(2026, 9, 20, tzinfo=UTC)

    valid_sse = daily / "SSE.600001.parquet"
    valid_szse = daily / "SZSE.000001.parquet"
    bse_file = daily / "BSE.920001.parquet"
    delisted_file = daily / "SSE.600099.parquet"
    orphan_file = daily / "SSE.688999.parquet"
    for path in (
        valid_sse,
        valid_szse,
        bse_file,
        delisted_file,
        orphan_file,
    ):
        path.touch()

    with duckdb.connect(str(catalog)) as con:
        rows = [
            ("SSE.600001", "600001", "SSE", "A", "main", "listed"),
            ("SSE.600002", "600002", "SSE", "B", "main", "listed"),
            ("SZSE.000001", "000001", "SZSE", "C", "main", "listed"),
            ("BSE.920001", "920001", "BSE", "D", "bse", "listed"),
            ("SSE.600099", "600099", "SSE", "E", "main", "delisted"),
        ]
        for instrument_id, symbol, exchange, name, board, status in rows:
            con.execute(
                "INSERT INTO security_master VALUES "
                "(?, ?, ?, ?, ?, NULL, NULL, FALSE, ?, 'fixture', ?)",
                [instrument_id, symbol, exchange, name, board, status, now],
            )

        datasets = [
            ("SSE.600001", valid_sse, 100),
            ("SZSE.000001", valid_szse, 80),
            ("BSE.920001", bse_file, 50),
            ("SSE.600099", delisted_file, 70),
            ("SSE.600002", daily / "missing.parquet", 90),
        ]
        for instrument_id, path, rows_count in datasets:
            con.execute(
                "INSERT INTO daily_dataset VALUES "
                "(?, 'fixture', ?, ?, DATE '2026-01-01', "
                "DATE '2026-09-18', ?)",
                [instrument_id, str(path), rows_count, now],
            )

    payload = load_catalog_universes(root)

    assert payload["listed_ids"] == [
        "SSE.600001",
        "SSE.600002",
        "SZSE.000001",
    ]
    assert payload["initialized_ids"] == [
        "SSE.600001",
        "SZSE.000001",
    ]
    assert [row["instrument_id"] for row in payload["initialization_errors"]] == [
        "SSE.600002"
    ]
    assert "BSE.920001" in payload["excluded_local_ids"]
    assert "SSE.600099" in payload["excluded_local_ids"]
    assert "SSE.688999" in payload["excluded_local_ids"]


def test_qfq_not_evaluated_is_explicit_not_zero_ready() -> None:
    payload = build_universe_coverage(
        listed_ids=["SSE.600001"],
        initialized_ids=["SSE.600001"],
        qfq_evaluated=False,
        operator_ids=["SSE.600001"],
    )

    qfq = payload["layers"]["formal_qfq_ready_universe"]
    assert qfq["count"] is None
    assert qfq["status"] == "not_evaluated"
    assert payload["coverage"]["formal_qfq_over_initialized"] is None
    assert payload["status"] == "valid"
