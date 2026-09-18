from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from htcn.research.lifecycle_journal import read_journal
from htcn.research.prospective_observations import build_prospective_observation_report
from htcn.research.snapshot_manifest import read_snapshot_manifest


def render_markdown(payload: dict[str, Any]) -> str:
    interpretation = payload.get("interpretation") or {}
    lines = [
        "# HT-CN M4 Prospective Observation 报告",
        "",
        f"- 状态：**{payload.get('status')}**",
        f"- Capture dates：{len(payload.get('captured_dates') or [])}",
        f"- Prospective candidates：{payload.get('prospective_candidate_count', 0)}",
        f"- Observation rows：{payload.get('observation_count', 0)}",
        f"- Timeline source：`{interpretation.get('capture_timeline_source', 'journal_fallback')}`",
        "",
        "## Scanner presence",
        "",
    ]
    presence = payload.get("scanner_presence_counts") or {}
    if presence:
        for key, value in sorted(presence.items()):
            lines.append(f"- `{key}`：{value}")
    else:
        lines.append("- 当前没有 prospective outcome cohort。")

    lines.extend(["", "## Lifecycle observations", ""])
    states = payload.get("lifecycle_observation_counts") or {}
    if states:
        for key, value in sorted(states.items()):
            lines.append(f"- `{key}`：{value}")
    else:
        lines.append("- 当前没有 lifecycle observation。")

    lines.extend(["", "## Candidate summaries", ""])
    summaries = payload.get("candidate_summaries") or []
    if summaries:
        for item in summaries:
            lines.append(
                f"- `{item.get('candidate_key')}`：enroll={item.get('outcome_enrollment_trade_date')}；"
                f"captured={item.get('captured_snapshot_count')}；present={item.get('present_snapshot_count')}；"
                f"absent={item.get('absent_snapshot_count')}；terminal={item.get('first_source_terminal_trade_date')}"
            )
    else:
        lines.append("- 无。")

    lines.extend([
        "",
        "## 固定解释边界",
        "",
        "- captured_snapshot_index 只是实际捕获序号，不是假定完整交易日序号。",
        "- scanner absent 不等于 invalidated。",
        "- 本报告只保留事实 observation 和 milestone。",
        "- 不计算 return / profit / win rate / alpha。",
        "- 不定义盈利阈值或买卖评分。",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build M4 prospective observation panel from journal + capture manifest."
    )
    parser.add_argument(
        "--journal",
        default="data/research/m4/lifecycle_journal.jsonl",
    )
    parser.add_argument(
        "--manifest",
        default="data/research/m4/snapshot_manifest.jsonl",
    )
    parser.add_argument(
        "--output",
        default="artifacts/reports/m4-prospective-observations.json",
    )
    args = parser.parse_args()

    rows = read_journal(Path(args.journal))
    manifest_path = Path(args.manifest)
    manifest_rows = (
        read_snapshot_manifest(manifest_path)
        if manifest_path.exists()
        else []
    )
    payload = build_prospective_observation_report(
        rows,
        manifest_rows=manifest_rows,
    )
    payload["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    payload["journal_path"] = str(args.journal)
    payload["manifest_path"] = str(args.manifest)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown = output.with_suffix(".md")
    markdown.write_text(render_markdown(payload), encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\n[M4] prospective observation report: {output}")
    print(f"[M4] human-readable report: {markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
