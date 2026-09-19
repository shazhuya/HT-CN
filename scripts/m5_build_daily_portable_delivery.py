from __future__ import annotations

import json
from pathlib import Path

from htcn.app.daily_portable_delivery import run_daily_portable_delivery

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "artifacts" / "reports"


def main() -> int:
    payload, code = run_daily_portable_delivery(
        root=ROOT,
        pipeline_report=REPORTS / "m5-daily-close-pipeline.json",
        output=REPORTS / "htcn-daily-portable-delivery-v1.zip",
        run_report=REPORTS / "m5-daily-portable-delivery-run.json",
        latest_pointer=REPORTS / "m5-daily-portable-delivery-latest.json",
        latest_v4_alias=REPORTS / "m5-daily-portable-v4.zip",
        latest_inspector_alias=(
            REPORTS / "m5-daily-portable-inspector.json"
        ),
        latest_workspace_alias=(
            REPORTS / "m5-daily-portable-workspace.html"
        ),
        archive_root=ROOT / "artifacts" / "deliveries" / "m5",
        bars=420,
        scales=(3, 5, 8, 13),
    )
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        ),
        flush=True,
    )
    if code == 0:
        print(
            "[HT-CN M5 PHASE19] portable delivery READY -> "
            "artifacts/reports/htcn-daily-portable-delivery-v1.zip",
            flush=True,
        )
        print(
            "[HT-CN M5 PHASE19] open -> "
            "artifacts/reports/m5-daily-portable-workspace.html",
            flush=True,
        )
    else:
        print(
            "[HT-CN M5 PHASE19] delivery failed. "
            "Previous successful latest pointer/archive remain authoritative. "
            "See artifacts/reports/m5-daily-portable-delivery-run.json",
            flush=True,
        )
    return int(code)


if __name__ == "__main__":
    raise SystemExit(main())
