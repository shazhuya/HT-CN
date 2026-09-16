from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from htcn.research.autonomous_calibration import enrich_walk_forward_records
from htcn.research.terminal_bar import build_terminal_bar_calibration
from htcn.research.type_i_holdout_eval import evaluate_preregistered_type_i_holdout
from htcn.research.walk_forward import walk_forward_forming_signals


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "research" / "a-share-research-universe-v1.json"
PREREG = ROOT / "research" / "m2-type-i-holdout-prereg-v1.json"
AUTHORIZATION = ROOT / "research" / "m2-type-i-holdout-open-v1.json"
DATA_DIR = ROOT / "artifacts" / "ci-research" / "data"
OUTPUT = ROOT / "artifacts" / "ci-research" / "m2-type-i-holdout-evaluation.json"


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    authorization = json.loads(AUTHORIZATION.read_text(encoding="utf-8"))

    expected_dataset = prereg.get("dataset") or {}
    authorized_dataset = authorization.get("dataset") or {}
    if (
        manifest.get("dataset_id") != expected_dataset.get("dataset_id")
        or manifest.get("snapshot_cutoff") != expected_dataset.get("snapshot_cutoff")
        or authorized_dataset.get("dataset_id") != expected_dataset.get("dataset_id")
        or authorized_dataset.get("snapshot_cutoff") != expected_dataset.get("snapshot_cutoff")
    ):
        print("[HT-CN M2 HOLDOUT] FAIL: dataset/cutoff does not match frozen pre-registration.")
        return 2

    horizon = int(manifest.get("horizon_bars", 60))
    reaction_horizon = int(manifest.get("completed_reaction_horizon_bars", 20))
    scales = tuple(int(value) for value in manifest.get("scales", [3, 5, 8, 13, 21]))
    all_records: list[dict] = []

    for item in manifest.get("instruments") or []:
        instrument_id = str(item["instrument_id"])
        path = DATA_DIR / f"{instrument_id}.parquet"
        if not path.exists():
            print(f"[HT-CN M2 HOLDOUT] FAIL: missing pinned snapshot {path.relative_to(ROOT)}")
            return 2
        frame = pd.read_parquet(path).sort_values("trade_date").reset_index(drop=True)
        signals = walk_forward_forming_signals(frame, scales=scales, horizon=horizon)
        all_records.extend(
            enrich_walk_forward_records(
                signals,
                frame=frame,
                instrument_id=instrument_id,
                horizon=horizon,
            )
        )

    terminal_calibration = build_terminal_bar_calibration(
        all_records,
        reaction_horizon=reaction_horizon,
    )
    result = evaluate_preregistered_type_i_holdout(
        all_records,
        terminal_calibration,
        prereg,
        authorization,
        reaction_horizon=reaction_horizon,
    )
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        "[HT-CN M2 HOLDOUT] "
        f"status={result.get('status')}, opened={result.get('holdout_opened')}, "
        f"prereg={result.get('preregistration_id')}"
    )
    primary = result.get("primary_contrast") or {}
    exposure = primary.get("exposure") or {}
    comparator = primary.get("comparator") or {}
    interval = primary.get("newcombe_95_ci") or {}
    print(
        "[HT-CN M2 HOLDOUT] primary "
        f"{primary.get('exposure_name')}: n={exposure.get('records', 0)}, "
        f"hits={exposure.get('endpoint_hits', 0)}, rate={exposure.get('endpoint_rate')}; "
        f"{primary.get('comparator_name')}: n={comparator.get('records', 0)}, "
        f"hits={comparator.get('endpoint_hits', 0)}, rate={comparator.get('endpoint_rate')}"
    )
    print(
        "[HT-CN M2 HOLDOUT] effect="
        f"{primary.get('absolute_rate_difference')}, CI95=[{interval.get('lower')}, {interval.get('upper')}], "
        f"result={primary.get('result')}"
    )
    print(
        "[HT-CN M2 HOLDOUT] secondary diagnostics are descriptive only; "
        "no alternate threshold or endpoint was searched."
    )
    print(f"[HT-CN M2 HOLDOUT] report={OUTPUT.relative_to(ROOT)}")
    return 0 if result.get("status") == "type_i_holdout_evaluated_once" else 2


if __name__ == "__main__":
    raise SystemExit(main())
