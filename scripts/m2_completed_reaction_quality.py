from __future__ import annotations

import argparse
import json
from pathlib import Path

from htcn.research.completed_reaction_quality import build_completed_reaction_quality_report


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "artifacts" / "ci-research" / "m2-confirmed-completed-reactions.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "ci-research" / "m2-completed-reaction-quality.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Train/Validation completed-reaction quality evidence from the redacted artifact"
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    calibration = payload.get("calibration") or {}
    records = payload.get("records") or []

    report = build_completed_reaction_quality_report(records, calibration)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    baseline = report.get("baseline") or {}
    train = baseline.get("train") or {}
    validation = baseline.get("validation") or {}
    print(
        "[HT-CN M2 REACTION QUALITY] "
        f"status={report['status']}, "
        f"train={train.get('records', 0)}, validation={validation.get('records', 0)}, "
        f"holdout={report['holdout'].get('records', 0)} SEALED"
    )
    if report.get("status") == "completed_reaction_quality_evidence_holdout_sealed":
        print(
            "[HT-CN M2 REACTION QUALITY] baseline "
            f"train T1={train.get('t1_rate'):.4f}, T2={train.get('t2_rate'):.4f}; "
            f"validation T1={validation.get('t1_rate'):.4f}, T2={validation.get('t2_rate'):.4f}"
        )
        print(
            "[HT-CN M2 REACTION QUALITY] consistent_t1="
            f"{','.join(report['consistent_t1_candidates']) or 'none'}"
        )
        print(
            "[HT-CN M2 REACTION QUALITY] t2_corroborated="
            f"{','.join(report['t2_corroborated_candidates']) or 'none'}"
        )
    else:
        print(
            "[HT-CN M2 REACTION QUALITY] research not opened: "
            f"{report.get('reason') or 'insufficient sample'}"
        )
    print("[HT-CN M2 REACTION QUALITY] COMPLETED-REACTION HOLDOUT SEALED")
    print(f"[HT-CN M2 REACTION QUALITY] report={args.output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
