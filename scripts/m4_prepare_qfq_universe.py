from __future__ import annotations

import argparse
import json
import time
from datetime import date
from pathlib import Path
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
SAFE_INTERNAL_GAP_MAX_RAW_SESSIONS = 10
SAFE_INTERNAL_GAP_MAX_RELATIVE_FACTOR_DRIFT = 0.005
SAFE_HISTORICAL_SATURDAY_FACTOR_DRIFT = 0.05
SAFE_RAW_PRECLOSE_CONTINUITY_DRIFT = 0.01
FORMAL_CAPTURE_ANALYSIS_BARS = 420
SZSE_FIVE_DAY_WEEK_START = date(1992, 1, 1)


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


def _repair_safe_internal_factor_gaps(
    raw: pd.DataFrame,
    factors: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Fill tiny provider-calendar holes without crossing factor regime jumps.

    QFQ factors are expected to be locally stable between corporate-action
    regime changes. Some providers omit historical sessions (notably early
    Saturday trading) even when raw history contains them. We only synthesize
    missing *internal* raw-session factors when:
      - the gap is bracketed on both sides by real factor observations;
      - the missing run is short;
      - the bracketing factor levels differ by <= 0.5%.

    Leading gaps, trailing gaps, and ordinary factor-regime jumps remain
    fail-closed. Narrow legacy-calendar bridges are allowed only when the whole
    gap is strictly outside the frozen 420-bar formal prospective-capture
    window: pre-1992 Saturday sessions may be genuine early-market sessions,
    while weekend rows on/after the SZSE five-day-week start are treated as
    legacy raw-calendar anomalies. Those synthetic rows can never enter the
    current formal harmonic analysis; every bridge remains audited. Trailing
    freshness remains owned by qfq_carry_forward.
    """
    if raw.empty or factors.empty:
        return factors.copy(), []

    raw_order = (
        pd.to_datetime(raw["trade_date"])
        .dt.normalize()
        .drop_duplicates()
        .sort_values()
        .tolist()
    )
    out = factors.copy()
    out["trade_date"] = pd.to_datetime(out["trade_date"]).dt.normalize()
    out = out.sort_values("trade_date").reset_index(drop=True)

    factor_by_date = {
        pd.Timestamp(row.trade_date).normalize(): float(row.price_factor)
        for row in out.itertuples(index=False)
    }
    max_factor_date = max(factor_by_date)
    candidate_missing = [
        pd.Timestamp(stamp).normalize()
        for stamp in raw_order
        if pd.Timestamp(stamp).normalize() <= max_factor_date
        and pd.Timestamp(stamp).normalize() not in factor_by_date
    ]
    if not candidate_missing:
        return out, []

    raw_position = {
        pd.Timestamp(stamp).normalize(): index
        for index, stamp in enumerate(raw_order)
    }
    runs: list[list[pd.Timestamp]] = []
    current: list[pd.Timestamp] = []
    previous_position: int | None = None
    for stamp in candidate_missing:
        position = raw_position[stamp]
        if (
            current
            and previous_position is not None
            and position != previous_position + 1
        ):
            runs.append(current)
            current = []
        current.append(stamp)
        previous_position = position
    if current:
        runs.append(current)

    additions: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    instrument_id = str(out.iloc[0]["instrument_id"])
    mode = str(out.iloc[0].get("mode", "qfq"))

    for run in runs:
        first_position = raw_position[run[0]]
        last_position = raw_position[run[-1]]
        if len(run) > SAFE_INTERNAL_GAP_MAX_RAW_SESSIONS:
            continue
        if first_position <= 0 or last_position >= len(raw_order) - 1:
            continue

        previous_date = pd.Timestamp(
            raw_order[first_position - 1]
        ).normalize()
        next_date = pd.Timestamp(
            raw_order[last_position + 1]
        ).normalize()
        if (
            previous_date not in factor_by_date
            or next_date not in factor_by_date
        ):
            continue

        previous_factor = float(factor_by_date[previous_date])
        next_factor = float(factor_by_date[next_date])
        midpoint = (previous_factor + next_factor) / 2.0
        relative_drift = (
            abs(next_factor - previous_factor)
            / max(abs(midpoint), 1e-12)
        )

        fill_rule = "stable_factor_brackets"
        allowed_factor_drift = SAFE_INTERNAL_GAP_MAX_RELATIVE_FACTOR_DRIFT

        if relative_drift > allowed_factor_drift:
            # D-077/D-078 calendar bridges are evaluated before optional raw
            # pre_close continuity. Pre-1992 Saturdays can be genuine early
            # A-share sessions. From 1992-01-01 SZSE had a five-day trading
            # week, so weekend raw rows from that point forward are legacy
            # calendar anomalies rather than formal trading sessions.
            historical_saturday_run = all(
                stamp.weekday() == 5
                and stamp.date() < SZSE_FIVE_DAY_WEEK_START
                for stamp in run
            )
            post_five_day_weekend_anomaly_run = all(
                stamp.weekday() >= 5
                and stamp.date() >= SZSE_FIVE_DAY_WEEK_START
                for stamp in run
            )
            formal_window_start_position = max(
                0,
                len(raw_order) - FORMAL_CAPTURE_ANALYSIS_BARS,
            )
            outside_formal_window = (
                last_position < formal_window_start_position
            )
            if historical_saturday_run and outside_formal_window:
                fill_rule = "legacy_saturday_outside_formal_capture_window"
                allowed_factor_drift = None
            elif (
                post_five_day_weekend_anomaly_run
                and outside_formal_window
            ):
                fill_rule = (
                    "legacy_nontrading_weekend_outside_formal_capture_window"
                )
                allowed_factor_drift = None
            else:
                # Inside the formal capture window there is no legacy escape.
                # Only genuine pre-1992 Saturday holes may use raw pre-close
                # continuity; post-five-day weekend anomalies remain blocked.
                if not historical_saturday_run or "pre_close" not in raw.columns:
                    continue

                raw_indexed = raw.copy()
                raw_indexed["trade_date"] = pd.to_datetime(
                    raw_indexed["trade_date"]
                ).dt.normalize()
                raw_indexed = raw_indexed.set_index("trade_date", drop=False)

                continuity_checks: list[float] = []
                valid_prec_close = True
                previous_raw_date = previous_date
                for stamp in run:
                    previous_close = pd.to_numeric(
                        raw_indexed.loc[previous_raw_date, "close"],
                        errors="coerce",
                    )
                    missing_pre_close = pd.to_numeric(
                        raw_indexed.loc[stamp, "pre_close"],
                        errors="coerce",
                    )
                    if (
                        pd.isna(previous_close)
                        or pd.isna(missing_pre_close)
                        or float(previous_close) <= 0
                        or float(missing_pre_close) <= 0
                    ):
                        valid_prec_close = False
                        break
                    continuity_checks.append(
                        abs(float(missing_pre_close) - float(previous_close))
                        / max(abs(float(previous_close)), 1e-12)
                    )
                    previous_raw_date = stamp

                if valid_prec_close:
                    last_close = pd.to_numeric(
                        raw_indexed.loc[run[-1], "close"],
                        errors="coerce",
                    )
                    next_pre_close = pd.to_numeric(
                        raw_indexed.loc[next_date, "pre_close"],
                        errors="coerce",
                    )
                    if (
                        pd.isna(last_close)
                        or pd.isna(next_pre_close)
                        or float(last_close) <= 0
                        or float(next_pre_close) <= 0
                    ):
                        valid_prec_close = False
                    else:
                        continuity_checks.append(
                            abs(float(next_pre_close) - float(last_close))
                            / max(abs(float(last_close)), 1e-12)
                        )

                if (
                    not valid_prec_close
                    or not continuity_checks
                    or max(continuity_checks)
                    > SAFE_RAW_PRECLOSE_CONTINUITY_DRIFT
                    or relative_drift > SAFE_HISTORICAL_SATURDAY_FACTOR_DRIFT
                ):
                    continue
                fill_rule = "historical_saturday_raw_preclose_continuity"
                allowed_factor_drift = SAFE_HISTORICAL_SATURDAY_FACTOR_DRIFT

        # Linear interpolation in raw-session index is deterministic and keeps
        # the synthetic values bounded by the two observed factor values.
        steps = len(run) + 1
        for offset, stamp in enumerate(run, start=1):
            weight = offset / steps
            factor = (
                previous_factor * (1.0 - weight)
                + next_factor * weight
            )
            additions.append({
                "instrument_id": instrument_id,
                "trade_date": stamp,
                "price_factor": factor,
                "mode": mode,
                "source": "safe_internal_calendar_gap_fill",
            })
            factor_by_date[stamp] = factor

        audit.append({
            "gap_start_trade_date": run[0].date().isoformat(),
            "gap_end_trade_date": run[-1].date().isoformat(),
            "gap_raw_session_count": len(run),
            "previous_factor_trade_date": previous_date.date().isoformat(),
            "next_factor_trade_date": next_date.date().isoformat(),
            "previous_factor": previous_factor,
            "next_factor": next_factor,
            "relative_factor_drift": relative_drift,
            "allowed_factor_drift": allowed_factor_drift,
            "fill_rule": fill_rule,
            "fill_method": "linear_between_bracketing_factors",
        })

    if additions:
        out = pd.concat(
            [out, pd.DataFrame(additions)],
            ignore_index=True,
        )
        out = (
            out.drop_duplicates(
                ["instrument_id", "trade_date"],
                keep="last",
            )
            .sort_values("trade_date")
            .reset_index(drop=True)
        )
    return out, audit


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
) -> tuple[pd.DataFrame, str, int, list[dict[str, Any]]]:
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
    factors, gap_repairs = _repair_safe_internal_factor_gaps(
        raw,
        factors,
    )
    valid, reason = _strict_factor_candidate(raw, factors)
    if not valid:
        raise RuntimeError(reason)
    return factors, fetched.source, fetched.attempts, gap_repairs


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
            "histories are fetched. Audited pre-1992 Saturday holes and "
            "post-five-day non-trading weekend raw-calendar anomalies may be "
            "bridged only outside the frozen 420-bar capture window. Raw "
            "OHLCV remains durable truth."
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

        existing_factors = factor_store.read(instrument_id)
        if not existing_factors.empty:
            repaired_factors, local_repairs = _repair_safe_internal_factor_gaps(
                raw,
                existing_factors,
            )
            local_valid, _ = _strict_factor_candidate(raw, repaired_factors)
            if local_valid and local_repairs:
                factor_store.write(repaired_factors)
                final_ready, final_mode, final_basis, final_warning = (
                    _formal_view_status(service, instrument_id, raw)
                )
                if final_ready:
                    report["built_or_repaired"] += 1
                    report["formal_ready_after"] += 1
                    report["rows"].append({
                        "instrument_id": instrument_id,
                        "status": "repaired_local_factor_store",
                        "source": "local_factor_store",
                        "factor_rows": len(repaired_factors),
                        "safe_internal_gap_repairs": local_repairs,
                        "safe_internal_gap_repair_count": sum(
                            int(item["gap_raw_session_count"])
                            for item in local_repairs
                        ),
                        "price_mode": final_mode,
                        "price_basis_id": final_basis,
                        "warning": final_warning,
                    })
                    print(
                        f"[HT-CN M4 QFQ] {position}/{len(instruments)} "
                        f"REPAIRED {instrument_id}: local factors "
                        f"repairs={len(local_repairs)} mode={final_mode}",
                        flush=True,
                    )
                    if sleep_seconds > 0:
                        time.sleep(float(sleep_seconds))
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
                factors, source, attempts, gap_repairs = _fetch_candidate(
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
                    "safe_internal_gap_repairs": gap_repairs,
                    "safe_internal_gap_repair_count": sum(
                        int(item["gap_raw_session_count"])
                        for item in gap_repairs
                    ),
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
