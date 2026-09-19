from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from htcn.research.baseline_audit import audit_t0_baseline
from htcn.research.lifecycle_journal import read_journal


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# HT-CN M4 T0 基线质量审计",
        "",
        f"- 状态：**{payload.get('status')}**",
        f"- T0 交易日：`{payload.get('baseline_trade_date')}`",
        f"- Journal 行数：{payload.get('journal_row_count', 0)}",
        f"- 唯一候选：{payload.get('unique_candidate_count', 0)}",
        f"- 候选覆盖标的：{payload.get('candidate_bearing_instrument_count', 0)}",
        f"- Hard blockers：{payload.get('blocker_count', 0)}",
        f"- Warnings：{payload.get('warning_count', 0)}",
        f"- T1 transition ready：**{payload.get('transition_ready')}**",
        f"- Prospective outcome ready：**{payload.get('prospective_outcome_ready')}**",
        "",
        "## Hard blockers",
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

    for title, field in [
        ("Pattern", "pattern_counts"),
        ("Schema", "schema_counts"),
        ("Direction", "direction_counts"),
        ("Scale", "scale_counts"),
        ("Source Lifecycle", "lifecycle_counts"),
        ("Action State", "action_counts"),
        ("Source Terminal 年龄", "source_terminal_age_buckets"),
    ]:
        lines.extend(["", f"## {title}", ""])
        values = payload.get(field) or {}
        if values:
            for key, value in values.items():
                lines.append(f"- `{key}`：{value}")
        else:
            lines.append("- 无。")

    lines.extend([
        "",
        "## Readiness 边界",
        "",
        f"- T1 transition：{payload.get('transition_ready')}",
        f"- Prospective outcome：{payload.get('prospective_outcome_ready')}",
        f"- 原因：{payload.get('prospective_outcome_reason')}",
        "- 本审计不使用综合评分。",
        "- 本审计不产生 alpha / 胜率 / 买卖结论。",
        "- T0 baseline 不进入 prospective outcome cohort。",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit M4 T0 lifecycle baseline.")
    parser.add_argument(
        "--journal",
        default="data/research/m4/lifecycle_journal.jsonl",
    )
    parser.add_argument(
        "--snapshot",
        default="artifacts/reports/m4-lifecycle-snapshot.json",
    )
    parser.add_argument(
        "--output",
        default="artifacts/reports/m4-t0-baseline-audit.json",
    )
    args = parser.parse_args()

    rows = read_journal(Path(args.journal))
    snapshot_path = Path(args.snapshot)
    snapshot = (
        json.loads(snapshot_path.read_text(encoding="utf-8"))
        if snapshot_path.exists()
        else None
    )
    payload = audit_t0_baseline(rows, snapshot=snapshot)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown = output.with_suffix(".md")
    markdown.write_text(render_markdown(payload), encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\n[M4] T0 audit: {output}")
    print(f"[M4] human-readable audit: {markdown}")
    return 0 if payload.get("blocker_count") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
