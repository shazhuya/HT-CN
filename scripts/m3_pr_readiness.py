from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from htcn.app.evidence_identity import read_code_identity


@dataclass(frozen=True, slots=True)
class ReadinessFinding:
    code: str
    severity: str
    detail: str


def _git_head() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:
        return None


def _load(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _finding(
    findings: list[ReadinessFinding],
    code: str,
    severity: str,
    detail: str,
) -> None:
    findings.append(ReadinessFinding(code, severity, detail))


def _require_current_report(
    findings: list[ReadinessFinding],
    *,
    name: str,
    report: dict[str, Any] | None,
    current_head: str | None,
) -> bool:
    if report is None:
        _finding(
            findings,
            f"{name}_report_missing",
            "blocker",
            f"{name} report is missing or unreadable.",
        )
        return False
    report_head = report.get("code_head")
    if current_head is None:
        _finding(
            findings,
            "current_git_head_unavailable",
            "blocker",
            "Cannot resolve current git HEAD, so acceptance evidence cannot be bound to code.",
        )
        return False
    if report_head != current_head:
        _finding(
            findings,
            f"{name}_report_stale",
            "blocker",
            f"{name} report belongs to {report_head!r}, current HEAD is {current_head!r}.",
        )
        return False
    return True


def evaluate(
    *,
    current_head: str | None,
    workbench: dict[str, Any] | None,
    metadata: dict[str, Any] | None,
    product: dict[str, Any] | None,
    context: dict[str, Any] | None,
) -> dict[str, Any]:
    findings: list[ReadinessFinding] = []

    workbench_current = _require_current_report(
        findings, name="workbench", report=workbench, current_head=current_head
    )
    metadata_current = _require_current_report(
        findings, name="metadata", report=metadata, current_head=current_head
    )
    product_current = _require_current_report(
        findings, name="product", report=product, current_head=current_head
    )
    context_current = _require_current_report(
        findings, name="context", report=context, current_head=current_head
    )

    for report_name, report in (
        ("workbench", workbench),
        ("metadata", metadata),
        ("product", product),
        ("context", context),
    ):
        if report is not None and report.get("worktree_clean") is not True:
            _finding(
                findings,
                f"{report_name}_evidence_dirty_worktree",
                "blocker",
                (
                    f"{report_name} evidence was generated from a dirty worktree: "
                    f"{report.get('dirty_paths') or []}."
                ),
            )

    if workbench_current and workbench is not None:
        if workbench.get("status") != "pass":
            _finding(
                findings, "workbench_acceptance_failed", "blocker",
                f"Formal workbench acceptance status is {workbench.get('status')!r}.",
            )
        expected_gates = {
            "python",
            "web_build",
            "real_m1_metadata",
            "real_m1_product_contract",
            "local_services",
            "playwright",
        }
        gates = workbench.get("gates") or {}
        missing = sorted(expected_gates - set(gates))
        if missing:
            _finding(
                findings, "workbench_gate_missing", "blocker",
                f"Formal acceptance is missing gates: {missing}.",
            )
        failed = sorted(
            key for key in expected_gates
            if isinstance(gates.get(key), dict)
            and gates[key].get("status") != "pass"
        )
        if failed:
            _finding(
                findings, "workbench_gate_not_passed", "blocker",
                f"Formal acceptance gates not passed: {failed}.",
            )

    if metadata_current and metadata is not None:
        if metadata.get("status") != "pass":
            _finding(
                findings, "real_m1_metadata_failed", "blocker",
                f"Strict real-M1 metadata status is {metadata.get('status')!r}.",
            )
        samples = metadata.get("samples") or []
        boards = {
            str(item.get("board_expected"))
            for item in samples
            if item.get("metadata_loaded") and item.get("parquet_loaded")
        }
        missing_boards = sorted({"MAIN", "STAR", "CHINEXT"} - boards)
        if missing_boards:
            _finding(
                findings, "real_m1_board_coverage_missing", "blocker",
                f"Readable representative parquet missing for boards: {missing_boards}.",
            )
        if metadata.get("event_feed_status") != "event_complete":
            _finding(
                findings, "daily_event_feed_partial", "warning",
                (
                    "Daily event feed is not complete-market coverage; "
                    "special-event exceptions remain fail-safe unresolved where applicable."
                ),
            )

        expected_trade_date = (
            None if context is None else context.get("expected_trade_date")
        )
        if expected_trade_date:
            stale_samples = sorted(
                str(item.get("instrument_id"))
                for item in samples
                if item.get("logical_last_trade_date") != expected_trade_date
            )
            if stale_samples:
                _finding(
                    findings,
                    "real_m1_metadata_trade_date_mismatch",
                    "blocker",
                    (
                        f"Metadata smoke samples are not all aligned to expected trade date "
                        f"{expected_trade_date}: {stale_samples}."
                    ),
                )

    if product_current and product is not None:
        if product.get("status") != "pass":
            _finding(
                findings, "real_m1_product_contract_failed", "blocker",
                f"Real-M1 product contract status is {product.get('status')!r}.",
            )
        if int(product.get("total_issues") or 0) != 0:
            _finding(
                findings, "real_m1_product_contract_issues", "blocker",
                f"Product contract found {product.get('total_issues')} issue(s).",
            )
        if int(product.get("successful_analyses") or 0) <= 0:
            _finding(
                findings, "real_m1_no_successful_analysis", "blocker",
                "No real-M1 analysis completed successfully.",
            )
        if int(product.get("total_patterns") or 0) <= 0:
            _finding(
                findings, "real_m1_no_pattern_observed", "warning",
                (
                    "Selected real-M1 samples produced no harmonic candidates; "
                    "unit/browser gates still verify pattern contracts, but real-pattern assembly was not observed."
                ),
            )

        expected_trade_date = (
            None if context is None else context.get("expected_trade_date")
        )
        if expected_trade_date:
            product_samples = [
                item for item in (product.get("samples") or [])
                if item.get("analysis_status") == "success"
            ]
            stale_product_samples = sorted(
                str(item.get("instrument_id"))
                for item in product_samples
                if item.get("last_trade_date") != expected_trade_date
            )
            if stale_product_samples:
                _finding(
                    findings,
                    "real_m1_product_trade_date_mismatch",
                    "blocker",
                    (
                        f"Product smoke analyses are not all aligned to expected trade date "
                        f"{expected_trade_date}: {stale_product_samples}."
                    ),
                )

    if context_current and context is not None:
        expected_trade_date = context.get("expected_trade_date")
        target_trade_date = context.get("target_trade_date")
        logical_market_latest = context.get("logical_market_latest")
        local_calendar_latest = context.get("local_trade_calendar_latest")
        if not expected_trade_date:
            _finding(
                findings, "context_expected_trade_date_missing", "blocker",
                "Context report does not expose expected_trade_date.",
            )
        else:
            if target_trade_date != expected_trade_date:
                _finding(
                    findings, "context_target_trade_date_mismatch", "blocker",
                    (
                        f"Context target trade date {target_trade_date!r} does not match "
                        f"provider-confirmed latest closed day {expected_trade_date!r}."
                    ),
                )
            if local_calendar_latest != expected_trade_date:
                _finding(
                    findings, "local_calendar_trade_date_mismatch", "blocker",
                    (
                        f"Local trade calendar latest {local_calendar_latest!r} does not match "
                        f"expected {expected_trade_date!r}."
                    ),
                )
            if logical_market_latest != expected_trade_date:
                _finding(
                    findings, "logical_market_trade_date_mismatch", "blocker",
                    (
                        f"Logical base+delta market latest {logical_market_latest!r} does not "
                        f"match expected {expected_trade_date!r}."
                    ),
                )

        overall = str(context.get("overall") or "unknown")
        if overall == "partial_failure":
            _finding(
                findings, "context_sync_partial_failure", "blocker",
                "At least one context synchronization layer failed structurally.",
            )
        elif overall == "degraded":
            _finding(
                findings, "context_sync_degraded", "warning",
                (
                    "Context sync completed with degradation; preserved snapshots/fallbacks "
                    "must remain explicitly surfaced by context integrity."
                ),
            )
        elif overall != "all_steps_completed":
            _finding(
                findings, "context_sync_unknown_state", "blocker",
                f"Unexpected context sync state: {overall!r}.",
            )

        coverage = context.get("market_dataset_coverage") or {}
        stale_count = int(coverage.get("stale_dataset_count") or 0)
        ahead_count = int(coverage.get("ahead_dataset_count") or 0)
        initialized_count = int(coverage.get("initialized_dataset_count") or 0)
        if initialized_count <= 0:
            _finding(
                findings, "market_dataset_coverage_empty", "blocker",
                "No initialized listed SSE/SZSE daily datasets were found.",
            )
        if stale_count > 0:
            _finding(
                findings, "market_dataset_stale_count", "blocker",
                (
                    f"{stale_count} initialized listed SSE/SZSE dataset(s) are behind "
                    f"expected trade date {expected_trade_date}."
                ),
            )
        if ahead_count > 0:
            _finding(
                findings, "market_dataset_ahead_of_closed_clock", "blocker",
                (
                    f"{ahead_count} dataset(s) are ahead of the latest closed-trade clock; "
                    "partial current-day data may have contaminated the daily view."
                ),
            )

        layers = context.get("layers") or {}
        for layer_name, layer in layers.items():
            if not isinstance(layer, dict):
                continue
            state = str(layer.get("state") or "unknown")
            if state == "failed":
                _finding(
                    findings, f"context_{layer_name}_failed", "blocker",
                    f"Context layer {layer_name} failed.",
                )
            elif state not in {"current", "partial_positive_evidence"}:
                _finding(
                    findings, f"context_{layer_name}_{state}", "warning",
                    f"Context layer {layer_name} is {state}.",
                )

        event = layers.get("execution_event") if isinstance(layers, dict) else None
        if isinstance(event, dict) and event.get("coverage_scope") == "positive_evidence_only":
            _finding(
                findings, "execution_event_positive_only", "warning",
                (
                    "Suspension feed is positive-evidence-only by design; absence of an event "
                    "does not prove a security was tradable."
                ),
            )

    blockers = [item for item in findings if item.severity == "blocker"]
    warnings = [item for item in findings if item.severity == "warning"]
    pr_ready = not blockers

    return {
        "schema_version": 1,
        "evaluated_at_utc": datetime.now(UTC).isoformat(),
        "code_head": current_head,
        "pr_ready": pr_ready,
        "status": "ready_with_warnings" if pr_ready and warnings else "ready" if pr_ready else "not_ready",
        "blocker_count": len(blockers),
        "warning_count": len(warnings),
        "blockers": [asdict(item) for item in blockers],
        "warnings": [asdict(item) for item in warnings],
        "known_boundaries": [
            "5-0 remains production-quarantined.",
            "Alternate Bat remains fail-closed.",
            "BSE remains deferred.",
            "Daily event coverage may remain positive-evidence-only; this is a surfaced limitation, not silent completeness.",
        ],
        "semantic_note": (
            "pr_ready is a code/evidence readiness gate, not an investment score, "
            "performance claim, or permission to execute trades."
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    status = str(payload.get("status") or "not_ready")
    title = {
        "ready": "READY",
        "ready_with_warnings": "READY（有已知警告）",
        "not_ready": "NOT READY",
    }.get(status, status)

    lines = [
        "# HT-CN M3 合并就绪报告",
        "",
        f"- 当前 HEAD：`{payload.get('code_head')}`",
        f"- 判定：**{title}**",
        f"- 硬阻断：{payload.get('blocker_count', 0)}",
        f"- 警告：{payload.get('warning_count', 0)}",
        "",
        "## 硬阻断",
        "",
    ]
    blockers = list(payload.get("blockers") or [])
    if blockers:
        for item in blockers:
            lines.append(f"- **{item.get('code')}**：{item.get('detail')}")
    else:
        lines.append("- 无。")

    lines.extend(["", "## 警告", ""])
    warnings = list(payload.get("warnings") or [])
    if warnings:
        for item in warnings:
            lines.append(f"- **{item.get('code')}**：{item.get('detail')}")
    else:
        lines.append("- 无。")

    lines.extend(["", "## 当前固定边界", ""])
    for item in payload.get("known_boundaries") or []:
        lines.append(f"- {item}")

    lines.extend([
        "",
        "## 判定含义",
        "",
        "这里的 READY 只表示 **M3 当前代码与真实 M1 验收证据满足合并就绪条件**。",
        "它不是投资评分、胜率结论，也不代表任何交易执行许可。",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="HT-CN M3 PR readiness closeout")
    parser.add_argument(
        "--workbench",
        default="artifacts/reports/m3-workbench-acceptance.json",
    )
    parser.add_argument(
        "--metadata",
        default="artifacts/reports/m3-metadata-tradability-smoke.json",
    )
    parser.add_argument(
        "--product",
        default="artifacts/reports/m3-product-contract-smoke.json",
    )
    parser.add_argument(
        "--context",
        default="artifacts/reports/m3-context-sync-summary.json",
    )
    parser.add_argument(
        "--output",
        default="artifacts/reports/m3-pr-readiness.json",
    )
    args = parser.parse_args()

    identity = read_code_identity()
    payload = evaluate(
        current_head=identity.head,
        workbench=_load(Path(args.workbench)),
        metadata=_load(Path(args.metadata)),
        product=_load(Path(args.product)),
        context=_load(Path(args.context)),
    )
    if not identity.worktree_clean:
        blockers = list(payload.get("blockers") or [])
        blockers.append({
            "code": "current_worktree_dirty",
            "severity": "blocker",
            "detail": f"Current worktree has uncommitted changes: {list(identity.dirty_paths)}.",
        })
        payload["blockers"] = blockers
        payload["blocker_count"] = len(blockers)
        payload["pr_ready"] = False
        payload["status"] = "not_ready"
        payload["current_worktree_clean"] = False
        payload["current_dirty_paths"] = list(identity.dirty_paths)
    else:
        payload["current_worktree_clean"] = True
        payload["current_dirty_paths"] = []

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown_output = output.with_suffix(".md")
    markdown_output.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\n[M3] PR readiness report: {output}")
    print(f"[M3] human-readable report: {markdown_output}")
    return 0 if payload["pr_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
