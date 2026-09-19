from __future__ import annotations

import json
from pathlib import Path

from htcn.app.main_real_browser_audit import (
    verify_main_real_browser_evidence,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "artifacts"
    / "reports"
    / "playwright"
    / "phase21-real-delivery-browser-source.json"
)
EVIDENCE = (
    ROOT
    / "artifacts"
    / "reports"
    / "playwright"
    / "phase21-real-delivery-browser-evidence.json"
)
OUTPUT = (
    ROOT
    / "artifacts"
    / "reports"
    / "playwright"
    / "phase21-real-delivery-browser-verification.json"
)


def main() -> int:
    payload = verify_main_real_browser_evidence(
        root=ROOT,
        source_report=SOURCE,
        evidence_report=EVIDENCE,
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["status"] == "valid" else 2


if __name__ == "__main__":
    raise SystemExit(main())
