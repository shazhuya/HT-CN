from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from htcn.app.real_closeout_preflight import (
    REQUIRED_CHECK_SEVERITY,
    RealCloseoutPreflightContract,
    _catalog_probe,
    evaluate_real_closeout_preflight,
    make_check,
)


def _checks(
    *,
    failures: dict[str, str] | None = None,
) -> list:
    failures = failures or {}
    result = []
    for name in REQUIRED_CHECK_SEVERITY:
        result.append(
            make_check(
                name,
                passed=name not in failures,
                detail=failures.get(name, "ok"),
                data={},
            )
        )
    return result


def test_all_required_preflight_checks_ready() -> None:
    payload = evaluate_real_closeout_preflight(
        _checks(),
        root=".",
        head="a" * 40,
    )

    assert payload["status"] == "ready"
    assert payload["blocker_count"] == 0
    assert payload["warning_count"] == 0
    assert payload["next_action"] == "daily_close_and_phase19_may_start"
    assert payload["check_count"] == len(REQUIRED_CHECK_SEVERITY)
    assert payload["passed_count"] == len(REQUIRED_CHECK_SEVERITY)


def test_blocking_check_stops_before_any_mutation() -> None:
    payload = evaluate_real_closeout_preflight(
        _checks(failures={"remote_main_matches_head": "local_remote_mismatch"}),
        head="a" * 40,
    )

    assert payload["status"] == "blocked"
    assert payload["next_action"] == "stop_before_any_m1_or_product_mutation"
    assert (
        "remote_main_matches_head:local_remote_mismatch"
        in payload["errors"]
    )


def test_partial_listed_universe_is_warning_not_new_product_blocker() -> None:
    payload = evaluate_real_closeout_preflight(
        _checks(
            failures={
                "m1_full_listed_coverage": "partial_initialized_scope_allowed:55/5000"
            }
        )
    )

    assert payload["status"] == "ready_with_warnings"
    assert payload["blocker_count"] == 0
    assert payload["warning_count"] == 1
    assert payload["next_action"] == "daily_close_and_phase19_may_start"
    assert payload["checks"]["m1_full_listed_coverage"]["severity"] == "warning"


def test_low_recommended_disk_is_warning_but_below_minimum_blocks() -> None:
    recommended = evaluate_real_closeout_preflight(
        _checks(failures={"free_disk_recommended": "free_bytes=2147483648"})
    )
    assert recommended["status"] == "ready_with_warnings"

    minimum = evaluate_real_closeout_preflight(
        _checks(failures={"free_disk_minimum": "free_bytes=1000"})
    )
    assert minimum["status"] == "blocked"
    assert any(
        value.startswith("free_disk_minimum:")
        for value in minimum["errors"]
    )


def test_missing_or_extra_check_fails_closed() -> None:
    checks = _checks()
    checks = [item for item in checks if item.name != "chromium_launch"]

    payload = evaluate_real_closeout_preflight(checks)

    assert payload["status"] == "blocked"
    assert any(
        value.startswith("check_set_mismatch:")
        for value in payload["errors"]
    )


def test_preflight_contract_is_read_only_and_never_auto_repairs() -> None:
    contract = RealCloseoutPreflightContract().as_payload()

    assert contract["catalog_opened_read_only"] is True
    assert contract["provider_probe_is_read_only"] is True
    assert contract["browser_probe_is_ephemeral"] is True
    assert contract["auto_git_pull"] is False
    assert contract["auto_git_fetch"] is False
    assert contract["auto_dependency_install"] is False
    assert contract["auto_playwright_install"] is False
    assert contract["mutates_m1_market_data"] is False
    assert contract["mutates_product_state"] is False
    assert contract["writes_m4_evidence"] is False
    assert contract["starts_daily_close"] is False
    assert contract["starts_phase19_delivery"] is False


