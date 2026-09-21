from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

from htcn.research.capture_transaction import read_committed_captures


def _closed_trade_dates(catalog: Path) -> list[str]:
    if not catalog.is_file():
        raise FileNotFoundError(f"missing M1 catalog: {catalog}")
    with duckdb.connect(str(catalog), read_only=True) as con:
        rows = con.execute(
            "SELECT trade_date FROM trade_calendar ORDER BY trade_date"
        ).fetchall()
    dates = [str(row[0]) for row in rows if row and row[0] is not None]
    if not dates:
        raise RuntimeError("M1 trade_calendar has no closed trade dates")
    return dates


def assess_append_need(
    *,
    catalog: Path,
    transaction_root: Path,
) -> dict[str, Any]:
    dates = _closed_trade_dates(catalog)
    committed = read_committed_captures(transaction_root)
    latest_closed = dates[-1]
    latest_capture = (
        None
        if not committed
        else str(committed[-1].get("as_of_trade_date") or "")
    )

    payload: dict[str, Any] = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "status": "ready",
        "action": "capture_due",
        "append_required": True,
        "latest_closed_trade_date": latest_closed,
        "latest_committed_capture_date": latest_capture,
        "committed_capture_count": len(committed),
        "pending_closed_trade_dates": [],
        "pending_closed_trade_count": 0,
        "statistical_inference_allowed": False,
        "alpha_inference_allowed": False,
        "win_rate_inference_allowed": False,
        "profitability_inference_allowed": False,
        "is_trade_instruction": False,
    }

    if latest_capture is None:
        payload["pending_closed_trade_dates"] = [latest_closed]
        payload["pending_closed_trade_count"] = 1
        payload["reason"] = "no_committed_capture_yet"
        return payload

    if latest_capture not in dates:
        payload.update({
            "status": "blocked",
            "action": "blocked",
            "append_required": False,
            "reason": "latest_committed_capture_not_in_local_trade_calendar",
        })
        return payload

    if latest_capture > latest_closed:
        payload.update({
            "status": "blocked",
            "action": "blocked",
            "append_required": False,
            "reason": "committed_capture_is_ahead_of_local_market_clock",
        })
        return payload

    pending = [value for value in dates if value > latest_capture]
    payload["pending_closed_trade_dates"] = pending
    payload["pending_closed_trade_count"] = len(pending)

    if not pending:
        payload.update({
            "action": "idempotent_noop",
            "append_required": False,
            "reason": "latest_closed_session_already_committed",
        })
        return payload

    if len(pending) == 1 and pending[0] == latest_closed:
        payload["reason"] = "exactly_one_new_closed_session"
        return payload

    payload.update({
        "status": "blocked",
        "action": "blocked",
        "append_required": False,
        "reason": "missed_closed_sessions_no_backfill_allowed",
    })
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Decide whether M7 needs a new authoritative append after M1 update."
        )
    )
    parser.add_argument(
        "--catalog",
        default="data/market/catalog.duckdb",
    )
    parser.add_argument(
        "--transaction-root",
        default="data/research/m4/captures",
    )
    parser.add_argument(
        "--output",
        default="artifacts/reports/m7-append-precheck.json",
    )
    parser.add_argument(
        "--action-output",
        default="artifacts/reports/m7-append-action.txt",
    )
    args = parser.parse_args()

    try:
        payload = assess_append_need(
            catalog=Path(args.catalog),
            transaction_root=Path(args.transaction_root),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        payload = {
            "schema_version": 1,
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "status": "blocked",
            "action": "blocked",
            "append_required": False,
            "errors": [f"{type(exc).__name__}: {exc}"],
            "statistical_inference_allowed": False,
            "alpha_inference_allowed": False,
            "win_rate_inference_allowed": False,
            "profitability_inference_allowed": False,
            "is_trade_instruction": False,
        }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    action_output = Path(args.action_output)
    action_output.parent.mkdir(parents=True, exist_ok=True)
    action_output.write_text(
        str(payload.get("action") or "blocked") + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if payload.get("status") == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
