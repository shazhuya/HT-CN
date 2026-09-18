from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from htcn.research.evidence_health import build_evidence_chain_health


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# HT-CN M4 Evidence Chain Health",
        "",
        f"- 状态：**{payload.get('status')}**",
        f"- 权威证据：`{payload.get('authoritative_evidence_source')}`",
        f"- Frozen baseline through：`{payload.get('frozen_legacy_baseline_through_trade_date')}`",
        f"- Committed captures：{payload.get('committed_capture_count', 0)}",
        f"- Latest committed date：`{payload.get('latest_committed_capture_date')}`",
        f"- Hard blockers：{payload.get('blocker_count', 0)}",
        f"- Warnings：{payload.get('warning_count', 0)}",
        f"- Transition evidence ready：**{payload.get('transition_evidence_chain_ready')}**",
        "",
        "## Blockers",
        "",
    ]
    blockers = payload.get("blockers") or []
    if blockers:
        for item in blockers:
            lines.append(f"- **{item.get('code')}**：{item.get('detail')}")
    else:
        lines.append("- 无。")
    lines.extend(["", "## Warnings", ""])
    warnings = payload.get("warnings") or []
    if warnings:
        for item in warnings:
            lines.append(f"- **{item.get('code')}**：{item.get('detail')}")
    else:
        lines.append("- 无。")
    mirror = payload.get("mirror_integrity") or {}
    lines.extend([
        "",
        "## Compatibility mirrors",
        "",
        f"- Journal：`{mirror.get('journal_mirror_status')}`",
        f"- Manifest：`{mirror.get('manifest_mirror_status')}`",
        f"- Repair needed：{mirror.get('repair_needed')}",
        "",
        "## 固定边界",
        "",
        "- compatibility mirror 不是权威证据。",
        "- 本报告不使用综合评分。",
        "- 本报告不产生 alpha / 胜率 / 买卖指令。",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect M4 authoritative evidence-chain health.")
    parser.add_argument("--transaction-root", default="data/research/m4/captures")
    parser.add_argument("--journal", default="data/research/m4/lifecycle_journal.jsonl")
    parser.add_argument("--manifest", default="data/research/m4/snapshot_manifest.jsonl")
    parser.add_argument("--output", default="artifacts/reports/m4-evidence-health.json")
    args = parser.parse_args()
    payload = build_evidence_chain_health(
        transaction_root=Path(args.transaction_root),
        journal_path=Path(args.journal),
        manifest_path=Path(args.manifest),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    output.with_suffix(".md").write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("blocker_count", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
