from __future__ import annotations

import argparse
import hashlib
import json
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
from htcn.research.quality_robustness import build_quality_robustness_report
from htcn.research.walk_forward import walk_forward_forming_signals


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "research" / "a-share-research-universe-v1.json"
OUT_DIR = ROOT / "artifacts" / "ci-research"
DATA_DIR = OUT_DIR / "data"
REPORT_PATH = OUT_DIR / "m2-autonomous-research-report.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run autonomous real-A-share calibration in CI")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--max-symbols", type=int, default=0)
    return parser.parse_args()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_manifest(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not payload.get("instruments"):
        raise ValueError("research manifest has no instruments")
    return payload


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
    scales = tuple(int(value) for value in manifest.get("scales", [3, 5, 8, 13, 21]))
    minimum_symbols = int(manifest.get("minimum_successful_symbols", 6))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    providers = [AkShareProvider(), BaoStockProvider()]
    all_records: list[dict] = []
    datasets: list[dict] = []
    failures: list[dict] = []

    print(
        f"[HT-CN AUTONOMOUS] real-A-share research: symbols={len(instruments)}, "
        f"window={start}..{end}, bars<={max_bars}, horizon={horizon}, scales={scales}"
    )

    for position, item in enumerate(instruments, start=1):
        instrument_id = str(item["instrument_id"])
        try:
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
            if len(frame) < 120:
                raise RuntimeError(f"too few QFQ bars: {len(frame)}")

            snapshot_path = DATA_DIR / f"{instrument_id}.parquet"
            frame.to_parquet(snapshot_path, index=False)
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
            all_records.extend(enriched)
            datasets.append(
                {
                    "instrument_id": instrument_id,
                    "name": item.get("name"),
                    "bucket": item.get("bucket"),
                    "source": fetched.source,
                    "attempts": fetched.attempts,
                    "bars": len(frame),
                    "first_trade_date": pd.Timestamp(frame.iloc[0]["trade_date"]).date().isoformat(),
                    "last_trade_date": pd.Timestamp(frame.iloc[-1]["trade_date"]).date().isoformat(),
                    "signals": len(symbol_records),
                    "snapshot": str(snapshot_path.relative_to(ROOT)),
                    "sha256": _sha256(snapshot_path),
                }
            )
            print(
                f"[HT-CN AUTONOMOUS] {position}/{len(instruments)} OK {instrument_id}: "
                f"source={fetched.source}, bars={len(frame)}, signals={len(symbol_records)}"
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
    research_status = (
        "calibration_complete"
        if coverage_ok
        and calibration.get("status") == "research_quality_evidence_holdout_sealed"
        and robustness.get("status") == "research_robustness_holdout_sealed"
        else "insufficient_provider_or_sample_coverage"
    )
    report = {
        "schema_version": 2,
        "status": research_status,
        "dataset_id": manifest.get("dataset_id"),
        "snapshot_cutoff": manifest.get("snapshot_cutoff"),
        "requested_symbols": len(instruments),
        "successful_symbols": len(datasets),
        "minimum_successful_symbols": minimum_symbols,
        "coverage_ok": coverage_ok,
        "datasets": datasets,
        "failures": failures,
        "signals": len(all_records),
        "calibration": calibration,
        "robustness": robustness,
        "methodology": {
            "runtime": "GitHub Actions / CI-accessible; no user workstation data is required.",
            "source": "Provider QFQ is used only for research calibration snapshots, separate from production raw+factor storage.",
            "determinism": "Snapshot cutoff and universe are pinned; provider restatements are detectable through per-file SHA256.",
            "holdout": "Holdout outcomes remain sealed during iterative quality-gate and robustness research.",
            "identity": "Carney geometry/identity is frozen and never fitted to later outcomes.",
            "robustness": "Strong gates are stress-tested across symbols, leave-one-symbol-out and coarse time segments before any policy freeze.",
            "network": "Provider availability is reported as evidence; network failure is not silently converted into a research conclusion.",
        },
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        f"[HT-CN AUTONOMOUS] coverage={len(datasets)}/{len(instruments)} "
        f"minimum={minimum_symbols}, signals={len(all_records)}, status={research_status}"
    )
    if calibration.get("status") == "research_quality_evidence_holdout_sealed":
        gate = calibration["quality_gate"]
        train = gate["baseline"]["train"]
        validation = gate["baseline"]["validation"]
        print(
            f"[HT-CN AUTONOMOUS] baseline train touch={train['touch_rate']:.4f}, "
            f"retire={train['retirement_rate']:.4f}; validation touch={validation['touch_rate']:.4f}, "
            f"retire={validation['retirement_rate']:.4f}"
        )
        print(
            f"[HT-CN AUTONOMOUS] strong_candidates={len(gate['strong_candidates'])}: "
            f"{', '.join(gate['strong_candidates']) or 'none'}"
        )
    if robustness.get("status") == "research_robustness_holdout_sealed":
        robust = robustness["robust_research_candidates"]
        print(
            f"[HT-CN AUTONOMOUS] robust_candidates={len(robust)}: "
            f"{', '.join(robust) or 'none'}"
        )
    print("[HT-CN AUTONOMOUS] HOLDOUT SEALED")
    print(f"[HT-CN AUTONOMOUS] report={REPORT_PATH.relative_to(ROOT)}")
    print("[HT-CN AUTONOMOUS] PASS: autonomous research pipeline completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
