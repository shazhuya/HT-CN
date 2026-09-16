from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "artifacts" / "ci-research" / "m2-autonomous-research-report.json"
OUTPUT = ROOT / "artifacts" / "ci-research" / "m2-type-i-exit-timing.json"


def _rate(value) -> str:
    return "n/a" if value is None else f"{float(value):.4f}"


def main() -> int:
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    report = ((payload.get("calibration") or {}).get("type_i_exit_timing") or {})
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        "[HT-CN M2 TYPE-I TIMING] "
        f"status={report.get('status')}, selected={report.get('selected_hypothesis') or 'none'}, "
        f"holdout={(report.get('holdout') or {}).get('records', 0)} SEALED"
    )
    for split_name in ("train", "validation"):
        split = report.get(split_name) or {}
        groups = split.get("groups") or {}
        comparisons = split.get("comparisons") or {}
        print(
            f"[HT-CN M2 TYPE-I TIMING] {split_name.upper()} "
            f"fast_n={(groups.get('exit_by_t3') or {}).get('pending_records', 0)} "
            f"fast={_rate((groups.get('exit_by_t3') or {}).get('later_t2_rate'))}; "
            f"late_n={(groups.get('exit_on_t4_t5') or {}).get('pending_records', 0)} "
            f"late={_rate((groups.get('exit_on_t4_t5') or {}).get('later_t2_rate'))}; "
            f"noexit_n={(groups.get('no_full_exit_by_t5') or {}).get('pending_records', 0)} "
            f"noexit={_rate((groups.get('no_full_exit_by_t5') or {}).get('later_t2_rate'))}; "
            f"fast-late={_rate(comparisons.get('fast_minus_late'))}; "
            f"late-noexit={_rate(comparisons.get('late_minus_no_exit'))}"
        )
    checks = report.get("decision_checks") or {}
    print(
        "[HT-CN M2 TYPE-I TIMING] checks="
        f"floor={checks.get('exclusive_sample_floor_ok')}, "
        f"speed={checks.get('speed_advantage_fast_over_late_in_both_visible_splits')}, "
        f"late_value={checks.get('late_exit_beats_no_exit_in_both_visible_splits')}, "
        f"pooled_value={checks.get('pooled_exit_by_t5_beats_no_exit_in_both_visible_splits')}"
    )
    print("[HT-CN M2 TYPE-I TIMING] HOLDOUT SEALED")
    print(f"[HT-CN M2 TYPE-I TIMING] report={OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
