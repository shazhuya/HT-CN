from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import median

import pandas as pd

from htcn.app.harmonic_service import DatasetNotFoundError, LocalHarmonicService
from htcn.research.walk_forward import (
    DEFAULT_FORWARD_HORIZON,
    DEFAULT_WALK_FORWARD_SCALES,
    walk_forward_forming_signals,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "market"
OUT_DIR = ROOT / "artifacts" / "calibration"
JSON_PATH = OUT_DIR / "m2-forming-walk-forward.json"
CSV_PATH = OUT_DIR / "m2-forming-walk-forward.csv"
CHECKPOINTS = (10, 20, 40, 60)


def _symbols() -> list[str]:
    root = DATA_ROOT / "adjustment" / "qfq"
    if not root.exists():
        return []
    return sorted(path.stem for path in root.glob("*.parquet"))


def _flat_row(record: dict) -> dict:
    outcome = record["outcome"]
    quality = record["quality_at_signal"]
    return {
        "instrument_id": record["instrument_id"],
        "pattern_id": record["pattern_id"],
        "schema": record["schema"],
        "direction": record["direction"],
        "signal_trade_date": record["signal_trade_date"],
        "signal_bar": record["signal_bar"],
        "source_scale": record["source_scale"],
        "signal_scales": ",".join(str(value) for value in record["signal_scales"]),
        "terminal_pivot_bar": record["terminal_pivot_bar"],
        "confirmation_lag_bars": record["confirmation_lag_bars"],
        "prz_low": record["prz"]["price_low"],
        "prz_high": record["prz"]["price_high"],
        "prz_width": record["prz"]["width"],
        "reference_span_name": quality["reference_span_name"],
        "reference_span": quality["reference_span"],
        "prz_width_ratio": quality["prz_width_ratio"],
        "distance_to_prz_ratio": quality["distance_to_prz_ratio"],
        "source_tolerance_used": quality["source_tolerance_used"],
        "available_future_bars": outcome["available_future_bars"],
        "pre_signal_prz_touch_bar": outcome["pre_signal_prz_touch_bar"],
        "bars_to_first_future_prz_touch": outcome["bars_to_first_future_prz_touch"],
        "touch_before_retirement": outcome["touch_before_retirement"],
        "bars_to_frontier_retirement": outcome["bars_to_frontier_retirement"],
        "bars_to_completion_terminal": outcome["bars_to_completion_terminal"],
        "bars_to_completion_confirmation": outcome["bars_to_completion_confirmation"],
        "completion_before_retirement": outcome["completion_before_retirement"],
        "outcome_class": outcome["outcome_class"],
    }


def _horizon_summary(records: list[dict], checkpoint: int) -> dict:
    eligible = [
        row
        for row in records
        if row["outcome"]["pre_signal_prz_touch_bar"] is None
        and int(row["outcome"]["available_future_bars"]) >= checkpoint
    ]
    touches = [
        row
        for row in eligible
        if row["outcome"]["touch_before_retirement"]
        and row["outcome"]["bars_to_first_future_prz_touch"] is not None
        and int(row["outcome"]["bars_to_first_future_prz_touch"]) <= checkpoint
    ]
    completions = [
        row
        for row in eligible
        if row["outcome"]["completion_before_retirement"]
        and row["outcome"]["bars_to_completion_confirmation"] is not None
        and 0 <= int(row["outcome"]["bars_to_completion_confirmation"]) <= checkpoint
    ]
    retired = [
        row
        for row in eligible
        if row["outcome"]["bars_to_frontier_retirement"] is not None
        and 0 <= int(row["outcome"]["bars_to_frontier_retirement"]) <= checkpoint
        and not (
            row["outcome"]["touch_before_retirement"]
            and row["outcome"]["bars_to_first_future_prz_touch"] is not None
            and int(row["outcome"]["bars_to_first_future_prz_touch"]) <= checkpoint
        )
    ]
    denominator = len(eligible)
    return {
        "mature_forward_eligible": denominator,
        "prz_touched_before_retirement": len(touches),
        "engine_completion_confirmed_before_retirement": len(completions),
        "frontier_retired_without_prior_touch": len(retired),
        "touch_rate": None if denominator == 0 else len(touches) / denominator,
        "completion_rate": None if denominator == 0 else len(completions) / denominator,
        "retirement_rate": None if denominator == 0 else len(retired) / denominator,
    }


def _summary(records: list[dict]) -> dict:
    future_touch_leads = [
        int(row["outcome"]["bars_to_first_future_prz_touch"])
        for row in records
        if row["outcome"]["pre_signal_prz_touch_bar"] is None
        and row["outcome"]["touch_before_retirement"]
        and row["outcome"]["bars_to_first_future_prz_touch"] is not None
    ]
    completion_leads = [
        int(row["outcome"]["bars_to_completion_confirmation"])
        for row in records
        if row["outcome"]["pre_signal_prz_touch_bar"] is None
        and row["outcome"]["completion_before_retirement"]
        and row["outcome"]["bars_to_completion_confirmation"] is not None
        and int(row["outcome"]["bars_to_completion_confirmation"]) >= 0
    ]
    return {
        "signals": len(records),
        "by_pattern": dict(sorted(Counter(row["pattern_id"] for row in records).items())),
        "by_schema": dict(sorted(Counter(row["schema"] for row in records).items())),
        "by_outcome": dict(sorted(Counter(row["outcome"]["outcome_class"] for row in records).items())),
        "late_signals_prz_already_touched": sum(
            row["outcome"]["pre_signal_prz_touch_bar"] is not None for row in records
        ),
        "forward_eligible_signals": sum(
            row["outcome"]["pre_signal_prz_touch_bar"] is None for row in records
        ),
        "median_bars_to_first_future_touch": None if not future_touch_leads else median(future_touch_leads),
        "median_bars_to_completion_confirmation": None if not completion_leads else median(completion_leads),
        "checkpoints": {str(value): _horizon_summary(records, value) for value in CHECKPOINTS},
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay forming harmonic projections without future leakage")
    parser.add_argument("--horizon", type=int, default=DEFAULT_FORWARD_HORIZON)
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
        print("[HT-CN M2 WF] WARN: no initialized QFQ datasets; nothing to replay.")
        return 0

    service = LocalHarmonicService(DATA_ROOT)
    records: list[dict] = []
    scanned = 0
    print(
        f"[HT-CN M2 WF] Event-driven no-lookahead replay: symbols={len(symbols)}, "
        f"bars={args.bars}, horizon={args.horizon}, scales={DEFAULT_WALK_FORWARD_SCALES}"
    )

    for position, symbol in enumerate(symbols, start=1):
        try:
            raw = service._load_history(symbol)
        except DatasetNotFoundError:
            continue
        continuous, price_mode, warning = service._continuous_view(symbol, raw)
        if not price_mode.startswith("qfq"):
            continue
        frame = continuous.tail(args.bars).reset_index(drop=True)
        if len(frame) < 80:
            continue

        symbol_records = walk_forward_forming_signals(
            frame,
            scales=DEFAULT_WALK_FORWARD_SCALES,
            horizon=args.horizon,
        )
        for row in symbol_records:
            row["instrument_id"] = symbol
            row["price_mode"] = price_mode
            row["data_warning"] = warning
        records.extend(symbol_records)
        scanned += 1
        print(
            f"[HT-CN M2 WF] {position}/{len(symbols)} {symbol}: "
            f"bars={len(frame)}, signals={len(symbol_records)}"
        )

    payload = {
        "schema_version": 1,
        "status": "research_walk_forward_not_trading_model",
        "scope": {
            "symbols_requested": len(symbols),
            "symbols_scanned": scanned,
            "bars": args.bars,
            "scales": list(DEFAULT_WALK_FORWARD_SCALES),
            "max_outcome_horizon_bars": args.horizon,
        },
        "summary": _summary(records),
        "records": records,
        "methodology": {
            "information_boundary": "A projection is emitted only after its terminal frontier pivot has been confirmed by the configured right-side scale. Later pivot events are not visible early.",
            "event_driven": "The replay advances only on pivot-confirmation bars because harmonic frontier geometry cannot change between confirmation events. This is computational optimization, not sampling of outcomes.",
            "late_signal_policy": "If the projected PRZ was already touched between the terminal pivot bar and its confirmation/signal bar, the signal is labelled late and excluded from forward-eligible checkpoint denominators.",
            "retirement_policy": "A projection stops being active when no configured scale retains the same physical frontier. A later touch after retirement is not credited as an active forecast success.",
            "completion_policy": "Engine completion is matched by exact pattern/schema/direction plus the same prefix pivot indices. Both physical completion-bar lead and later confirmation-bar lead are retained.",
            "checkpoint_policy": "10/20/40/60-bar rates are descriptive HT-CN research horizons, not Carney identity rules or trading probabilities.",
            "anti_leakage": "Future touch/completion/retirement outcomes never alter the original projection, PRZ, source scale, or first-signal timestamp.",
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame([_flat_row(row) for row in records]).to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

    summary = payload["summary"]
    h60 = summary["checkpoints"].get("60", {})
    print(
        f"[HT-CN M2 WF] scanned={scanned}, signals={summary['signals']}, "
        f"forward_eligible={summary['forward_eligible_signals']}, "
        f"late={summary['late_signals_prz_already_touched']}"
    )
    print(
        f"[HT-CN M2 WF] mature60={h60.get('mature_forward_eligible', 0)}, "
        f"touch60={h60.get('prz_touched_before_retirement', 0)}, "
        f"completion60={h60.get('engine_completion_confirmed_before_retirement', 0)}, "
        f"retired60={h60.get('frontier_retired_without_prior_touch', 0)}"
    )
    print(f"[HT-CN M2 WF] JSON: {JSON_PATH.relative_to(ROOT)}")
    print(f"[HT-CN M2 WF] CSV : {CSV_PATH.relative_to(ROOT)}")
    print("[HT-CN M2 WF] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
