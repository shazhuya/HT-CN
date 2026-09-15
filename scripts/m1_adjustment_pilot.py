from __future__ import annotations

from pathlib import Path

import pandas as pd

from htcn.data.adjustment import AdjustmentFactorStore, apply_price_factors, derive_price_factors
from htcn.data.catalog import DataCatalog
from htcn.data.providers import AkShareProvider
from htcn.data.store import ParquetDailyStore


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "market"
CATALOG_PATH = DATA_ROOT / "catalog.duckdb"
DAILY_ROOT = DATA_ROOT / "daily"
FACTOR_ROOT = DATA_ROOT / "adjustment" / "qfq"
PILOT = ["SSE.688256", "SZSE.300820", "SSE.600519"]


def main() -> int:
    print("[HT-CN M1 ADJ] Starting QFQ adjustment-factor pilot...", flush=True)
    if not CATALOG_PATH.exists():
        print("[HT-CN M1 ADJ] Database not found.", flush=True)
        return 1

    catalog = DataCatalog(CATALOG_PATH)
    raw_store = ParquetDailyStore(DAILY_ROOT)
    factor_store = AdjustmentFactorStore(FACTOR_ROOT)
    provider = AkShareProvider()

    passed = 0
    for instrument_id in PILOT:
        metadata = catalog.get_daily(instrument_id)
        if metadata is None:
            print(f"[HT-CN M1 ADJ] SKIP {instrument_id}: raw history not initialized", flush=True)
            continue

        raw = raw_store.read(instrument_id)
        if raw.empty:
            print(f"[HT-CN M1 ADJ] FAIL {instrument_id}: raw parquet empty", flush=True)
            return 2

        start = pd.Timestamp(raw["trade_date"].min()).date()
        end = pd.Timestamp(raw["trade_date"].max()).date()
        print(
            f"[HT-CN M1 ADJ] Fetching qfq {instrument_id}: {start} -> {end}",
            flush=True,
        )
        adjusted = provider.get_daily_adjusted(instrument_id, start, end, mode="qfq")
        factors = derive_price_factors(raw, adjusted, mode="qfq", source="akshare_qfq")
        overlap_ratio = len(factors) / len(raw) if len(raw) else 0.0
        if overlap_ratio < 0.95:
            print(
                f"[HT-CN M1 ADJ] FAIL {instrument_id}: overlap={overlap_ratio:.2%}",
                flush=True,
            )
            return 2

        factor_store.write(factors)
        reconstructed = apply_price_factors(raw.loc[raw["trade_date"].isin(factors["trade_date"])], factors)
        expected = adjusted.copy()
        expected["trade_date"] = pd.to_datetime(expected["trade_date"]).dt.normalize()
        expected = expected[expected["trade_date"].isin(reconstructed["trade_date"])]
        expected = expected.sort_values("trade_date").reset_index(drop=True)
        reconstructed = reconstructed.sort_values("trade_date").reset_index(drop=True)

        max_close_error = float((reconstructed["close"] - expected["close"]).abs().max())
        factor_changes = int((factors["price_factor"].diff().abs() > 1e-10).sum())
        latest_factor = float(factors.iloc[-1]["price_factor"])
        print(
            f"[HT-CN M1 ADJ] OK {instrument_id}: raw={len(raw)}, factors={len(factors)}, "
            f"overlap={overlap_ratio:.2%}, factor_changes={factor_changes}, "
            f"latest_factor={latest_factor:.8f}, max_close_error={max_close_error:.10f}",
            flush=True,
        )
        if max_close_error > 1e-6:
            print(f"[HT-CN M1 ADJ] FAIL {instrument_id}: reconstruction mismatch", flush=True)
            return 2
        passed += 1

    if passed == 0:
        print("[HT-CN M1 ADJ] No pilot symbols available.", flush=True)
        return 1

    print(f"[HT-CN M1 ADJ] PASS: {passed} pilot instruments", flush=True)
    print(f"[HT-CN M1 ADJ] Factor root: {FACTOR_ROOT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
