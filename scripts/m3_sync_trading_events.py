from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from datetime import time as clock_time
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb

from htcn.data.providers import AkShareProvider
from htcn.data.trading_events import sync_daily_trading_events

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
POST_CLOSE_CUTOFF = clock_time(16, 30)


def _target_date(provider: AkShareProvider, requested: str | None) -> date:
    if requested:
        return date.fromisoformat(requested)
    now = datetime.now(SHANGHAI_TZ)
    candidate = (
        now.date()
        if now.timetz().replace(tzinfo=None) >= POST_CLOSE_CUTOFF
        else now.date() - timedelta(days=1)
    )
    calendar = sorted(set(provider.get_trade_calendar(candidate - timedelta(days=20), candidate)))
    if not calendar:
        raise RuntimeError(f"no A-share trading day found before {candidate}")
    return calendar[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description="HT-CN M3 confirmed daily trading-event sync")
    parser.add_argument("--catalog", default="data/market/catalog.duckdb")
    parser.add_argument(
        "--date",
        default=None,
        help="YYYY-MM-DD; default is latest closed A-share session",
    )
    parser.add_argument("--output", default="artifacts/reports/m3-trading-event-sync.json")
    args = parser.parse_args()

    catalog = Path(args.catalog)
    if not catalog.exists():
        raise SystemExit(f"catalog not found: {catalog}")

    provider = AkShareProvider()
    target = _target_date(provider, args.date)
    stored = sync_daily_trading_events(
        catalog_path=catalog,
        provider=provider,
        trade_date=target,
    )

    with duckdb.connect(str(catalog), read_only=True) as con:
        audit = con.execute(
            """
            SELECT status, record_count, coverage_scope, error_message, updated_at
            FROM security_daily_event_sync
            WHERE trade_date = ? AND source = ?
            """,
            [target, provider.event_source],
        ).fetchone()
        rows = con.execute(
            """
            SELECT instrument_id, trading_status, reason
            FROM security_daily_event
            WHERE trade_date = ? AND source = ?
            ORDER BY instrument_id
            """,
            [target, provider.event_source],
        ).fetchall()

    payload = {
        "schema_version": 1,
        "trade_date": target.isoformat(),
        "source": provider.event_source,
        "stored_positive_events": stored,
        "coverage_scope": None if audit is None else audit[2],
        "sync_status": None if audit is None else audit[0],
        "events": [
            {"instrument_id": row[0], "trading_status": row[1], "reason": row[2]}
            for row in rows
        ],
        "semantic_note": (
            "positive_evidence_only: confirmed suspension rows are useful evidence, but an "
            "empty result does not certify that every security had no other special event."
        ),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    print(f"\n[M3] report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
