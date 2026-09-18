from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from htcn.research.capture_transaction import (
    committed_capture_view,
    read_committed_captures,
    read_frozen_legacy_baseline,
)
from htcn.research.lifecycle_journal import read_journal
from htcn.research.lifecycle_transitions import build_transition_report
from htcn.research.snapshot_manifest import read_snapshot_manifest, resolve_capture_timeline


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# HT-CN M4 生命周期迁移报告",
        "",
        f"- 状态：**{payload.get('status')}**",
        f"- 基线交易日：`{payload.get('baseline_trade_date')}`",
        f"- 最新交易日：`{payload.get('latest_trade_date')}`",
        f"- 日志交易日数量：{payload.get('date_count', 0)}",
        f"- Journal 行数：{payload.get('journal_row_count', 0)}",
        f"- 最新候选数：{payload.get('latest_candidate_count', 0)}",
        f"- Prospective outcome eligible 行数：{payload.get('prospective_outcome_eligible_row_count', 0)}",
        f"- Capture timeline：`{(payload.get('capture_timeline') or {}).get('source', 'journal_fallback')}`",
        "",
        "## Cohort",
        "",
    ]
    cohorts = payload.get("cohort_counts") or {}
    if cohorts:
        for key, value in sorted(cohorts.items()):
            lines.append(f"- `{key}`：{value}")
    else:
        lines.append("- 无。")

    lines.extend(["", "## Transition", ""])
    transitions = payload.get("transition_counts") or {}
    if transitions:
        for key, value in sorted(transitions.items()):
            lines.append(f"- `{key}`：{value}")
    else:
        lines.append("- 当前还没有跨交易日迁移。")

    lines.extend(["", "## 最新 Source Lifecycle 分布", ""])
    states = payload.get("latest_lifecycle_state_counts") or {}
    if states:
        for key, value in sorted(states.items()):
            lines.append(f"- `{key}`：{value}")
    else:
        lines.append("- 无。")

    pairs = payload.get("lifecycle_pair_counts") or {}
    lines.extend(["", "## 已观察到的 Lifecycle 状态变化", ""])
    if pairs:
        for key, value in sorted(pairs.items()):
            lines.append(f"- `{key}`：{value}")
    else:
        lines.append("- 当前没有可比较的跨交易日 lifecycle change。")

    lines.extend([
        "",
        "## 固定解释边界",
        "",
        "- `scanner_disappeared` 只表示该候选下一快照未被 scanner 返回，**不等于 invalidated**。",
        "- 不使用线性 lifecycle 排名，因此不会把分叉状态强行解释成‘升级/降级’。",
        "- `baseline_existing` 不是从 formation 开始的 prospective 样本。",
        "- 只有 T0 之后首次出现的 `prospective_new` 才属于真正新入组候选。",
        "- 只有 prospective_outcome_eligible=true 的记录才允许进入未来 outcome protocol；T0 baseline 永远排除。",
        "- 本报告不计算胜率、收益率、alpha 或交易评分。",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a derived M4 lifecycle transition report from the append-only journal."
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
        default="artifacts/reports/m4-lifecycle-transitions.json",
    )
    args = parser.parse_args()

    transaction_root = Path(args.transaction_root)
    committed = read_committed_captures(transaction_root)
    if committed:
        frozen_baseline = read_frozen_legacy_baseline(transaction_root)
        if not frozen_baseline:
            raise RuntimeError(
                "committed capture transactions exist but frozen legacy baseline is missing"
            )
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
    timeline = resolve_capture_timeline(rows, manifest_rows)
    payload = build_transition_report(
        rows,
        captured_dates=timeline.dates,
    )
    payload["capture_timeline"] = timeline.as_payload()
    payload["evidence_source"] = evidence_source
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
    print(f"\n[M4] transition report: {output}")
    print(f"[M4] human-readable report: {markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
