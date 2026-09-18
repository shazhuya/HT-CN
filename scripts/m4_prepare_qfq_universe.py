from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import time
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from htcn.app.harmonic_service import LocalHarmonicService
from htcn.data.adjusted_fetch import fetch_adjusted_history
from htcn.data.adjustment import (
    AdjustmentFactorStore,
    derive_price_factors,
)
from htcn.data.providers import AkShareProvider, BaoStockProvider
from htcn.data.validation import normalize_daily


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "market"
CATALOG_PATH = DATA_ROOT / "catalog.duckdb"
REPORT_PATH = ROOT / "artifacts" / "reports" / "m4-qfq-readiness.json"
FORMAL_PRICE_MODES = {"qfq", "qfq_carry_forward"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare strict formal-QFQ coverage for the initialized M4 "
            "SSE/SZSE universe before authoritative prospective capture."
        )
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=1,
        help="extra retries per adjusted-history provider",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.05,
        help="small delay after a network build attempt",
    )
    return parser.parse_args()


def _instrument_ids(catalog: Path) -> list[str]:
    with duckdb.connect(str(catalog), read_only=True) as con:
        rows = con.execute(
            """
            SELECT s.instrument_id
            FROM security_master s
            JOIN daily_dataset d ON d.instrument_id = s.instrument_id
            WHERE s.status = 'listed'
              AND (
                s.instrument_id LIKE 'SSE.%'
                OR s.instrument_id LIKE 'SZSE.%'
              )
            ORDER BY s.instrument_id
            """
        ).fetchall()
    return [str(row[0]) for row in rows]


def _strict_factor_candidate(
    raw: pd.DataFrame,
    factors: pd.DataFrame,
) -> tuple[bool, str]:
    if raw.empty:
        return False, "raw_history_empty"
    if factors.empty:
        return False, "factor_history_empty"

    raw_dates = pd.to_datetime(raw["trade_date"]).dt.normalize()
    factor_dates = pd.to_datetime(
        factors["trade_date"]
    ).dt.normalize()

    if factor_dates.duplicated().any():
        return False, "duplicate_factor_dates"

    values = pd.to_numeric(
        factors["price_factor"],
        errors="coerce",
    ).astype(float)
    if values.isna().any() or (~np.isfinite(values)).any():
        return False, "non_finite_factor"
    if (values <= 0).any():
        return False, "non_positive_factor"

    raw_set = set(raw_dates)
    factor_set = set(factor_dates)
    overlap = len(raw_set.intersection(factor_set)) / max(1, len(raw_set))
    if overlap < 0.95:
        return False, f"factor_overlap_too_low:{overlap:.6f}"

    if factor_dates.min() > raw_dates.min():
        return False, "factor_history_starts_after_raw_history"

    latest_factor = factor_dates.max()
    historical_missing = sorted(
        stamp
        for stamp in raw_set
        if stamp <= latest_factor and stamp not in factor_set
    )
    if historical_missing:
        sample = ",".join(
            stamp.date().isoformat()
            for stamp in historical_missing[:5]
        )
        return False, f"historical_factor_gap:{sample}"

    return True, "strict_factor_candidate_ready"


def _formal_view_status(
    service: LocalHarmonicService,
    instrument_id: str,
    raw: pd.DataFrame,
) -> tuple[bool, str, str, str | None]:
    try:
        _, mode, warning, basis_id = service._continuous_view(
            instrument_id,
            raw,
        )
    except Exception as exc:
        return (
            False,
            "error",
            "error",
            f"{type(exc).__name__}: {exc}",
        )
    ready = (
        mode in FORMAL_PRICE_MODES
        and str(basis_id).startswith("qfq:")
    )
    return ready, str(mode), str(basis_id), warning


def _fetch_candidate(
    *,
    instrument_id: str,
    raw: pd.DataFrame,
    provider: Any,
    retries: int,
) -> tuple[pd.DataFrame, str, int]:
    start: date = pd.Timestamp(raw["trade_date"].min()).date()
    end: date = pd.Timestamp(raw["trade_date"].max()).date()
    fetched = fetch_adjusted_history(
        instrument_id=instrument_id,
        start=start,
        end=end,
        providers=[provider],
        mode="qfq",
        retries_per_provider=max(0, int(retries)),
        base_delay=0.75,
    )
    adjusted = normalize_daily(fetched.frame)
    factors = derive_price_factors(
        raw,
        adjusted,
        mode="qfq",
        source=fetched.source,
    )
    valid, reason = _strict_factor_candidate(raw, factors)
    if not valid:
        raise RuntimeError(reason)
    return factors, fetched.source, fetched.attempts