def test_critical_environment_and_data_checks_are_blockers() -> None:
    blockers = {
        name
        for name, severity in REQUIRED_CHECK_SEVERITY.items()
        if severity == "blocker"
    }
    required = {
        "branch_main",
        "worktree_clean",
        "remote_main_reachable",
        "remote_main_matches_head",
        "phase22_ancestor",
        "python_version_313",
        "python_from_project_venv",
        "python_dependencies",
        "m1_catalog_read_only",
        "m1_required_tables",
        "m1_scope_initialized",
        "m1_dataset_metadata_valid",
        "m1_parquet_files_present",
        "m1_delta_files_valid",
        "m1_calendar_present",
        "provider_liveness",
        "node_available",
        "npm_available",
        "npx_available",
        "npm_dependency_tree",
        "playwright_package",
        "chromium_executable",
        "chromium_launch",
        "report_path_writable",
        "market_delta_path_writable",
        "product_path_writable",
        "free_disk_minimum",
    }

    assert required <= blockers


def test_final_bat_runs_preflight_before_daily_close() -> None:
    root = Path(__file__).resolve().parents[2]
    bat = (
        root / "运行HT-CN主线真实A股最终验收.bat"
    ).read_text(encoding="utf-8")

    preflight = 'scripts\\m5_real_closeout_preflight.py'
    daily = '运行HT-CN每日收盘并生成便携复盘包.bat'

    assert preflight in bat
    assert daily in bat
    assert bat.index(preflight) < bat.index(daily)
    assert "BLOCKED BY PREFLIGHT" in bat
    assert "No daily close / Phase19 was started." in bat


def test_final_bat_and_preflight_never_auto_install_or_update_repository() -> None:
    root = Path(__file__).resolve().parents[2]
    bat = (
        root / "运行HT-CN主线真实A股最终验收.bat"
    ).read_text(encoding="utf-8").lower()
    module = (
        root / "src" / "htcn" / "app" / "real_closeout_preflight.py"
    ).read_text(encoding="utf-8").lower()

    forbidden = (
        "git pull",
        "git fetch",
        "pip install",
        "npm install",
        "npm ci",
        "playwright install",
    )
    for snippet in forbidden:
        assert snippet not in bat
        assert snippet not in module

    assert '"ls-remote"' in module
    assert "read_only=true" in module


def test_phase23_does_not_replace_phase21_structural_or_browser_closeout() -> None:
    root = Path(__file__).resolve().parents[2]
    bat = (
        root / "运行HT-CN主线真实A股最终验收.bat"
    ).read_text(encoding="utf-8")

    assert "scripts\\m5_main_real_closeout.py" in bat
    assert "scripts\\m5_prepare_main_real_browser_audit.py" in bat
    assert "tests/main-real-portable-delivery.spec.ts" in bat
    assert "scripts\\m5_verify_main_real_browser_evidence.py" in bat
    assert "scripts\\m5_finalize_main_real_closeout.py" in bat


def test_warning_severity_is_limited_to_non_authoritative_capacity_diagnostics() -> None:
    warnings = {
        name
        for name, severity in REQUIRED_CHECK_SEVERITY.items()
        if severity == "warning"
    }

    assert warnings == {
        "m1_full_listed_coverage",
        "free_disk_recommended",
    }



