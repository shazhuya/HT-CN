from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from htcn.app.a_share_execution_context import (
    build_a_share_execution_context,
    load_daily_trading_metadata,
    load_security_metadata,
)


def _table_exists(con: duckdb.DuckDBPyConnection, name: str) -> bool:
    row = con.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [name],
    ).fetchone()
    return bool(row and int(row[0]) > 0)


def _resolve_parquet(catalog: Path, raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    candidates = [Path.cwd() / path, catalog.parent / path, catalog.parent.parent / path]
    return next((item for item in candidates if item.exists()), candidates[0])


def _sample_rows(con: duckdb.DuckDBPyConnection) -> list[tuple[str, str, str | None]]:
    rows: list[tuple[str, str, str | None]] = []
    for board in ("MAIN", "STAR", "CHINEXT"):
        row = con.execute(
            """
            SELECT s.instrument_id, s.board, d.parquet_path
            FROM security_master AS s
            LEFT JOIN daily_dataset AS d ON d.instrument_id = s.instrument_id
            WHERE s.status = 'listed' AND s.board = ?
            ORDER BY CASE WHEN d.parquet_path IS NULL THEN 1 ELSE 0 END, s.instrument_id
            LIMIT 1
            """,
            [board],
        ).fetchone()
        if row is not None:
            rows.append((str(row[0]), str(row[1]), None if row[2] is None else str(row[2])))
    return rows


def run(catalog: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": 1,
        "catalog": str(catalog),
        "status": "failed",
        "security_master": {},
        "daily_event_table": {},
        "daily_event_sync": {},
        "samples": [],
    }
    if not catalog.exists():
        result["error"] = "catalog_not_found"
        return result

    with duckdb.connect(str(catalog), read_only=True) as con:
        if not _table_exists(con, "security_master"):
            result["error"] = "security_master_missing"
            return result
        security_count = int(con.execute("SELECT COUNT(*) FROM security_master").fetchone()[0])
        board_counts = {
            str(board): int(count)
            for board, count in con.execute(
                "SELECT board, COUNT(*) FROM security_master GROUP BY board ORDER BY board"
            ).fetchall()
        }
        result["security_master"] = {
            "count": security_count,
            "board_counts": board_counts,
        }

        event_exists = _table_exists(con, "security_daily_event")
        event_count = (
            int(con.execute("SELECT COUNT(*) FROM security_daily_event").fetchone()[0])
            if event_exists
            else 0
        )
        result["daily_event_table"] = {
            "exists": event_exists,
            "count": event_count,
        }
        sync_exists = _table_exists(con, "security_daily_event_sync")
        latest_sync = None
        if sync_exists:
            latest_sync = con.execute(
                """
                SELECT trade_date, source, status, record_count, coverage_scope, error_message
                FROM security_daily_event_sync
                ORDER BY trade_date DESC, updated_at DESC
                LIMIT 1
                """
            ).fetchone()
        result["daily_event_sync"] = {
            "exists": sync_exists,
            "latest": (
                None
                if latest_sync is None
                else {
                    "trade_date": str(latest_sync[0]),
                    "source": str(latest_sync[1]),
                    "status": str(latest_sync[2]),
                    "record_count": int(latest_sync[3]),
                    "coverage_scope": str(latest_sync[4]),
                    "error_message": latest_sync[5],
                }
            ),
        }
        if event_exists:
            confirmed_suspended = int(
                con.execute(
                    """
                    SELECT COUNT(*) FROM security_daily_event
                    WHERE trading_status IN ('suspended', 'intraday_suspended')
                    """
                ).fetchone()[0]
            )
        else:
            confirmed_suspended = 0
        samples = _sample_rows(con)

    sample_payloads: list[dict[str, Any]] = []
    for instrument_id, board, parquet_raw in samples:
        metadata = load_security_metadata(catalog, instrument_id)
        payload: dict[str, Any] = {
            "instrument_id": instrument_id,
            "board_expected": board,
            "metadata_loaded": metadata is not None,
            "metadata_board": None if metadata is None else metadata.board.value,
            "list_date": None if metadata is None or metadata.list_date is None else metadata.list_date.isoformat(),
            "is_st": None if metadata is None else metadata.is_st,
            "metadata_source": None if metadata is None else metadata.source,
            "parquet_path": parquet_raw,
            "parquet_loaded": False,
            "execution_context": None,
        }
        if parquet_raw:
            parquet = _resolve_parquet(catalog, parquet_raw)
            payload["resolved_parquet_path"] = str(parquet)
            if parquet.exists():
                frame = pd.read_parquet(parquet).tail(80).reset_index(drop=True)
                if not frame.empty:
                    as_of = None
                    if "trade_date" in frame.columns:
                        stamp = pd.to_datetime(frame["trade_date"].iloc[-1], errors="coerce")
                        if not pd.isna(stamp):
                            as_of = stamp.date()
                    event = load_daily_trading_metadata(catalog, instrument_id, as_of)
                    context = build_a_share_execution_context(
                        frame,
                        instrument_id=instrument_id,
                        metadata=metadata,
                        daily_event=event,
                    )
                    payload["parquet_loaded"] = True
                    payload["execution_context"] = {
                        "as_of_trade_date": context.as_of_trade_date,
                        "board": context.board,
                        "metadata_available": context.metadata_available,
                        "daily_event_available": context.daily_event_available,
                        "daily_trading_status": context.daily_trading_status,
                        "tradable_on_as_of_date": context.tradable_on_as_of_date,
                        "price_limit_status": context.price_limit_status,
                        "rule_based_price_limit_pct": context.rule_based_price_limit_pct,
                        "special_event_exceptions_unresolved": context.special_event_exceptions_unresolved,
                        "atr_pct": context.atr_pct,
                        "volume_ratio_20": context.volume_ratio_20,
                    }
        sample_payloads.append(payload)

    result["samples"] = sample_payloads
    core_ok = bool(result["security_master"].get("count", 0)) and all(
        item["metadata_loaded"] and item["metadata_board"] == item["board_expected"]
        for item in sample_payloads
    )
    parquet_checks = [item for item in sample_payloads if item.get("parquet_path")]
    parquet_ok = all(item["parquet_loaded"] for item in parquet_checks) if parquet_checks else False
    result["status"] = (
        "pass"
        if core_ok and parquet_ok
        else "security_master_pass_parquet_unavailable"
        if core_ok
        else "failed"
    )
    latest_sync_payload = result["daily_event_sync"].get("latest")
    if latest_sync_payload is None or latest_sync_payload.get("status") != "success":
        result["event_feed_status"] = "event_unknown"
    elif latest_sync_payload.get("coverage_scope") == "complete_market":
        result["event_feed_status"] = "event_complete"
    else:
        result["event_feed_status"] = "event_partial"
    result["confirmed_suspended_count"] = confirmed_suspended
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="HT-CN M3 Phase 3.1 metadata/tradability smoke test")
    parser.add_argument("--catalog", default="data/market/catalog.duckdb")
    parser.add_argument("--output", default="artifacts/reports/m3-metadata-tradability-smoke.json")
    parser.add_argument(
        "--require-parquet",
        action="store_true",
        help="fail unless representative MAIN/STAR/CHINEXT parquet histories are readable",
    )
    args = parser.parse_args()

    result = run(Path(args.catalog))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n[M3] report: {output}")
    accepted = {"pass"} if args.require_parquet else {
        "pass",
        "security_master_pass_parquet_unavailable",
    }
    if args.require_parquet:
        result["acceptance_mode"] = "strict_real_m1_parquet_required"
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if result["status"] in accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
