from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb
import pandas as pd

from htcn.data.benchmarks import CORE_BENCHMARKS, CoreBenchmarkStore
from htcn.data.concepts import (
    build_concept_snapshots_from_local_market,
    concept_sync_is_fresh,
    sync_concept_memberships,
)
from htcn.data.providers import AkShareProvider
from htcn.data.sectors import (
    build_industry_snapshot_from_local_market,
    membership_sync_is_fresh,
    sync_industry_memberships,
)
from htcn.data.trading_events import sync_daily_trading_events


SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
BENCHMARK_START = date(2024, 1, 1)


def _latest_local_trade_date(catalog: Path) -> date:
    with duckdb.connect(str(catalog), read_only=True) as con:
        row = con.execute("SELECT MAX(trade_date) FROM trade_calendar").fetchone()
    if row is None or row[0] is None:
        raise RuntimeError("trade_calendar has no local trade date")
    return pd.Timestamp(row[0]).date()


def _error(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


def _sync_benchmarks(
    provider: AkShareProvider,
    *,
    root: Path,
    target: date,
) -> dict[str, object]:
    store = CoreBenchmarkStore(root)
    items: list[dict[str, object]] = []
    for spec in CORE_BENCHMARKS:
        try:
            existing = store.read(spec.key)
            fetch_start = BENCHMARK_START
            if not existing.empty:
                latest = pd.Timestamp(existing["trade_date"].max()).date()
                fetch_start = max(BENCHMARK_START, latest + timedelta(days=1))
            if fetch_start <= target:
                incoming = provider.get_index_daily(spec.symbol, fetch_start, target)
                merged = store.upsert(spec.key, incoming) if not incoming.empty else existing
            else:
                merged = existing
            last = (
                None
                if merged.empty
                else pd.Timestamp(merged["trade_date"].max()).date()
            )
            state = "current" if last == target else "stale_or_empty"
            items.append({
                "key": spec.key,
                "symbol": spec.symbol,
                "name_zh": spec.name_zh,
                "state": state,
                "last_trade_date": None if last is None else last.isoformat(),
                "rows": len(merged),
            })
        except Exception as exc:
            items.append({
                "key": spec.key,
                "symbol": spec.symbol,
                "name_zh": spec.name_zh,
                "state": "failed",
                "error": _error(exc),
            })
    return {
        "state": (
            "current"
            if items and all(item["state"] == "current" for item in items)
            else "partial"
        ),
        "items": items,
    }


def _sync_industry(
    provider: AkShareProvider,
    *,
    catalog: Path,
    data_root: Path,
    target: date,
    today: date,
    refresh_days: int,
) -> dict[str, object]:
    result: dict[str, object] = {}
    refresh = not membership_sync_is_fresh(
        catalog, as_of=today, max_age_days=refresh_days
    )
    result["membership_refresh_needed"] = refresh
    membership_degraded = False
    if refresh:
        try:
            result["membership"] = sync_industry_memberships(
                catalog_path=catalog, provider=provider, observed_on=today
            )
        except Exception as exc:
            membership_degraded = True
            result["membership"] = {
                "status": "refresh_failed_previous_snapshot_preserved",
                "error": _error(exc),
            }
    else:
        result["membership"] = {"status": "fresh_cached_snapshot"}

    try:
        snapshots = build_industry_snapshot_from_local_market(
            catalog_path=catalog, data_root=data_root, target_date=target
        )
        result["snapshot_count"] = len(snapshots)
        result["snapshot_trade_date"] = target.isoformat()
        result["state"] = "degraded" if membership_degraded else "current"
    except Exception as exc:
        result["state"] = "failed"
        result["snapshot_error"] = _error(exc)
    return result


def _sync_concepts(
    provider: AkShareProvider,
    *,
    catalog: Path,
    data_root: Path,
    target: date,
    today: date,
    refresh_days: int,
    workers: int,
) -> dict[str, object]:
    result: dict[str, object] = {}
    refresh = not concept_sync_is_fresh(
        catalog, as_of=today, max_age_days=refresh_days
    )
    result["membership_refresh_needed"] = refresh
    membership_degraded = False
    if refresh:
        try:
            result["membership"] = sync_concept_memberships(
                catalog_path=catalog,
                provider=provider,
                observed_on=today,
                workers=workers,
            )
        except Exception as exc:
            membership_degraded = True
            result["membership"] = {
                "status": "refresh_failed_previous_snapshot_preserved",
                "error": _error(exc),
            }
    else:
        result["membership"] = {"status": "fresh_cached_snapshot"}

    try:
        snapshots = build_concept_snapshots_from_local_market(
            catalog_path=catalog, data_root=data_root, target_date=target
        )
        result["snapshot_count"] = len(snapshots)
        result["snapshot_trade_date"] = target.isoformat()
        result["state"] = "degraded" if membership_degraded else "current"
    except Exception as exc:
        result["state"] = "failed"
        result["snapshot_error"] = _error(exc)
    return result


def _catalog_audit(catalog: Path, target: date) -> dict[str, object]:
    with duckdb.connect(str(catalog), read_only=True) as con:
        tables = {
            str(row[0])
            for row in con.execute(
                "SELECT table_name FROM information_schema.tables"
            ).fetchall()
        }
        payload: dict[str, object] = {"tables": sorted(tables)}
        if "security_daily_event_sync" in tables:
            payload["daily_event_sync"] = [
                {
                    "trade_date": str(row[0]),
                    "source": str(row[1]),
                    "status": str(row[2]),
                    "record_count": int(row[3]),
                    "coverage_scope": str(row[4]),
                }
                for row in con.execute(
                    """
                    SELECT trade_date, source, status, record_count, coverage_scope
                    FROM security_daily_event_sync
                    WHERE trade_date = ?
                    ORDER BY source
                    """,
                    [target],
                ).fetchall()
            ]
        if "sector_membership_sync" in tables:
            payload["membership_sync"] = [
                {
                    "sector_kind": str(row[0]),
                    "source": str(row[1]),
                    "observed_on": str(row[2]),
                    "status": str(row[3]),
                    "sector_count": int(row[4]),
                    "membership_count": int(row[5]),
                }
                for row in con.execute(
                    """
                    SELECT sector_kind, source, observed_on, status,
                           sector_count, membership_count
                    FROM sector_membership_sync
                    ORDER BY sector_kind
                    """
                ).fetchall()
            ]
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HT-CN M3 one-click context data synchronization"
    )
    parser.add_argument("--catalog", default="data/market/catalog.duckdb")
    parser.add_argument("--data-root", default="data/market")
    parser.add_argument("--membership-refresh-days", type=int, default=7)
    parser.add_argument("--concept-workers", type=int, default=8)
    parser.add_argument(
        "--output",
        default="artifacts/reports/m3-context-sync-summary.json",
    )
    args = parser.parse_args()

    catalog = Path(args.catalog)
    data_root = Path(args.data_root)
    if not catalog.exists():
        raise SystemExit(f"catalog not found: {catalog}")

    target = _latest_local_trade_date(catalog)
    today = datetime.now(SHANGHAI_TZ).date()
    provider = AkShareProvider()
    layers: dict[str, object] = {}

    try:
        count = sync_daily_trading_events(
            catalog_path=catalog, provider=provider, trade_date=target
        )
        layers["execution_event"] = {
            "state": "partial_positive_evidence",
            "confirmed_event_count": count,
            "coverage_scope": "positive_evidence_only",
        }
    except Exception as exc:
        layers["execution_event"] = {"state": "failed", "error": _error(exc)}

    layers["market"] = _sync_benchmarks(
        provider, root=data_root / "benchmarks", target=target
    )
    layers["industry"] = _sync_industry(
        provider,
        catalog=catalog,
        data_root=data_root,
        target=target,
        today=today,
        refresh_days=max(args.membership_refresh_days, 0),
    )
    layers["concept"] = _sync_concepts(
        provider,
        catalog=catalog,
        data_root=data_root,
        target=target,
        today=today,
        refresh_days=max(args.membership_refresh_days, 0),
        workers=max(1, min(args.concept_workers, 16)),
    )

    states = {
        str(value.get("state"))
        for value in layers.values()
        if isinstance(value, dict)
    }
    overall = (
        "complete"
        if states.issubset({"current", "partial_positive_evidence"})
        else "degraded"
        if "failed" not in states
        else "partial_failure"
    )
    payload = {
        "schema_version": 1,
        "target_trade_date": target.isoformat(),
        "run_date_shanghai": today.isoformat(),
        "overall": overall,
        "is_score": False,
        "layers": layers,
        "catalog_audit": _catalog_audit(catalog, target),
        "semantic_note": (
            "overall only describes whether synchronization steps completed; it is not an investment score or evidence-completeness score. "
            "Event coverage remains positive-evidence-only until a complete source exists."
        ),
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    print(f"\n[M3] combined context report: {output}")
    return 0 if overall == "all_steps_completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