def _build_catalog_fixture(
    root: Path,
    *,
    catalog_row_count: int = 2,
    corrupt_delta: bool = False,
) -> None:
    market = root / "data" / "market"
    daily = market / "daily"
    delta = market / "daily_delta"
    daily.mkdir(parents=True)
    delta.mkdir(parents=True)
    catalog_path = market / "catalog.duckdb"

    base_frame = pd.DataFrame(
        {
            "instrument_id": ["SSE.600000", "SSE.600000"],
            "trade_date": ["2026-09-17", "2026-09-18"],
            "open": [10.0, 10.2],
            "high": [10.3, 10.5],
            "low": [9.9, 10.1],
            "close": [10.2, 10.4],
            "volume": [1000.0, 1200.0],
        }
    )
    base_path = daily / "SSE.600000.parquet"
    base_frame.to_parquet(base_path, index=False)

    delta_path = delta / "2026-09-19.parquet"
    if corrupt_delta:
        delta_path.write_bytes(b"not-a-parquet")
    else:
        pd.DataFrame(
            {
                "instrument_id": ["SSE.600000"],
                "trade_date": ["2026-09-19"],
                "open": [10.4],
                "high": [10.6],
                "low": [10.3],
                "close": [10.5],
                "volume": [1300.0],
            }
        ).to_parquet(delta_path, index=False)

    con = duckdb.connect(str(catalog_path))
    try:
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
            CREATE TABLE trade_calendar (
                trade_date DATE PRIMARY KEY,
                source VARCHAR NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            """
        )
        con.execute(
            """
            CREATE TABLE sync_task (
                instrument_id VARCHAR PRIMARY KEY,
                status VARCHAR NOT NULL,
                error_message VARCHAR,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMP NOT NULL
            )
            """
        )
        con.execute(
            """
            INSERT INTO security_master VALUES (
                'SSE.600000', '600000', 'SSE', 'fixture', 'MAIN',
                DATE '1999-11-10', NULL, FALSE, 'listed', 'fixture', CURRENT_TIMESTAMP
            )
            """
        )
        con.execute(
            """
            INSERT INTO daily_dataset VALUES (
                'SSE.600000', 'fixture', ?, ?,
                DATE '2026-09-17', DATE '2026-09-18', CURRENT_TIMESTAMP
            )
            """,
            [str(base_path), catalog_row_count],
        )
        con.execute(
            """
            INSERT INTO trade_calendar VALUES
                (DATE '2026-09-17', 'fixture', CURRENT_TIMESTAMP),
                (DATE '2026-09-18', 'fixture', CURRENT_TIMESTAMP),
                (DATE '2026-09-19', 'fixture', CURRENT_TIMESTAMP)
            """
        )
    finally:
        con.close()


def test_catalog_probe_uses_read_only_metadata_and_validates_real_parquet(
    tmp_path: Path,
) -> None:
    _build_catalog_fixture(tmp_path)

    payload = _catalog_probe(tmp_path)

    assert payload["read_only_open"] is True
    assert payload["error"] is None
    assert payload["listed_scope_count"] == 1
    assert payload["initialized_scope_count"] == 1
    assert payload["invalid_metadata_count"] == 0
    assert payload["inactive_dataset_count"] == 0
    assert payload["invalid_parquet_count"] == 0
    assert payload["row_count_mismatch_count"] == 0
    assert payload["delta_file_count"] == 1
    assert payload["invalid_delta_count"] == 0
    assert payload["calendar_count"] == 3


def test_catalog_probe_detects_base_parquet_row_count_mismatch(
    tmp_path: Path,
) -> None:
    _build_catalog_fixture(tmp_path, catalog_row_count=99)

    payload = _catalog_probe(tmp_path)

    assert payload["invalid_parquet_count"] == 1
    assert payload["row_count_mismatch_count"] == 1
    assert any(
        "row_count_mismatch=2!=99" in value
        for value in payload["invalid_parquet_examples"]
    )


def test_catalog_probe_detects_corrupt_daily_delta(
    tmp_path: Path,
) -> None:
    _build_catalog_fixture(tmp_path, corrupt_delta=True)

    payload = _catalog_probe(tmp_path)

    assert payload["delta_file_count"] == 1
    assert payload["invalid_delta_count"] == 1
    assert payload["invalid_delta_examples"]



def test_catalog_probe_ignores_inactive_historical_dataset_like_daily_pipeline(
    tmp_path: Path,
) -> None:
    _build_catalog_fixture(tmp_path)
    catalog_path = tmp_path / "data" / "market" / "catalog.duckdb"
    con = duckdb.connect(str(catalog_path))
    try:
        con.execute(
            """
            INSERT INTO security_master VALUES (
                'SZSE.000001', '000001', 'SZSE', 'inactive', 'MAIN',
                DATE '1991-04-03', DATE '2026-01-01', FALSE, 'delisted',
                'fixture', CURRENT_TIMESTAMP
            )
            """
        )
        con.execute(
            """
            INSERT INTO daily_dataset VALUES (
                'SZSE.000001', 'fixture', 'missing-inactive.parquet', 999,
                DATE '1991-04-03', DATE '2025-12-31', CURRENT_TIMESTAMP
            )
            """
        )
    finally:
        con.close()

    payload = _catalog_probe(tmp_path)

    assert payload["listed_scope_count"] == 1
    assert payload["initialized_scope_count"] == 1
    assert payload["inactive_dataset_count"] == 1
    assert payload["invalid_metadata_count"] == 0
    assert payload["invalid_parquet_count"] == 0
