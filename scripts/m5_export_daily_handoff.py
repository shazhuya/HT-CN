from __future__ import annotations

import json
from pathlib import Path

from htcn.app.daily_handoff import build_daily_handoff_bundle


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "artifacts" / "reports" / "m5-daily-close-pipeline.json"
OUTPUT = ROOT / "artifacts" / "reports" / "htcn-daily-handoff.zip"


def main() -> int:
    if not REPORT.is_file():
        print(f"[HT-CN HANDOFF] missing pipeline report: {REPORT}")
        return 2
    try:
        payload = json.loads(REPORT.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("pipeline report must be a JSON object")
        result = build_daily_handoff_bundle(
            root=ROOT,
            pipeline_summary=payload,
            output=OUTPUT,
        )
    except Exception as exc:
        print(f"[HT-CN HANDOFF] FAILED: {type(exc).__name__}: {exc}")
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n[HT-CN HANDOFF] ready: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
