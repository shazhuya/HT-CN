from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd

from htcn.data.adjusted_fetch import fetch_adjusted_history
from htcn.data.providers import AkShareProvider, BaoStockProvider
from htcn.data.validation import normalize_daily
from htcn.research.autonomous_calibration import (
    build_autonomous_quality_report,
    enrich_walk_forward_records,
)
from htcn.research.completed_reaction import (
    DEFAULT_COMPLETED_REACTION_HORIZON,
    confirmed_completed_reaction_records,
)
from htcn.research.completed_reaction_calibration import (
    attach_completed_reaction_observation_windows,
    build_completed_reaction_calibration,
    completed_reaction_inventory,
    redact_completed_reaction_holdout,
)
from htcn.research.quality_layers import build_layered_quality_report
from htcn.research.quality_robustness import build_quality_robustness_report
from htcn.research.snapshot_cache import (
    CachedResearchSnapshot,
    load_research_snapshot,
    snapshot_manifest_entry,
    write_research_snapshot,
)
from htcn.research.walk_forward import walk_forward_forming_signals

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "research" / "a-share-research-universe-v1.json"
OUT_DIR = ROOT / "artifacts" / "ci-research"
DATA_DIR = OUT_DIR / "data"
REPORT_PATH = OUT_DIR / "m2-autonomous-research-report.json"
COMPLETED_REACTION_PATH = OUT_DIR / "m2-confirmed-completed-reactions.json"
SNAPSHOT_MANIFEST_PATH = OUT_DIR / "m2-research-snapshot-manifest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run autonomous real-A-share calibration in CI")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--max-symbols", type=int, default=0)
    parser.add_argument(
        "--no-snapshot-cache",
        action="store_true",
        help="ignore restored research snapshots and fetch every requested symbol",
    )
    return parser.parse_args()


