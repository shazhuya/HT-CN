from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from htcn.research.quality_gate import evaluate_gate_library

ROOT = Path(__file__).resolve().parents[1]
CAL_DIR = ROOT / "artifacts" / "calibration"
SPLIT_JSON = CAL_DIR / "m2-time-split-calibration.json"
TRAIN_CSV = CAL_DIR / "m2-time-split-train.csv"
VALIDATION_CSV = CAL_DIR / "m2-time-split-validation.csv"
OUT_PATH = CAL_DIR / "m2-quality-gate-evidence.json"


def _records(path: Path) -> list[dict]:
    frame = pd.read_csv(path)
    return frame.to_dict(orient="records")


def main() -> int:
    missing = [path for path in (SPLIT_JSON, TRAIN_CSV, VALIDATION_CSV) if not path.exists()]
    if missing:
        print("[HT-CN M2 GATE] FAIL: missing time-split artifacts; run 运行M2时间切分校准.bat first.")
        return 1

    split = json.loads(SPLIT_JSON.read_text(encoding="utf-8"))
    holdout = split.get("holdout") or {}
    if not holdout.get("sealed") or holdout.get("outcomes_reported"):
        print("[HT-CN M2 GATE] FAIL: holdout is not sealed; refusing iterative gate research.")
        return 2

    thresholds = split["train_learned_thresholds"]
    train = _records(TRAIN_CSV)
    validation = _records(VALIDATION_CSV)
    horizon = int(split.get("horizon_bars", 60))
    report = evaluate_gate_library(
        train,
        validation,
        thresholds=thresholds,
        horizon=horizon,
    )
    report.update(
        {
            "schema_version": 1,
            "status": "research_quality_gate_evidence_holdout_sealed",
            "source": str(SPLIT_JSON.relative_to(ROOT)),
            "train_records": len(train),
            "validation_records": len(validation),
            "holdout_records_sealed": int(holdout.get("records", 0)),
            "scope_warning": "Do not freeze a production quality policy from a tiny symbol universe; expand QFQ coverage first and require stable Train/Validation direction.",
        }
    )
    CAL_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    train_base = report["baseline"]["train"]
    val_base = report["baseline"]["validation"]
    print(
        f"[HT-CN M2 GATE] baseline train touch={train_base['touch_rate']:.4f}, "
        f"retire={train_base['retirement_rate']:.4f}; "
        f"validation touch={val_base['touch_rate']:.4f}, retire={val_base['retirement_rate']:.4f}"
    )
    print(f"[HT-CN M2 GATE] strong_candidates={len(report['strong_candidates'])}: {', '.join(report['strong_candidates']) or 'none'}")
    for row in report["gates"][:5]:
        tr = row["train"]
        va = row["validation"]
        print(
            f"[HT-CN M2 GATE] {row['name']}: n={tr['records']}/{va['records']}, "
            f"touch={tr['touch_rate']:.4f}/{va['touch_rate']:.4f}, "
            f"retire={tr['retirement_rate']:.4f}/{va['retirement_rate']:.4f}, "
            f"strong={row['strong_candidate']}"
        )
    print("[HT-CN M2 GATE] HOLDOUT SEALED; no holdout outcomes were read.")
    print(f"[HT-CN M2 GATE] JSON: {OUT_PATH.relative_to(ROOT)}")
    print("[HT-CN M2 GATE] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
