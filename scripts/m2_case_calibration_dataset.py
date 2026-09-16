from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd

from htcn.app.harmonic_service import DatasetNotFoundError, LocalHarmonicService
from htcn.research.case_calibration import (
    DEFAULT_OBSERVATION_HORIZON,
    build_completed_case_record,
    dedupe_case_records,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "market"
OUT_DIR = ROOT / "artifacts" / "calibration"
JSON_PATH = OUT_DIR / "m2-case-calibration.json"
CSV_PATH = OUT_DIR / "m2-case-calibration.csv"
SCALES = (3, 5, 8, 13, 21)


def _symbols() -> list[str]:
    root = DATA_ROOT / "adjustment" / "qfq"
    if not root.exists():
        return []
    return sorted(path.stem for path in root.glob("*.parquet"))


def _flat_row(record: dict) -> dict:
    identity = record["identity"]
    quality = record["quality"]
    pivot = quality["pivot"]
    outcome = record["outcome"]
    return {
        "instrument_id": record["instrument_id"],
        "terminal_trade_date": record["terminal_trade_date"],
        "pattern_id": identity["pattern_id"],
        "schema": identity["schema"],
        "direction": identity["direction"],
        "scale": identity["scale"],
        "observed_scales": ",".join(str(value) for value in record.get("observed_scales", [])),
        "geometry_score": identity["geometry_score"],
        "reference_span_name": quality["reference_span_name"],
        "reference_span": quality["reference_span"],
        "prz_low": quality["prz_low"],
        "prz_high": quality["prz_high"],
        "prz_width": quality["prz_width"],
        "prz_width_ratio": quality["prz_width_ratio"],
        "pivot_min_support": pivot["min_support"],
        "pivot_mean_support": pivot["mean_support"],
        "pivot_terminal_support": pivot["terminal_support"],
        "reaction_family": outcome["family"],
        "observation_horizon_bars": outcome["observation_horizon_bars"],
        "available_future_bars": outcome["available_future_bars"],
        "bars_to_t1": outcome["bars_to_t1"],
        "bars_to_t2": outcome["bars_to_t2"],
        "bars_to_reciprocal_abcd": outcome["bars_to_reciprocal_abcd"],
        "type_ii_evidence_state": outcome["type_ii_evidence_state"],
        "outcome_class": outcome["outcome_class"],
    }


def _summary(records: list[dict]) -> dict:
    return {
        "cases": len(records),
        "by_pattern": dict(sorted(Counter(row["identity"]["pattern_id"] for row in records).items())),
        "by_schema": dict(sorted(Counter(row["identity"]["schema"] for row in records).items())),
        "by_outcome": dict(sorted(Counter(row["outcome"]["outcome_class"] for row in records).items())),
        "mature_cases": sum(row["outcome"]["outcome_class"] != "immature" for row in records),
        "t2_within_horizon": sum(row["outcome"]["outcome_class"] == "t2_within_horizon" for row in records),
        "no_t1_within_horizon": sum(row["outcome"]["outcome_class"] == "no_t1_within_horizon" for row in records),
    }


def _review_queue(records: list[dict], outcome_class: str, limit: int = 100) -> list[dict]:
    selected = [row for row in records if row["outcome"]["outcome_class"] == outcome_class]
    # Ordering is geometry/pivot-only. Outcome chooses the queue but never the rank inside it.
    selected.sort(
        key=lambda row: (
            row["quality"]["pivot"]["min_support"],
            row["quality"]["pivot"]["mean_support"],
            row["identity"]["geometry_score"],
        ),
        reverse=True,
    )
    return selected[:limit]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build M2 source/outcome-separated calibration dataset")
    parser.add_argument("--horizon", type=int, default=DEFAULT_OBSERVATION_HORIZON)
    parser.add_argument("--bars", type=int, default=3000)
    parser.add_argument("--max-symbols", type=int, default=0, help="0 means all initialized QFQ symbols")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.horizon < 1:
        raise SystemExit("--horizon must be >= 1")
    if args.bars < 80 or args.bars > 3000:
        raise SystemExit("--bars must be between 80 and 3000")

    symbols = _symbols()
    if args.max_symbols > 0:
        symbols = symbols[: args.max_symbols]
    if not symbols:
        print("[HT-CN M2 CAL] WARN: no initialized QFQ datasets; nothing to calibrate.")
        return 0

    print(
        f"[HT-CN M2 CAL] Building source/outcome-separated cases: "
        f"symbols={len(symbols)}, horizon={args.horizon}, bars={args.bars}"
    )
    service = LocalHarmonicService(DATA_ROOT)
    raw_records: list[dict] = []
    scanned = 0

    for symbol in symbols:
        try:
            result = service.analyze(
                symbol,
                bars=args.bars,
                scales=SCALES,
                max_completed=300,
                max_forming=20,
            )
        except DatasetNotFoundError:
            continue
        if not result["price_mode"].startswith("qfq"):
            continue
        scanned += 1
        for pattern in result["completed"]:
            if pattern.get("is_primary_identity") is False:
                continue
            raw_records.append(
                build_completed_case_record(
                    pattern,
                    instrument_id=symbol,
                    price_mode=result["price_mode"],
                    bars_returned=int(result["bars_returned"]),
                    observation_horizon=args.horizon,
                )
            )

    cases = dedupe_case_records(raw_records)
    payload = {
        "schema_version": 1,
        "status": "research_calibration_not_trading_model",
        "scope": {
            "symbols_requested": len(symbols),
            "symbols_scanned": scanned,
            "bars": args.bars,
            "scales": list(SCALES),
            "observation_horizon_bars": args.horizon,
            "raw_completed_primary_records": len(raw_records),
            "deduplicated_physical_cases": len(cases),
        },
        "summary": _summary(cases),
        "review_queues": {
            "strong_reaction_candidates": _review_queue(cases, "t2_within_horizon"),
            "negative_control_candidates": _review_queue(cases, "no_t1_within_horizon"),
            "immature_holdout": _review_queue(cases, "immature"),
        },
        "cases": cases,
        "methodology": {
            "identity": "Only source-valid completed primary identities emitted by the deterministic harmonic core are admitted.",
            "dedupe": "Same physical node sequence repeated across Pivot scales is collapsed using geometry and Pivot robustness only; later outcome is excluded from representative selection.",
            "outcome": "Outcome is stored in a separate namespace. Standard/ABCD/5-0 cases use 38.2% and 61.8% reaction audit; Shark uses its source-specific 50% and 61.8% targets.",
            "maturity": "A case with fewer future bars than the configured horizon is immature and cannot be labelled a negative control.",
            "horizon_policy": "The fixed observation horizon is an HT-CN calibration policy, not a Carney identity rule.",
            "anti_leakage": "Outcome success/failure cannot change geometry identity, geometry score, PRZ, Pivot selection or cross-scale dedupe ranking.",
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame([_flat_row(row) for row in cases]).to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

    summary = payload["summary"]
    print(
        f"[HT-CN M2 CAL] scanned={scanned}, raw={len(raw_records)}, cases={len(cases)}, "
        f"mature={summary['mature_cases']}, T2={summary['t2_within_horizon']}, "
        f"negative_controls={summary['no_t1_within_horizon']}"
    )
    print(f"[HT-CN M2 CAL] JSON: {JSON_PATH.relative_to(ROOT)}")
    print(f"[HT-CN M2 CAL] CSV : {CSV_PATH.relative_to(ROOT)}")
    print("[HT-CN M2 CAL] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
