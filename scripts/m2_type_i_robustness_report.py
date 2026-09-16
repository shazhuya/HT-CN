from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "artifacts" / "ci-research" / "m2-autonomous-research-report.json"
OUTPUT = ROOT / "artifacts" / "ci-research" / "m2-type-i-early-path-robustness.json"


def _rate(value) -> str:
    return "n/a" if value is None else f"{float(value):.4f}"


def main() -> int:
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    report = ((payload.get("calibration") or {}).get("type_i_early_path_robustness") or {})
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        "[HT-CN M2 TYPE-I ROBUST] "
        f"status={report.get('status')}, candidates={len(report.get('candidates_in') or [])}, "
        f"robust={len(report.get('robust_candidates') or [])}, "
        f"holdout={(report.get('holdout') or {}).get('records', 0)} SEALED"
    )
    for row in report.get("cohorts") or []:
        train = row.get("train") or {}
        validation = row.get("validation") or {}
        print(
            "[HT-CN M2 TYPE-I ROBUST] "
            f"{row.get('name')}: robust={row.get('robust_research_candidate')}, "
            f"train_n={(train.get('gated') or {}).get('pending_records', 0)}, "
            f"train_lift={_rate(train.get('later_t2_lift'))}, "
            f"validation_n={(validation.get('gated') or {}).get('pending_records', 0)}, "
            f"validation_lift={_rate(validation.get('later_t2_lift'))}, "
            f"blockers={','.join(row.get('blockers') or []) or 'none'}"
        )
    print(
        "[HT-CN M2 TYPE-I ROBUST] robust_candidates="
        f"{','.join(report.get('robust_candidates') or []) or 'none'}"
    )
    print("[HT-CN M2 TYPE-I ROBUST] HOLDOUT SEALED")
    print(f"[HT-CN M2 TYPE-I ROBUST] report={OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
