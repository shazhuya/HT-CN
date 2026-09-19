from __future__ import annotations

import argparse
import json
from pathlib import Path

from htcn.app.handoff_v4_inspector import write_portable_pattern_workspace
from htcn.app.handoff_v4_portable_detail import build_daily_handoff_bundle_v4
from htcn.app.operator_input_identity import (
    build_analysis_code_identity,
    build_operator_cache_input_identity,
)
from htcn.app.source_clock_lifecycle_service import M3SourceClockHarmonicService

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "market"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="HT-CN M5 Phase 16: build verified v4 portable pattern detail and visual workspace."
    )
    parser.add_argument(
        "--v3-bundle",
        default="artifacts/reports/htcn-daily-handoff-v3.zip",
    )
    parser.add_argument(
        "--v4-output",
        default="artifacts/reports/htcn-daily-handoff-v4.zip",
    )
    parser.add_argument(
        "--json-output",
        default="artifacts/reports/m5-handoff-v4-inspector.json",
    )
    parser.add_argument(
        "--html-output",
        default="artifacts/reports/m5-handoff-v4-pattern-workspace.html",
    )
    parser.add_argument("--bars", type=int, default=420)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    analysis_identity = build_analysis_code_identity(project_root=ROOT)
    input_identity = build_operator_cache_input_identity(
        data_root=DATA_ROOT,
        project_root=ROOT,
        analysis_code_identity=analysis_identity,
    )
    service = M3SourceClockHarmonicService(DATA_ROOT)
    built = build_daily_handoff_bundle_v4(
        v3_bundle=args.v3_bundle,
        analysis_provider=service,
        current_input_identity_fingerprint=input_identity.fingerprint,
        output=args.v4_output,
        bars=args.bars,
        scales=(3, 5, 8, 13),
    )
    workspace = write_portable_pattern_workspace(
        bundle_path=args.v4_output,
        json_output=args.json_output,
        html_output=args.html_output,
    )
    print(
        json.dumps(
            {
                "handoff_v4": built,
                "workspace": workspace,
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
