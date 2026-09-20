from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from htcn.research.capture_transaction import (
    committed_capture_view,
    committed_followup_view,
    frozen_legacy_baseline_present,
    frozen_legacy_baseline_through_date,
    read_committed_captures,
    read_frozen_legacy_baseline,
)
from htcn.research.evidence_health import build_evidence_chain_health
from htcn.research.m7_accumulation import build_m7_accumulation_status
from htcn.research.outcome_snapshot import read_outcome_snapshots
from htcn.research.prospective_observations import (
    build_prospective_observation_report,
)


def _observation_report(transaction_root: Path) -> dict[str, Any]:
    committed = read_committed_captures(transaction_root)
    if not committed:
        return {
            "schema_version": 4,
            "status": "no_outcome_cohort",
            "captured_dates": [],
            "prospective_candidate_count": 0,
            "observation_count": 0,
            "candidate_summaries": [],
            "observations": [],
        }
    if not frozen_legacy_baseline_present(transaction_root):
        raise RuntimeError(
            "committed captures exist but frozen legacy baseline is missing"
        )
    baseline = read_frozen_legacy_baseline(transaction_root)
    baseline_through = frozen_legacy_baseline_through_date(transaction_root)
    rows, manifest_rows = committed_capture_view(
        legacy_journal_rows=baseline,
        capture_rows=committed,
    )
    followup_rows = committed_followup_view(committed)
    return build_prospective_observation_report(
        rows,
        manifest_rows=manifest_rows,
        followup_rows=followup_rows,
        legacy_baseline_trade_date=baseline_through,
    )


def render_markdown(payload: dict[str, Any]) -> str:
    boundary = payload.get("inference_boundary") or {}
    lines = [
        "# HT-CN M7 前瞻证据积累状态",
        "",
        f"- 状态：**{payload.get('status')}**",
        f"- 证据链健康：**{payload.get('evidence_health_status')}**",
        f"- 已提交 future captures：{payload.get('committed_capture_count', 0)}",
        f"- 最新 capture：`{payload.get('latest_committed_capture_date')}`",
        f"- Prospective outcome cohort：{payload.get('prospective_candidate_count', 0)}",
        f"- Observation rows：{payload.get('observation_count', 0)}",
        f"- Outcome snapshots：{payload.get('outcome_snapshot_count', 0)}",
        f"- 最新 outcome as-of：`{payload.get('latest_outcome_as_of_trade_date')}`",
        f"- Gate：`{payload.get('issue_gate')}`",
        "",
        "## 积累事实",
        "",
        f"- 曾 scanner absent 的候选：{payload.get('scanner_absent_ever_candidate_count', 0)}",
        f"- 已观察 Source Terminal 的候选：{payload.get('source_terminal_observed_candidate_count', 0)}",
        f"- 出现 price-basis drift 的候选：{payload.get('price_basis_drift_candidate_count', 0)}",
        f"- 最大 capture follow-up 深度：{payload.get('max_captured_snapshot_depth', 0)}",
        f"- 最新 outcome 状态分布：{payload.get('latest_outcome_status_counts') or {}}",
        f"- 最新 market-path traded-bar 深度：{payload.get('latest_market_path_traded_bar_depth') or {}}",
        "",
        "## 固定推断边界",
        "",
        f"- statistical inference：**{boundary.get('statistical_inference_allowed')}**",
        f"- alpha inference：**{boundary.get('alpha_inference_allowed')}**",
        f"- win-rate inference：**{boundary.get('win_rate_inference_allowed')}**",
        f"- profitability inference：**{boundary.get('profitability_inference_allowed')}**",
        f"- trade instruction：**{boundary.get('is_trade_instruction')}**",
        "",
        "## Next action",
        "",
        f"- {payload.get('next_action')}",
        "",
    ]
    return "\n".join(lines)


def run(
    *,
    transaction_root: Path,
    outcome_root: Path,
    journal_path: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    health = build_evidence_chain_health(
        transaction_root=transaction_root,
        journal_path=journal_path,
        manifest_path=manifest_path,
    )
    observations = _observation_report(transaction_root)
    snapshots = read_outcome_snapshots(outcome_root)
    payload = build_m7_accumulation_status(
        evidence_health=health,
        observation_report=observations,
        outcome_snapshots=snapshots,
    )
    payload["generated_at_utc"] = datetime.now(UTC).isoformat()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build read-only M7 prospective evidence accumulation status."
    )
    parser.add_argument(
        "--transaction-root",
        default="data/research/m4/captures",
    )
    parser.add_argument(
        "--outcome-root",
        default="data/research/m4/outcomes",
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
        default="artifacts/reports/m7-accumulation-status.json",
    )
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        payload = run(
            transaction_root=Path(args.transaction_root),
            outcome_root=Path(args.outcome_root),
            journal_path=Path(args.journal),
            manifest_path=Path(args.manifest),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        payload = {
            "schema_version": 1,
            "status": "blocked",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "issue_gate": "ISSUE-0066",
            "errors": [f"{type(exc).__name__}: {exc}"],
            "inference_boundary": {
                "statistical_inference_allowed": False,
                "alpha_inference_allowed": False,
                "win_rate_inference_allowed": False,
                "profitability_inference_allowed": False,
                "is_trade_instruction": False,
            },
            "next_action": (
                "Resolve the evidence read/validation error before another M7 evidence append."
            ),
        }

    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    output.with_suffix(".md").write_text(
        render_markdown(payload),
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\n[M7] accumulation status: {output}")
    return 0 if payload.get("status") != "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