def _load_manifest(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not payload.get("instruments"):
        raise ValueError("research manifest has no instruments")
    return payload


def _research_snapshot(
    *,
    instrument_id: str,
    start: date,
    end: date,
    max_bars: int,
    providers: list,
    use_cache: bool,
) -> tuple[CachedResearchSnapshot, int, str]:
    miss_reason = "cache_disabled"
    if use_cache:
        cached, miss_reason = load_research_snapshot(
            DATA_DIR,
            instrument_id=instrument_id,
            requested_start=start,
            requested_end=end,
            max_bars=max_bars,
            price_mode="qfq",
        )
        if cached is not None:
            return cached, 0, miss_reason

    fetched = fetch_adjusted_history(
        instrument_id=instrument_id,
        start=start,
        end=end,
        providers=providers,
        mode="qfq",
        retries_per_provider=1,
        base_delay=0.5,
    )
    frame = normalize_daily(fetched.frame).tail(max_bars).reset_index(drop=True)
    snapshot = write_research_snapshot(
        DATA_DIR,
        instrument_id=instrument_id,
        frame=frame,
        source=fetched.source,
        requested_start=start,
        requested_end=end,
        max_bars=max_bars,
        price_mode="qfq",
    )
    return snapshot, fetched.attempts, miss_reason


def main() -> int:
    args = parse_args()
    manifest = _load_manifest(args.manifest)
    instruments = list(manifest["instruments"])
    if args.max_symbols > 0:
        instruments = instruments[: args.max_symbols]

    start = date.fromisoformat(str(manifest["start_date"]))
    end = date.fromisoformat(str(manifest["snapshot_cutoff"]))
    max_bars = int(manifest.get("max_bars", 3000))
    horizon = int(manifest.get("horizon_bars", 60))
    reaction_horizon = int(
        manifest.get("completed_reaction_horizon_bars", DEFAULT_COMPLETED_REACTION_HORIZON)
    )
    scales = tuple(int(value) for value in manifest.get("scales", [3, 5, 8, 13, 21]))
    minimum_symbols = int(manifest.get("minimum_successful_symbols", 6))
    minimum_completed_actionable = int(
        manifest.get("minimum_completed_reaction_actionable_records", 60)
    )
    minimum_completed_train = int(manifest.get("minimum_completed_reaction_train_records", 30))
    minimum_completed_validation = int(
        manifest.get("minimum_completed_reaction_validation_records", 10)
    )
    minimum_completed_holdout = int(
        manifest.get("minimum_completed_reaction_holdout_records", 10)
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    providers = [AkShareProvider(), BaoStockProvider()]
    all_records: list[dict] = []
    all_completed_reactions: list[dict] = []
    datasets: list[dict] = []
    snapshot_entries: list[dict] = []
    failures: list[dict] = []
    cache_miss_reasons: Counter[str] = Counter()

    print(
        f"[HT-CN AUTONOMOUS] real-A-share research: symbols={len(instruments)}, "
        f"window={start}..{end}, forming_horizon={horizon}, "
        f"reaction_horizon={reaction_horizon}, bars<={max_bars}, scales={scales}, "
        f"snapshot_cache={'off' if args.no_snapshot_cache else 'on'}"
    )

    for position, item in enumerate(instruments, start=1):
        instrument_id = str(item["instrument_id"])
        try:
            snapshot, attempts, cache_reason = _research_snapshot(
                instrument_id=instrument_id,
                start=start,
                end=end,
                max_bars=max_bars,
                providers=providers,
                use_cache=not args.no_snapshot_cache,
            )
            frame = snapshot.frame
            if len(frame) < 120:
                raise RuntimeError(f"too few QFQ bars: {len(frame)}")
            if snapshot.cache_status != "hit_verified":
                cache_miss_reasons[cache_reason] += 1

            symbol_records = walk_forward_forming_signals(
                frame,
                scales=scales,
                horizon=horizon,
            )
            enriched = enrich_walk_forward_records(
                symbol_records,
                frame=frame,
                instrument_id=instrument_id,
                horizon=horizon,
            )

            completed_reactions = confirmed_completed_reaction_records(
                frame,
                instrument_id=instrument_id,
                scales=scales,
                horizon=reaction_horizon,
            )
            completed_reactions = attach_completed_reaction_observation_windows(
                completed_reactions,
                trade_dates=frame["trade_date"].tolist(),
                horizon=reaction_horizon,
            )

            all_records.extend(enriched)
            all_completed_reactions.extend(completed_reactions)
            snapshot_entry = snapshot_manifest_entry(snapshot)
            snapshot_entries.append(snapshot_entry)
            datasets.append(
                {
                    "instrument_id": instrument_id,
                    "name": item.get("name"),
                    "bucket": item.get("bucket"),
                    "source": snapshot.source,
                    "attempts": attempts,
                    "cache_status": snapshot.cache_status,
                    "cache_miss_reason": None if snapshot.cache_status == "hit_verified" else cache_reason,
                    "bars": len(frame),
                    "first_trade_date": pd.Timestamp(frame.iloc[0]["trade_date"]).date().isoformat(),
                    "last_trade_date": pd.Timestamp(frame.iloc[-1]["trade_date"]).date().isoformat(),
                    "forming_signals": len(symbol_records),
                    "confirmed_completed_reactions": len(completed_reactions),
                    "snapshot": str((DATA_DIR / f"{instrument_id}.parquet").relative_to(ROOT)),
                    "sha256": snapshot.sha256,
                }
            )
            print(
                f"[HT-CN AUTONOMOUS] {position}/{len(instruments)} OK {instrument_id}: "
                f"cache={snapshot.cache_status}, source={snapshot.source}, bars={len(frame)}, "
                f"forming={len(symbol_records)}, completed={len(completed_reactions)}"
            )
        except Exception as exc:
            failures.append(
                {
                    "instrument_id": instrument_id,
                    "name": item.get("name"),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            print(
                f"[HT-CN AUTONOMOUS] {position}/{len(instruments)} WARN {instrument_id}: "
                f"{type(exc).__name__}: {exc}"
            )

    coverage_ok = len(datasets) >= minimum_symbols
    cache_hits = sum(row["cache_status"] == "hit_verified" for row in datasets)
    cache_misses = len(datasets) - cache_hits

    calibration = build_autonomous_quality_report(
        all_records,
        horizon=horizon,
        minimum_mature_records=30,
    )
    robustness = build_quality_robustness_report(
        all_records,
        horizon=horizon,
        min_mature_records=100,
    )
    layered = build_layered_quality_report(
        all_records,
        robust_gate_names=robustness.get("robust_research_candidates", []),
        horizon=horizon,
        min_mature_records=100,
    )

    completed_inventory = completed_reaction_inventory(all_completed_reactions)
    completed_calibration = build_completed_reaction_calibration(
        all_completed_reactions,
        horizon=reaction_horizon,
        minimum_actionable_records=minimum_completed_actionable,
        minimum_train_records=minimum_completed_train,
        minimum_validation_records=minimum_completed_validation,
        minimum_holdout_records=minimum_completed_holdout,
    )
    emitted_completed_reactions = redact_completed_reaction_holdout(
        all_completed_reactions,
        completed_calibration,
    )

    forming_ok = (
        coverage_ok
        and calibration.get("status") == "research_quality_evidence_holdout_sealed"
        and robustness.get("status") == "research_robustness_holdout_sealed"
        and layered.get("status") == "research_layers_holdout_sealed"
    )
    completed_reaction_ready = (
        completed_calibration.get("status") == "completed_reaction_calibration_holdout_sealed"
    )
    if forming_ok and completed_reaction_ready:
        research_status = "calibration_complete"
    elif forming_ok:
        research_status = "forming_calibration_complete_completed_reaction_sample_insufficient"
    else:
        research_status = "insufficient_provider_or_sample_coverage"

    snapshot_manifest = {
        "schema_version": 1,
        "dataset_id": manifest.get("dataset_id"),
        "snapshot_cutoff": manifest.get("snapshot_cutoff"),
        "price_mode": "qfq",
        "requested_symbols": len(instruments),
        "successful_symbols": len(snapshot_entries),
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "cache_miss_reasons": dict(sorted(cache_miss_reasons.items())),
        "snapshots": sorted(snapshot_entries, key=lambda row: row["instrument_id"]),
        "policy": {
            "cache_hit": "A cached parquet is reused only after sidecar metadata and exact parquet SHA256 verification.",
            "cutoff": "A different snapshot cutoff invalidates the restored symbol snapshot.",
            "expansion": "Manifest expansion may restore older same-cutoff symbol snapshots and fetch only missing/incompatible symbols.",
            "provider_restatement": "Accepted cache hits are byte-frozen for the pinned cutoff; provider restatements cannot silently replace them.",
        },
    }
    SNAPSHOT_MANIFEST_PATH.write_text(
        json.dumps(snapshot_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    report = {
        "schema_version": 6,
        "status": research_status,
        "dataset_id": manifest.get("dataset_id"),
        "snapshot_cutoff": manifest.get("snapshot_cutoff"),
        "requested_symbols": len(instruments),
        "successful_symbols": len(datasets),
        "minimum_successful_symbols": minimum_symbols,
        "coverage_ok": coverage_ok,
        "snapshot_cache": {
            "enabled": not args.no_snapshot_cache,
            "hits": cache_hits,
            "misses": cache_misses,
            "miss_reasons": dict(sorted(cache_miss_reasons.items())),
            "manifest": str(SNAPSHOT_MANIFEST_PATH.relative_to(ROOT)),
        },
        "datasets": datasets,
        "failures": failures,
        "forming_signals": len(all_records),
        "confirmed_completed_reaction_records": len(all_completed_reactions),
        "calibration": calibration,
        "robustness": robustness,
        "layers": layered,
        "completed_reaction_inventory": completed_inventory,
        "completed_reaction_calibration": completed_calibration,
        "methodology": {
            "runtime": "GitHub Actions / CI-accessible; no user workstation data is required.",
            "source": "Provider QFQ is used only to create missing pinned research snapshots, separate from production raw+factor storage.",
            "snapshot_freeze": "A verified same-cutoff cached parquet is reused byte-for-byte; each symbol carries a source sidecar and SHA256.",
            "forming_holdout": "Forming-signal Holdout outcomes remain sealed during iterative calibration, robustness and semantic-layer research.",
            "completed_holdout": "Completed-reaction Holdout outcomes are omitted from calibration summaries and redacted from the emitted reaction record artifact.",
            "identity": "Carney geometry/identity is frozen and never fitted to later outcomes.",
            "robustness": "Strong forming gates are stress-tested across symbols, leave-one-symbol-out and coarse time segments before any policy freeze.",
            "semantic_layers": "Structural quality, readiness and context are separated before generalization; distance-to-PRZ is readiness, not geometry quality.",
            "completed_reaction_clock": "Completed reaction evidence starts at terminal Pivot confirmation, not at historical D, so pre-confirmation price movement cannot be credited.",
            "completed_reaction_purge": "Completed reactions use their own chronological split and forward-window purge; they do not reuse forming-signal labels.",
            "target_separation": "Forming PRZ-arrival evidence and post-completion Type-I reaction evidence are separate research targets and are never treated as the same success label.",
            "network": "Provider availability is reported as evidence; network failure is not silently converted into a research conclusion.",
        },
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    COMPLETED_REACTION_PATH.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "status": "research_completed_reaction_holdout_sealed",
                "inventory": completed_inventory,
                "calibration": completed_calibration,
                "records": emitted_completed_reactions,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"[HT-CN AUTONOMOUS] coverage={len(datasets)}/{len(instruments)} "
        f"minimum={minimum_symbols}, cache={cache_hits} hit/{cache_misses} miss, "
        f"forming={len(all_records)}, completed={len(all_completed_reactions)}, "
        f"status={research_status}"
    )
    if calibration.get("status") == "research_quality_evidence_holdout_sealed":
        gate = calibration["quality_gate"]
        train = gate["baseline"]["train"]
        validation = gate["baseline"]["validation"]
        print(
            f"[HT-CN AUTONOMOUS] forming baseline train touch={train['touch_rate']:.4f}, "
            f"retire={train['retirement_rate']:.4f}; validation touch={validation['touch_rate']:.4f}, "
            f"retire={validation['retirement_rate']:.4f}"
        )
        print(
            f"[HT-CN AUTONOMOUS] forming strong_candidates={len(gate['strong_candidates'])}: "
            f"{', '.join(gate['strong_candidates']) or 'none'}"
        )
    if robustness.get("status") == "research_robustness_holdout_sealed":
        robust = robustness["robust_research_candidates"]
        print(
            f"[HT-CN AUTONOMOUS] forming robust_candidates={len(robust)}: "
            f"{', '.join(robust) or 'none'}"
        )
    if layered.get("status") == "research_layers_holdout_sealed":
        robust_layers = layered["robust_candidates_by_layer"]
        print(
            "[HT-CN AUTONOMOUS] robust semantic layers: "
            f"quality={','.join(robust_layers['quality']) or 'none'} | "
            f"readiness={','.join(robust_layers['readiness']) or 'none'} | "
            f"context={','.join(robust_layers['context']) or 'none'} | "
            f"mixed={','.join(robust_layers['mixed']) or 'none'}"
        )
        universal = layered["universal_quality_candidates"]
        print(
            f"[HT-CN AUTONOMOUS] universal_quality_candidates={len(universal)}: "
            f"{', '.join(universal) or 'none'}"
        )
        family_hypotheses = layered["family_specific_quality_hypotheses"]
        compact = "; ".join(
            f"{name}=>{','.join(values)}" for name, values in sorted(family_hypotheses.items())
        )
        print(
            "[HT-CN AUTONOMOUS] family_specific_quality_hypotheses="
            f"{compact or 'none'}"
        )

    split_counts = completed_calibration["split_counts"]
    train_reaction = completed_calibration["train"]
    validation_reaction = completed_calibration["validation"]
    print(
        "[HT-CN AUTONOMOUS] completed reaction calibration: "
        f"actionable={completed_calibration['actionable_mature_records']}, "
        f"purged={completed_calibration['purged_records']}, "
        f"train={split_counts['train']}, validation={split_counts['validation']}, "
        f"holdout={split_counts['holdout']}, status={completed_calibration['status']}"
    )
    if train_reaction["records"]:
        print(
            "[HT-CN AUTONOMOUS] completed reaction TRAIN: "
            f"T1={train_reaction['t1_rate']:.4f}, T2={train_reaction['t2_rate']:.4f}"
        )
    if validation_reaction["records"]:
        print(
            "[HT-CN AUTONOMOUS] completed reaction VALIDATION: "
            f"T1={validation_reaction['t1_rate']:.4f}, T2={validation_reaction['t2_rate']:.4f}"
        )

    print("[HT-CN AUTONOMOUS] FORMING HOLDOUT SEALED")
    print("[HT-CN AUTONOMOUS] COMPLETED-REACTION HOLDOUT SEALED")
    print(f"[HT-CN AUTONOMOUS] snapshots={SNAPSHOT_MANIFEST_PATH.relative_to(ROOT)}")
    print(f"[HT-CN AUTONOMOUS] report={REPORT_PATH.relative_to(ROOT)}")
    print(
        f"[HT-CN AUTONOMOUS] completed_reactions={COMPLETED_REACTION_PATH.relative_to(ROOT)}"
    )

    if not coverage_ok:
        print(
            f"[HT-CN AUTONOMOUS] FAIL: provider coverage {len(datasets)}/{len(instruments)} "
            f"is below required minimum {minimum_symbols}."
        )
        return 2

    print("[HT-CN AUTONOMOUS] PASS: autonomous research pipeline completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
