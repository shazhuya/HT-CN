from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "artifacts" / "ci-research" / "m2-autonomous-research-report.json"
OUTPUT = ROOT / "artifacts" / "ci-research" / "m2-type-i-early-path.json"


def _rate(value) -> str:
    return "n/a" if value is None else f"{float(value):.4f}"


def main() -> int:
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    report = ((payload.get("calibration") or {}).get("type_i_early_path") or {})
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    baseline = report.get("baseline") or {}
    train = baseline.get("train") or {}
    validation = baseline.get("validation") or {}
    holdout = report.get("holdout") or {}
    counts = report.get("split_counts") or {}
    print(
        "[HT-CN M2 TYPE-I] "
        f"status={report.get('status')}, landmark=T+{report.get('landmark_bar')}, "
        f"train={counts.get('train', 0)}, validation={counts.get('validation', 0)}, "
        f"holdout={counts.get('holdout', 0)} SEALED"
    )
    if train or validation:
        print(
            "[HT-CN M2 TYPE-I] TRAIN "
            f"earlyT1={_rate(train.get('early_t1_rate'))}, earlyT2={_rate(train.get('early_t2_rate'))}, "
            f"pending-T2 later={_rate(train.get('t2_after_landmark_rate_among_pending'))}"
        )
        print(
            "[HT-CN M2 TYPE-I] VALIDATION "
            f"earlyT1={_rate(validation.get('early_t1_rate'))}, earlyT2={_rate(validation.get('early_t2_rate'))}, "
            f"pending-T2 later={_rate(validation.get('t2_after_landmark_rate_among_pending'))}"
        )
        for cohort in report.get("cohorts") or []:
            train_row = cohort.get("train") or {}
            validation_row = cohort.get("validation") or {}
            print(
                "[HT-CN M2 TYPE-I] cohort="
                f"{cohort.get('name')} train_n={train_row.get('records', 0)} "
                f"train_pendingT2_later={_rate(train_row.get('t2_after_landmark_rate_among_pending'))} "
                f"validation_n={validation_row.get('records', 0)} "
                f"validation_pendingT2_later={_rate(validation_row.get('t2_after_landmark_rate_among_pending'))}"
            )
    print(
        "[HT-CN M2 TYPE-I] HOLDOUT SEALED: outcome statistics intentionally not opened; "
        f"records={holdout.get('records', 0)}"
    )
    print(f"[HT-CN M2 TYPE-I] report={OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
