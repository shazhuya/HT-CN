from __future__ import annotations

import json
from pathlib import Path

from htcn.app.daily_handoff_v3_runner import run_daily_handoff_bundle_v3


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_REPORT = ROOT / "artifacts" / "reports" / "m5-daily-close-pipeline.json"
OUTPUT = ROOT / "artifacts" / "reports" / "htcn-daily-handoff-v3.zip"
REPORT = ROOT / "artifacts" / "reports" / "m5-daily-handoff-v3.json"


def main() -> int:
    print(
        "[HT-CN M5 HANDOFF V3] building versioned review-state transport...",
        flush=True,
    )
    payload, code = run_daily_handoff_bundle_v3(
        root=ROOT,
        pipeline_report=PIPELINE_REPORT,
        output=OUTPUT,
        report=REPORT,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    if code == 0:
        print(
            f"[HT-CN M5 HANDOFF V3] READY -> {OUTPUT.relative_to(ROOT)}",
            flush=True,
        )
    else:
        print(
            "[HT-CN M5 HANDOFF V3] TRANSPORT FAILED; "
            "Phase 9/11/12 readiness remains unchanged and v2 is untouched. "
            f"See {REPORT.relative_to(ROOT)}",
            flush=True,
        )
    return int(code)


if __name__ == "__main__":
    raise SystemExit(main())
