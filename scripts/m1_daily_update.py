from __future__ import annotations

import argparse
import random
import time
from datetime import date, datetime, time as clock_time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from htcn.data.catalog import DataCatalog
from htcn.data.providers import AkShareProvider, AkShareSinaProvider, BaoStockProvider, FailoverProvider
from htcn.data.store import ParquetDailyStore
from htcn.data.sync import sync_daily
from htcn.data.universe import SUPPORTED_INITIAL_DAILY_PREFIXES


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "market"
CATALOG_PATH = DATA_ROOT / "catalog.duckdb"
DAILY_ROOT = DATA_ROOT / "daily"
START_DATE = date(1990, 1, 1)
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
POST_CLOSE_CUTOFF = clock_time(16, 30)


def build_provider() -> FailoverProvider:
    return FailoverProvider(
        AkShareProvider(),
        FailoverProvider(AkShareSinaProvider(), BaoStockProvider()),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HT-CN fast SSE/SZSE daily incremental updater")
    parser.add_argument("--limit", type=int, default=0, help="0 means all initialized SSE/SZSE datasets")
    parser.add_argument("--sleep", type=float, default=0.05, help="sleep only between slow-path fallbacks")
    return parser.parse_args()


def latest_closed_trade_dates(
    provider: FailoverProvider,
    *,
    now: datetime | None = None,
) -> tuple[date, date | None, bool]:
    """Return latest closed day, prior trade day, and whether today's bulk snapshot is safe."""
    sh_now = now.astimezone(SHANGHAI_TZ) if now is not None else datetime.now(SHANGHAI_TZ)
    after_cutoff = sh_now.timetz().replace(tzinfo=None) >= POST_CLOSE_CUTOFF
    candidate = sh_now.date() if after_cutoff else sh_now.date() - timedelta(days=1)
    days = sorted(set(provider.get_trade_calendar(candidate - timedelta(days=30), candidate)))
    if not days:
        raise RuntimeError(f"no trading day found before {candidate}")
    target = days[-1]
    previous = days[-2] if len(days) >= 2 else None
    return target, previous, after_cutoff and target == sh_now.date()


def _normalize_last_date(value: object) -> date | None:
    if value is None:
        return None
    return pd.Timestamp(value).date()


def _apply_snapshot_row(
    *,
    store: ParquetDailyStore,
    catalog: DataCatalog,
    instrument_id: str,
    row: pd.DataFrame,
) -> None:
    merged = store.upsert(row)
    if merged.empty:
        raise RuntimeError("snapshot row produced empty local dataset")
    first_date = pd.Timestamp(merged["trade_date"].min()).date().isoformat()
    last_date = pd.Timestamp(merged["trade_date"].max()).date().isoformat()
    source_values = row["source"].dropna() if "source" in row.columns else pd.Series(dtype=str)
    source = str(source_values.iloc[-1]) if not source_values.empty else "akshare_spot"
    catalog.record_daily(
        instrument_id=instrument_id,
        source=source,
        parquet_path=str(store.path_for(instrument_id)),
        row_count=len(merged),
        first_trade_date=first_date,
        last_trade_date=last_date,
    )


def main() -> int:
    args = parse_args()
    print("[HT-CN M1 DAILY] Starting smart incremental update...", flush=True)
    if not CATALOG_PATH.exists():
        print("[HT-CN M1 DAILY] Database not found. Run initializer first.", flush=True)
        return 1

    catalog = DataCatalog(CATALOG_PATH)
    store = ParquetDailyStore(DAILY_ROOT)
    provider = build_provider()

    target, previous_trade_day, allow_snapshot = latest_closed_trade_dates(provider)
    print(
        f"[HT-CN M1 DAILY] Latest closed A-share day: {target}; "
        f"bulk_snapshot={'YES' if allow_snapshot else 'NO'}",
        flush=True,
    )

    listed_ids = set(catalog.list_security_ids(listed_only=True))
    datasets = [
        row
        for row in catalog.list_daily_datasets()
        if str(row["instrument_id"]) in listed_ids
        and str(row["instrument_id"]).startswith(SUPPORTED_INITIAL_DAILY_PREFIXES)
    ]
    datasets.sort(key=lambda item: str(item["instrument_id"]))
    if args.limit > 0:
        datasets = datasets[: args.limit]

    current: list[dict[str, object]] = []
    stale: list[dict[str, object]] = []
    for item in datasets:
        last_date = _normalize_last_date(item.get("last_trade_date"))
        if last_date is not None and last_date >= target:
            current.append(item)
        else:
            stale.append(item)

    print(
        f"[HT-CN M1 DAILY] Initialized={len(datasets)}, already_current={len(current)}, "
        f"need_update={len(stale)}",
        flush=True,
    )
    if not stale:
        print(
            "[HT-CN M1 DAILY] FAST PASS: all local datasets already cover the latest "
            "closed trading day; zero per-symbol network requests.",
            flush=True,
        )
        return 0

    updated = 0
    failed = 0
    snapshot_updated: set[str] = set()

    if allow_snapshot and previous_trade_day is not None:
        try:
            print(
                f"[HT-CN M1 DAILY] Fetching one all-market snapshot for {target}...",
                flush=True,
            )
            snapshot = AkShareProvider().get_market_daily_snapshot(target)
            snapshot_map = {
                instrument_id: group.reset_index(drop=True)
                for instrument_id, group in snapshot.groupby("instrument_id", sort=False)
            }
            eligible = [
                item
                for item in stale
                if _normalize_last_date(item.get("last_trade_date")) == previous_trade_day
                and str(item["instrument_id"]) in snapshot_map
            ]
            print(
                f"[HT-CN M1 DAILY] Snapshot rows={len(snapshot)}, directly_applicable={len(eligible)}",
                flush=True,
            )
            for index, item in enumerate(eligible, start=1):
                instrument_id = str(item["instrument_id"])
                try:
                    _apply_snapshot_row(
                        store=store,
                        catalog=catalog,
                        instrument_id=instrument_id,
                        row=snapshot_map[instrument_id],
                    )
                    snapshot_updated.add(instrument_id)
                    updated += 1
                    if index <= 5 or index % 250 == 0 or index == len(eligible):
                        print(
                            f"[HT-CN M1 DAILY] BULK {index}/{len(eligible)} {instrument_id}",
                            flush=True,
                        )
                except Exception as exc:
                    print(
                        f"[HT-CN M1 DAILY] BULK-ROW fallback {instrument_id}: "
                        f"{type(exc).__name__}: {exc}",
                        flush=True,
                    )
        except Exception as exc:
            print(
                f"[HT-CN M1 DAILY] Bulk snapshot unavailable; using repair path: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )

    repair = [item for item in stale if str(item["instrument_id"]) not in snapshot_updated]
    print(
        f"[HT-CN M1 DAILY] Slow-path historical repairs required: {len(repair)}",
        flush=True,
    )

    for index, item in enumerate(repair, start=1):
        instrument_id = str(item["instrument_id"])
        before_last = _normalize_last_date(item.get("last_trade_date"))
        try:
            result = sync_daily(
                provider=provider,
                store=store,
                catalog=catalog,
                instrument_id=instrument_id,
                start=START_DATE,
                end=target,
            )
            after = catalog.get_daily(instrument_id) or {}
            after_last = _normalize_last_date(after.get("last_trade_date"))
            if after_last is not None and after_last >= target and after_last != before_last:
                updated += 1
                state = "UPDATED"
            elif after_last is not None and after_last >= target:
                state = "CURRENT"
            else:
                raise RuntimeError(f"provider did not reach target trade date {target}; last={after_last}")
            print(
                f"[HT-CN M1 DAILY] REPAIR [{index}/{len(repair)}] {state} {instrument_id}: "
                f"rows={len(result)}, last={after_last}, source={after.get('source')}",
                flush=True,
            )
        except KeyboardInterrupt:
            print("\n[HT-CN M1 DAILY] Interrupted. Existing data remains safe.", flush=True)
            return 130
        except Exception as exc:
            failed += 1
            print(
                f"[HT-CN M1 DAILY] REPAIR [{index}/{len(repair)}] FAILED {instrument_id}: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )

        if args.sleep > 0:
            time.sleep(args.sleep + random.uniform(0.0, min(0.05, args.sleep)))

    print(
        f"[HT-CN M1 DAILY] DONE updated={updated}, preexisting_current={len(current)}, "
        f"bulk={len(snapshot_updated)}, repair={len(repair)}, failed={failed}",
        flush=True,
    )
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
