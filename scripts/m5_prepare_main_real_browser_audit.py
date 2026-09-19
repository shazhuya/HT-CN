from __future__ import annotations

import argparse
import json
from pathlib import Path

from htcn.app.main_real_browser_audit import (
    prepare_main_real_browser_source,
)

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_HTML = (
    ROOT / "apps" / "web" / "public" / "latest-real-portable-workspace.html"
)
SOURCE_REPORT = (
    ROOT
    / "artifacts"
    / "reports"
    / "playwright"
    / "phase21-real-delivery-browser-source.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.fixture:
        workspace = (
            ROOT / "apps" / "web" / "public" / "portable-visual-fixture.html"
        )
        inspection = (
            ROOT
            / "artifacts"
            / "reports"
            / "playwright"
            / "phase18-portable-visual-fixture.json"
        )
        identity = "f" * 64
        payload = prepare_main_real_browser_source(
            root=ROOT,
            workspace_source=workspace,
            inspection_source=inspection,
            output_html=PUBLIC_HTML,
            source_report=SOURCE_REPORT,
            mode="deterministic_fixture",
            trade_date="2026-09-19",
            source_identity=identity,
        )
    else:
        closeout_path = (
            ROOT / "artifacts" / "reports" / "m5-main-real-closeout.json"
        )
        pointer_path = (
            ROOT
            / "artifacts"
            / "reports"
            / "m5-daily-portable-delivery-latest.json"
        )
        closeout = json.loads(closeout_path.read_text(encoding="utf-8"))
        pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
        payload = prepare_main_real_browser_source(
            root=ROOT,
            workspace_source=pointer["workspace_html"],
            inspection_source=pointer["inspector_json"],
            output_html=PUBLIC_HTML,
            source_report=SOURCE_REPORT,
            mode="phase19_latest",
            trade_date=str(pointer["trade_date"]),
            source_identity=str(pointer["bundle_sha256"]),
            structural_closeout_status=str(closeout["status"]),
            structural_closeout_report_sha256=__import__("hashlib").sha256(
                closeout_path.read_bytes()
            ).hexdigest(),
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
