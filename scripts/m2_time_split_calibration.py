from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from htcn.app.harmonic_service import DatasetNotFoundError, LocalHarmonicService
from htcn.research.time_split import (
    assign_purged_split,
    derive_boundaries,
    grouped_summary,
    learn_numeric_thresholds,
    mature_forward_records,
    outcome_summary,
    split_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "market"
CAL_DIR = ROOT / "artifacts" / "calibration"
SOURCE_PATH = CAL_DIR / "m2-forming-walk-forward.json"
OUT_PATH = CAL_DIR / "m2-time-split-calibration.json"
TRAIN_CSV = CAL_DIR / "m2-time-split-train.csv"
VALIDATION_CSV = CAL_DIR / "m2-time-split-validation.csv"
HOLDOUT_INDEX_CSV = CAL_DIR / "m2-time-split-holdout-index.csv"


def _enrich_observation_end_dates(payload: dict) -> list[dict]:
    horizon = int(payload["scope"]["max_outcome_horizon_bars"])
    bars = int(payload["scope"]["bars"])
    service = LocalHarmonicService(DATA_ROOT)
    cache: dict[str, pd.DataFrame] = {}
    enriched: list[dict] = []

    for row in payload.get("records", []):
        outcome = row.get("outcome") or {}
        if outcome.get("pre_signal_prz_touch_bar") is not None:
            continue
        if int(outcome.get("available_future_bars", 0)) < horizon:
            continue
        symbol = str(row["instrument_id"])
        if symbol not in cache:
            try:
                raw = service._load_history(symbol)
            except DatasetNotFoundError:
                continue
            continuous, price_mode, _warning = service._continuous_view(symbol, raw)
            if not price_mode.startswith("qfq"):
                continue
            cache[symbol] = continuous.tail(bars).reset_index(drop=True)
        frame = cache[symbol]
        end_bar = int(row["signal_bar"]) + horizon
        if end_bar >= len(frame):
            continue
        item = dict(row)
        item["observation_end_bar"] = end_bar
        item["observation_end_trade_date"] = pd.Timestamp(
            frame.iloc[end_bar]["trade_date"]
        ).date().isoformat()
        enriched.append(item)
    return enriched


def _flat_rows(rows: list[dict], split: str, *, include_outcome: bool) -> list[dict]:
    result: list[dict] = []
    for row in rows:
        quality = row.get("quality_at_signal") or {}
        base = {
            "split": split,
            "instrument_id": row["instrument_id"],
            "signal_trade_date": row["signal_trade_date"],
            "observation_end_trade_date": row["observation_end_trade_date"],
            "pattern_id": row["pattern_id"],
            "schema": row["schema"],
            "direction": row["direction"],
            "source_scale": row["source_scale"],
            "scale_support_count": len(row.get("signal_scales") or []),
            "confirmation_lag_bars": row["confirmation_lag_bars"],
            "prz_width_ratio": quality.get("prz_width_ratio"),
            "distance_to_prz_ratio": quality.get("distance_to_prz_ratio"),
            "source_tolerance_used": quality.get("source_tolerance_used"),
        }
        if include_outcome:
            outcome = row["outcome"]
            base.update(
                {
                    "bars_to_first_future_prz_touch": outcome.get(
                        "bars_to_first_future_prz_touch"
                    ),
                    "touch_before_retirement": outcome.get("touch_before_retirement"),
                    "bars_to_completion_confirmation": outcome.get(
                        "bars_to_completion_confirmation"
                    ),
                    "completion_before_retirement": outcome.get(
                        "completion_before_retirement"
                    ),
                    "bars_to_frontier_retirement": outcome.get(
                        "bars_to_frontier_retirement"
                    ),
                    "outcome_class": outcome.get("outcome_class"),
                }
            )
        result.append(base)
    return result


def main() -> int:
    if not SOURCE_PATH.exists():
        print(
            "[HT-CN M2 SPLIT] FAIL: missing artifacts\\calibration\\m2-forming-walk-forward.json; "
            "run 运行M2前瞻校准.bat first."
        )
        return 1

    payload = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    horizon = int(payload["scope"]["max_outcome_horizon_bars"])
    enriched = _enrich_observation_end_dates(payload)
    mature = mature_forward_records(enriched, horizon=horizon)
    if len(mature) < 30:
        print(f"[HT-CN M2 SPLIT] FAIL: only {len(mature)} mature forward records; need >= 30.")
        return 1

    boundaries = derive_boundaries(mature)
    splits, purged = assign_purged_split(mature, boundaries)
    if not splits["train"] or not splits["validation"] or not splits["holdout"]:
        print("[HT-CN M2 SPLIT] FAIL: chronological split produced an empty partition.")
        return 1

    thresholds = learn_numeric_thresholds(splits["train"])
    train_summary = outcome_summary(splits["train"], horizon=horizon)
    validation_summary = outcome_summary(splits["validation"], horizon=horizon)
    train_groups = grouped_summary(
        splits["train"], thresholds=thresholds, horizon=horizon, min_group_size=5
    )
    validation_groups = grouped_summary(
        splits["validation"], thresholds=thresholds, horizon=horizon, min_group_size=5
    )

    out = {
        "schema_version": 1,
        "status": "research_time_split_holdout_sealed",
        "source": str(SOURCE_PATH.relative_to(ROOT)),
        "horizon_bars": horizon,
        "manifest": split_manifest(splits, purged=purged, boundaries=boundaries),
        "train_learned_thresholds": {
            "prz_width_ratio": list(thresholds.prz_width_ratio),
            "distance_to_prz_ratio": list(thresholds.distance_to_prz_ratio),
            "confirmation_lag_bars": list(thresholds.confirmation_lag_bars),
        },
        "train": {
            "outcome_summary": train_summary,
            "grouped_diagnostics": train_groups,
        },
        "validation": {
            "outcome_summary": validation_summary,
            "grouped_diagnostics": validation_groups,
        },
        "holdout": {
            "sealed": True,
            "records": len(splits["holdout"]),
            "outcomes_reported": False,
            "policy": "Holdout outcomes are intentionally not summarized until a quality policy is frozen after train/validation research.",
        },
        "methodology": {
            "chronology": "Global signal dates define 60% train / 20% validation / 20% holdout boundaries.",
            "purging": "Train labels that extend into validation and validation labels that extend into holdout are removed using the exact 60-trading-bar observation end date for each symbol.",
            "threshold_learning": "Numeric quality bucket thresholds are learned from TRAIN only and reused unchanged in validation.",
            "holdout": "Holdout membership is materialized, but outcome statistics are sealed to prevent iterative overfitting.",
            "identity_freeze": "Carney pattern identity and PRZ construction are not fitted or changed by these outcomes.",
            "scope_warning": "With only the currently initialized local QFQ universe, results are calibration diagnostics and are not representative of the full A-share market.",
        },
    }

    CAL_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(_flat_rows(splits["train"], "train", include_outcome=True)).to_csv(
        TRAIN_CSV, index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(
        _flat_rows(splits["validation"], "validation", include_outcome=True)
    ).to_csv(VALIDATION_CSV, index=False, encoding="utf-8-sig")
    pd.DataFrame(
        _flat_rows(splits["holdout"], "holdout", include_outcome=False)
    ).to_csv(HOLDOUT_INDEX_CSV, index=False, encoding="utf-8-sig")

    manifest = out["manifest"]
    print(
        f"[HT-CN M2 SPLIT] mature={len(mature)}, train={manifest['train']['records']}, "
        f"validation={manifest['validation']['records']}, holdout={manifest['holdout']['records']}, "
        f"purged={manifest['purged_boundary_records']}"
    )
    print(
        f"[HT-CN M2 SPLIT] dates: train<= {boundaries.train_end}; "
        f"validation={boundaries.validation_start}..{boundaries.validation_end}; "
        f"holdout>= {boundaries.holdout_start}"
    )
    print(
        f"[HT-CN M2 SPLIT] train touch60={train_summary['touch_rate']:.4f}, "
        f"completion60={train_summary['completion_rate']:.4f}, "
        f"retirement60={train_summary['retirement_rate']:.4f}"
    )
    print(
        f"[HT-CN M2 SPLIT] validation touch60={validation_summary['touch_rate']:.4f}, "
        f"completion60={validation_summary['completion_rate']:.4f}, "
        f"retirement60={validation_summary['retirement_rate']:.4f}"
    )
    print("[HT-CN M2 SPLIT] HOLDOUT SEALED: outcome statistics intentionally not opened.")
    print(f"[HT-CN M2 SPLIT] JSON: {OUT_PATH.relative_to(ROOT)}")
    print("[HT-CN M2 SPLIT] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