def run(
    *,
    data_root: Path = DATA_ROOT,
    catalog_path: Path = CATALOG_PATH,
    retries: int = 1,
    sleep_seconds: float = 0.05,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": 1,
        "status": "not_ready",
        "policy": (
            "Formal M4 prospective capture requires qfq/qfq_carry_forward "
            "for every initialized listed SSE/SZSE instrument. Existing formal "
            "views are reused; only missing or historically broken factor "
            "histories are fetched. Raw OHLCV remains durable truth."
        ),
        "initialized_instruments": 0,
        "already_formal_ready": 0,
        "built_or_repaired": 0,
        "formal_ready_after": 0,
        "failed_count": 0,
        "provider_build_counts": {},
        "rows": [],
        "failed": [],
        "alpha_inference_allowed": False,
        "is_trade_instruction": False,
    }

    if not catalog_path.is_file():
        report["failed"].append({
            "scope": "catalog",
            "error": f"missing {catalog_path}",
        })
        report["failed_count"] = 1
        return report

    instruments = _instrument_ids(catalog_path)
    report["initialized_instruments"] = len(instruments)
    if not instruments:
        report["failed"].append({
            "scope": "universe",
            "error": "no initialized listed SSE/SZSE instruments",
        })
        report["failed_count"] = 1
        return report

    service = LocalHarmonicService(data_root)
    factor_store = AdjustmentFactorStore(
        data_root / "adjustment" / "qfq"
    )
    providers = [AkShareProvider(), BaoStockProvider()]
    provider_counts: dict[str, int] = {}

    for position, instrument_id in enumerate(instruments, start=1):
        raw = service._load_history(instrument_id)
        ready, mode, basis_id, warning = _formal_view_status(
            service,
            instrument_id,
            raw,
        )
        if ready:
            report["already_formal_ready"] += 1
            report["formal_ready_after"] += 1
            report["rows"].append({
                "instrument_id": instrument_id,
                "status": "already_formal_ready",
                "price_mode": mode,
                "price_basis_id": basis_id,
                "warning": warning,
            })
            print(
                f"[HT-CN M4 QFQ] {position}/{len(instruments)} "
                f"READY {instrument_id}: mode={mode}",
                flush=True,
            )
            continue

        errors: list[str] = []
        built = False
        for provider in providers:
            print(
                f"[HT-CN M4 QFQ] {position}/{len(instruments)} "
                f"FETCH {instrument_id}: provider={getattr(provider, 'name', type(provider).__name__)}",
                flush=True,
            )
            try:
                factors, source, attempts = _fetch_candidate(
                    instrument_id=instrument_id,
                    raw=raw,
                    provider=provider,
                    retries=retries,
                )
                factor_store.write(factors)
                final_ready, final_mode, final_basis, final_warning = (
                    _formal_view_status(
                        service,
                        instrument_id,
                        raw,
                    )
                )
                if not final_ready:
                    raise RuntimeError(
                        "factor write did not produce formal QFQ view: "
                        f"mode={final_mode} basis={final_basis}"
                    )
                report["built_or_repaired"] += 1
                report["formal_ready_after"] += 1
                provider_counts[source] = provider_counts.get(source, 0) + 1
                report["rows"].append({
                    "instrument_id": instrument_id,
                    "status": "built_or_repaired",
                    "source": source,
                    "attempts": attempts,
                    "factor_rows": len(factors),
                    "price_mode": final_mode,
                    "price_basis_id": final_basis,
                    "warning": final_warning,
                })
                print(
                    f"[HT-CN M4 QFQ] {position}/{len(instruments)} "
                    f"BUILT {instrument_id}: source={source} "
                    f"factors={len(factors)} mode={final_mode}",
                    flush=True,
                )
                built = True
                break
            except Exception as exc:
                errors.append(
                    f"{getattr(provider, 'name', type(provider).__name__)}: "
                    f"{type(exc).__name__}: {exc}"
                )

        if not built:
            report["failed"].append({
                "instrument_id": instrument_id,
                "starting_mode": mode,
                "starting_basis": basis_id,
                "errors": errors,
            })
            report["rows"].append({
                "instrument_id": instrument_id,
                "status": "failed",
                "starting_mode": mode,
                "starting_basis": basis_id,
                "errors": errors,
            })
            print(
                f"[HT-CN M4 QFQ] {position}/{len(instruments)} "
                f"FAILED {instrument_id}: {' | '.join(errors[-4:])}",
                flush=True,
            )

        if sleep_seconds > 0:
            time.sleep(float(sleep_seconds))

    report["provider_build_counts"] = dict(sorted(provider_counts.items()))
    report["failed_count"] = len(report["failed"])
    if (
        report["failed_count"] == 0
        and report["formal_ready_after"]
        == report["initialized_instruments"]
    ):
        report["status"] = "formal_qfq_ready"
    else:
        report["status"] = "formal_qfq_not_ready"
    return report


def main() -> int:
    args = parse_args()
    print(
        "[HT-CN M4 QFQ] Preparing strict formal-QFQ universe...",
        flush=True,
    )
    payload = run(
        retries=args.retries,
        sleep_seconds=args.sleep,
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        ),
        encoding="utf-8",
    )
    print(
        "[HT-CN M4 QFQ] DONE "
        f"initialized={payload['initialized_instruments']} "
        f"already_ready={payload['already_formal_ready']} "
        f"built={payload['built_or_repaired']} "
        f"formal_ready={payload['formal_ready_after']} "
        f"failed={payload['failed_count']} "
        f"status={payload['status']}",
        flush=True,
    )
    print(
        f"[HT-CN M4 QFQ] Report: {REPORT_PATH.relative_to(ROOT)}",
        flush=True,
    )
    return 0 if payload["status"] == "formal_qfq_ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
