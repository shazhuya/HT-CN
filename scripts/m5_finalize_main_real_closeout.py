from __future__ import annotations

import json
from pathlib import Path

from htcn.app.main_real_browser_audit import finalize_main_real_closeout

ROOT = Path(__file__).resolve().parents[1]
STRUCTURAL = ROOT / "artifacts" / "reports" / "m5-main-real-closeout.json"
BROWSER = (
    ROOT
    / "artifacts"
    / "reports"
    / "playwright"
    / "phase21-real-delivery-browser-verification.json"
)
OUTPUT = ROOT / "artifacts" / "reports" / "m5-main-real-closeout-final.json"


def main() -> int:
    structural = json.loads(STRUCTURAL.read_text(encoding="utf-8"))
    browser = json.loads(BROWSER.read_text(encoding="utf-8"))
    payload = finalize_main_real_closeout(
        structural_report=structural,
        browser_verification=browser,
    )
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["full_closeout_ready"] is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
