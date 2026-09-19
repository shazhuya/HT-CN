from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from htcn.data.adjusted_fetch import fetch_adjusted_history
from htcn.data.adjustment import AdjustmentFactorStore, apply_price_factors, derive_price_factors
from htcn.data.catalog import DataCatalog
from htcn.data.providers import AkShareProvider, BaoStockProvider
from htcn.data.store import ParquetDailyStore
from htcn.data.validation import normalize_daily

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "market"
CATALOG_PATH = DATA_ROOT / "catalog.duckdb"
DAILY_ROOT = DATA_ROOT / "daily"
FACTOR_ROOT = DATA_ROOT / "adjustment" / "qfq"
OUT_DIR = ROOT / "artifacts" / "calibration"
OUT_PATH = OUT_DIR / "m2-qfq-expansion.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Expand QFQ factors across initialized SSE/SZSE datasets")
    parser.add_argument("--limit", type=int, default=0, help="0 means all initialized SSE/SZSE datasets")
    parser.add_argument("--force", action="store_true", help="refetch even when the local factor file is current")
    parser.add_argument("--retries", type=int, default=1)
    return parser.parse_args()


def _factor_is_current(raw: pd.DataFrame, factors: pd.DataFrame) -> bool:
    if raw.empty or factors.empty:
        return False
    raw_dates = pd.to_datetime(raw["trade_date"]).dt.normalize()
    factor_dates = pd.to_datetime(factors["trade_date"]).dt.normalize()
    overlap = len(set(raw_dates).intersection(set(factor_dates))) / max(1, len(set(raw_dates)))
    return bool(
        overlap >= 0.95
        and factor_dates.min() <= raw_dates.min()
        and factor_dates.max() >= raw_dates.max()
    )


def main() -> int:
    args = parse_args()
    if not CATALOG_PATH.exists():
        print("[HT-CN M2 QFQ] FAIL: local market catalog not found.")
        return 1

    catalog = DataCatalog(CATALOG_PATH)
    raw_store = ParquetDailyStore(DAILY_ROOT)
    factor_store = AdjustmentFactorStore(FACTOR_ROOT)
    datasets = [
        str(row["instrument_id"])
        for row in catalog.list_daily_datasets()
        if str(row["instrument_id"]).startswith(("SSE.", "SZSE."))
    ]
    if args.limit > 0:
        datasets = datasets[: args.limit]
    if not datasets:
        print("[HT-CN M2 QFQ] FAIL: no initialized SSE/SZSE raw datasets.")
        return 1

    existing = 0
    built = 0
    failed: list[dict[str, str]] = []
    print(f"[HT-CN M2 QFQ] Resumable expansion: initialized={len(datasets)}, force={args.force}")

    for position, instrument_id in enumerate(datasets, start=1):
        raw = raw_store.read(instrument_id)
        if raw.empty:
            failed.append({"instrument_id": instrument_id, "error": "raw parquet empty"})
            print(f"[HT-CN M2 QFQ] {position}/{len(datasets)} FAIL {instrument_id}: raw empty")
            continue

        current = factor_store.read(instrument_id)
        if not args.force and _factor_is_current(raw, current):
            existing += 1
            print(f"[HT-CN M2 QFQ] {position}/{len(datasets)} CURRENT {instrument_id}: factors={len(current)}")
            continue

        start = pd.Timestamp(raw["trade_date"].min()).date()
        end = pd.Timestamp(raw["trade_date"].max()).date()
        try:
            fetched = fetch_adjusted_history(
                instrument_id=instrument_id,
                start=start,
                end=end,
                providers=[AkShareProvider(), BaoStockProvider()],
                mode="qfq",
                retries_per_provider=max(0, int(args.retries)),
                base_delay=0.75,
            )
            adjusted = normalize_daily(fetched.frame)
            factors = derive_price_factors(raw, adjusted, mode="qfq", source=fetched.source)
            overlap = len(factors) / max(1, len(raw))
            if overlap < 0.95:
                raise RuntimeError(f"factor overlap too low: {overlap:.2%}")
            factor_store.write(factors)

            reconstructed = apply_price_factors(
                raw.loc[raw["trade_date"].isin(factors["trade_date"])], factors
            ).sort_values("trade_date").reset_index(drop=True)
            expected = adjusted.loc[
                adjusted["trade_date"].isin(reconstructed["trade_date"])
            ].sort_values("trade_date").reset_index(drop=True)
            if len(reconstructed) != len(expected):
                raise RuntimeError("reconstruction row mismatch")
            max_close_error = float((reconstructed["close"] - expected["close"]).abs().max())
            if max_close_error > 1e-6:
                raise RuntimeError(f"reconstruction mismatch: {max_close_error:.10f}")
            built += 1
            print(
                f"[HT-CN M2 QFQ] {position}/{len(datasets)} OK {instrument_id}: "
                f"source={fetched.source}, factors={len(factors)}, overlap={overlap:.2%}"
            )
        except Exception as exc:
            failed.append({"instrument_id": instrument_id, "error": f"{type(exc).__name__}: {exc}"})
            print(f"[HT-CN M2 QFQ] {position}/{len(datasets)} WARN {instrument_id}: {type(exc).__name__}: {exc}")

    usable = sum(1 for instrument_id in datasets if not factor_store.read(instrument_id).empty)
    payload = {
        "schema_version": 1,
        "status": "research_qfq_universe_expansion",
        "initialized_raw": len(datasets),
        "already_current": existing,
        "built_or_refreshed": built,
        "usable_qfq": usable,
        "failed": failed,
        "policy": "Resumable one-time research expansion. Raw OHLCV remains durable truth; QFQ remains a separate factor layer.",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"[HT-CN M2 QFQ] DONE initialized={len(datasets)}, current={existing}, "
        f"built={built}, usable_qfq={usable}, failed={len(failed)}"
    )
    print(f"[HT-CN M2 QFQ] Report: {OUT_PATH.relative_to(ROOT)}")
    if usable < 3:
        print("[HT-CN M2 QFQ] FAIL: fewer than 3 usable QFQ datasets remain.")
        return 2
    print("[HT-CN M2 QFQ] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
