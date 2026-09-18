from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from htcn.research.capture_transaction import (
    committed_capture_view,
    frozen_legacy_baseline_present,
    frozen_legacy_baseline_through_date,
    read_committed_captures,
    read_frozen_legacy_baseline,
)
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
        f"- Methodology fingerprint：`{payload.get('methodology_fingerprint')}`",
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

    lines.extend(["", "## Market observation", ""])
    market = payload.get("market_observation_counts") or {}
    if market:
        for key, value in sorted(market.items()):
            lines.append(f"- `{key}`：{value}")
    else:
        lines.append("- 当前没有 market observation。")

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
                f"absent={item.get('absent_snapshot_count')}；"
                f"suspended={item.get('confirmed_full_day_suspended_snapshot_count', 0)}；"
                f"terminal={item.get('first_source_terminal_trade_date')}"
            )
    else:
        lines.append("- 无。")

    lines.extend([
        "",
        "## 固定解释边界",
        "",
        "- captured_snapshot_index 只是实际捕获序号，不是假定完整交易日序号。",
        "- scanner absent 不等于 invalidated。",
        "- 确认全天停牌 carry-forward 仍是 candidate present，但不是 traded observation。",
        "- 停牌 carry-forward 不伪造当日 OHLC，也不能作为首次 prospective outcome enrollment。",
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
        "--transaction-root",
        default="data/research/m4/captures",
    )
    parser.add_argument(
        "--output",
        default="artifacts/reports/m4-prospective-observations.json",
    )
    args = parser.parse_args()

    transaction_root = Path(args.transaction_root)
    committed = read_committed_captures(transaction_root)
    if committed:
        if not frozen_legacy_baseline_present(transaction_root):
            raise RuntimeError(
                "committed capture transactions exist but frozen legacy baseline marker is missing"
            )
        frozen_baseline = read_frozen_legacy_baseline(transaction_root)
        baseline_through = frozen_legacy_baseline_through_date(transaction_root)
        rows, manifest_rows = committed_capture_view(
            legacy_journal_rows=frozen_baseline,
            capture_rows=committed,
        )
        evidence_source = "frozen_baseline_plus_committed_transactions"
    else:
        rows = read_journal(Path(args.journal))
        manifest_path = Path(args.manifest)
        manifest_rows = (
            read_snapshot_manifest(manifest_path)
            if manifest_path.exists()
            else []
        )
        evidence_source = "legacy_journal_manifest"
    payload = build_prospective_observation_report(
        rows,
        manifest_rows=manifest_rows,
        legacy_baseline_trade_date=(
            baseline_through if committed else None
        ),
    )
    payload["evidence_source"] = evidence_source
    payload["methodology_contract_version"] = (
        committed[0].get("methodology_contract_version")
        if committed
        else None
    )
    payload["methodology_fingerprint"] = (
        committed[0].get("methodology_fingerprint")
        if committed
        else None
    )
    payload["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    payload["journal_path"] = str(args.journal)
    payload["manifest_path"] = str(args.manifest)
    payload["transaction_root"] = str(args.transaction_root)

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
