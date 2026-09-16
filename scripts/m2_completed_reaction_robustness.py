from __future__ import annotations

import argparse
import json
from pathlib import Path

from htcn.research.completed_reaction_robustness import build_completed_reaction_robustness_report


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "artifacts" / "ci-research" / "m2-confirmed-completed-reactions.json"
DEFAULT_QUALITY = ROOT / "artifacts" / "ci-research" / "m2-completed-reaction-quality.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "ci-research" / "m2-completed-reaction-robustness.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stress-test completed-reaction quality evidence while Holdout remains sealed"
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--quality", type=Path, default=DEFAULT_QUALITY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    quality = json.loads(args.quality.read_text(encoding="utf-8"))
    report = build_completed_reaction_robustness_report(
        payload.get("records") or [],
        payload.get("calibration") or {},
        quality,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        "[HT-CN M2 REACTION ROBUST] "
        f"status={report['status']}, candidates={len(report.get('candidates_in', []))}, "
        f"robust={len(report.get('robust_candidates', []))}, "
        f"holdout={report['holdout'].get('records', 0)} SEALED"
    )
    for gate in report.get("gates", []):
        blockers = ",".join(gate.get("blockers") or []) or "none"
        alias = gate.get("semantic_alias") or {}
        print(
            "[HT-CN M2 REACTION ROBUST] "
            f"{gate['name']}: robust={gate['robust_research_candidate']}, "
            f"effective_layer={gate['effective_layer']}, "
            f"scale_alias={alias.get('is_scale_alias', False)}, blockers={blockers}"
        )
    print(
        "[HT-CN M2 REACTION ROBUST] robust_candidates="
        f"{','.join(report.get('robust_candidates', [])) or 'none'}"
    )
    print("[HT-CN M2 REACTION ROBUST] COMPLETED-REACTION HOLDOUT SEALED")
    print(f"[HT-CN M2 REACTION ROBUST] report={args.output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
