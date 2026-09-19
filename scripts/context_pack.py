from __future__ import annotations

import argparse
import sys
from pathlib import Path

from project_state import ROOT, build_resume_pack, validate

DEFAULT_OUTPUT = ROOT / "logs" / "context" / "HTCN_CONTEXT_PACK.md"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build/check HT-CN Project OS v2 dynamic resume pack"
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    ok, errors, warnings, state = validate()
    print("[HT-CN CONTEXT] Project OS v2 continuity check")
    for warning in warnings:
        print(f"[HT-CN CONTEXT] WARN: {warning}")
    for error in errors:
        print(f"[HT-CN CONTEXT] FATAL: {error}")
    if not ok:
        return 2
    if args.check:
        print("[HT-CN CONTEXT] CHECK PASSED")
        return 0

    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_resume_pack(state), encoding="utf-8")
    print(f"[HT-CN CONTEXT] dynamic resume pack written: {output}")
    print("[HT-CN CONTEXT] Active specs/decisions/issues were derived from PROJECT_STATE.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
