from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import duckdb

from htcn.app.harmonic_service import LocalHarmonicService
from htcn.research.capture_transaction import (
    committed_capture_view,
    committed_followup_view,
    frozen_legacy_baseline_present,
    frozen_legacy_baseline_through_date,
    read_committed_captures,
    read_frozen_legacy_baseline,
)
from htcn.research.outcome_evaluator import evaluate_candidate_outcome
from htcn.research.outcome_protocol import load_outcome_protocol
from htcn.research.outcome_snapshot import (
    build_outcome_snapshot,
    commit_outcome_snapshot,
)
from htcn.research.prospective_observations import (
    build_prospective_observation_report,
)


def _latest_catalog_trade_date(catalog: Path) -> str:
    if not catalog.is_file():
        raise FileNotFoundError(f"missing M1 catalog: {catalog}")
    with duckdb.connect(str(catalog), read_only=True) as con:
        row = con.execute(
            "SELECT MAX(trade_date) FROM trade_calendar"
        ).fetchone()
    if row is None or row[0] is None:
        raise RuntimeError("M1 trade_calendar has no trade date")
    return str(row[0])


def _authoritative_observation_panel(
    transaction_root: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    committed = read_committed_captures(transaction_root)
    if not committed:
        return {
            "schema_version": 1,
            "status": "no_authoritative_future_capture",
            "candidate_summaries": [],
        }, []

    if not frozen_legacy_baseline_present(transaction_root):
        raise RuntimeError(
            "committed captures exist but frozen legacy baseline is missing"
        )
    baseline = read_frozen_legacy_baseline(transaction_root)
    baseline_through = frozen_legacy_baseline_through_date(
        transaction_root
    )
    rows, manifest_rows = committed_capture_view(
        legacy_journal_rows=baseline,
        capture_rows=committed,
    )
    followup_rows = committed_followup_view(committed)
    panel = build_prospective_observation_report(
        rows,
        manifest_rows=manifest_rows,
        followup_rows=followup_rows,
        legacy_baseline_trade_date=baseline_through,
    )
    return panel, committed


def _continuous_market_path(
    service: LocalHarmonicService,
    instrument_id: str,
) -> tuple[Any, str, str, str | None]:
    raw = service._load_history(instrument_id)
    continuous, mode, warning, basis_id = service._continuous_view(
        instrument_id,
        raw,
    )
    return (
        continuous.sort_values("trade_date").reset_index(drop=True),
        mode,
        basis_id,
        warning,
    )


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# HT-CN M4 Outcome Protocol v2 报告",
        "",
        f"- 状态：**{payload.get('status')}**",
        f"- Outcome as-of：{payload.get('outcome_as_of_trade_date')}",
        f"- Protocol：{payload.get('outcome_protocol_id')}",
        f"- Protocol fingerprint：{payload.get('outcome_protocol_fingerprint')}",
        f"- Capture methodology：{payload.get('capture_methodology_fingerprint')}",
        f"- Outcome engine：v{payload.get('outcome_engine_contract_version')} / {payload.get('outcome_engine_fingerprint')}",
        f"- Candidate count：{payload.get('candidate_count', 0)}",
        f"- Outcome snapshot：{payload.get('outcome_snapshot_id')}",
        "",
        "## 状态分布",
        "",
    ]
    counts = payload.get("status_counts") or {}
    if counts:
        for key, value in sorted(counts.items()):
            lines.append(f"- {key}：{value}")
    else:
        lines.append("- 当前没有 outcome-enrolled candidate。")

    lines.extend(["", "## Candidate outcomes", ""])
    results = payload.get("results") or []
    if not results:
        lines.append("- 无。")
    for item in results:
        events = item.get("source_events") or {}
        lines.append(
            f"- {item.get('candidate_key')}："
            f"status={item.get('status')}；"
            f"terminal={events.get('source_terminal_trade_date')}；"
            f"Type-I={events.get('type_i_early_result')}；"
            f"Type-II-price={events.get('type_ii_price_structure_status')}；"
            f"path-bars={item.get('market_path_traded_bar_count')}；"
            f"path-sha={item.get('market_path_sha256')}"
        )

    lines.extend([
        "",
        "## 固定边界",
        "",
        "- Outcome path 使用 M1 base + daily_delta logical history 的真实 traded bars，不使用 capture snapshot 序号代替交易日。",
        "- Source Terminal / Type-I / Type-II price structure 复用现有 observe_source_execution / derive_source_lifecycle。",
        "- Type-II price structure 不是完整 Carney indicator-confirmed reversal proof。",
        "- basis drift 不自动重基准；跨 basis 价格比较保持 unresolved。",
        "- Terminal 未出现属于 right-censored / ongoing，不记失败。",
        "- 5/10/20 bar excursion 从 T+1 开始，不包含 Terminal bar。",
        "- 本协议不定义 entry / stop / position / fees / execution P&L。",
        "- 不计算 win rate / alpha / benchmark excess return / p-value / 买卖排名。",
        "",
    ])
    errors = payload.get("errors") or []
    if errors:
        lines.extend(["## Errors", ""])
        for item in errors:
            lines.append(
                f"- {item.get('scope')}：{item.get('error')}"
            )
        lines.append("")
    return "\n".join(lines)


def run(
    *,
    data_root: Path,
    transaction_root: Path,
    outcome_root: Path,
    outcome_as_of_trade_date: str | None = None,
) -> dict[str, Any]:
    protocol, protocol_identity = load_outcome_protocol()
    payload: dict[str, Any] = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "not_ready",
        "outcome_protocol_id": protocol_identity.protocol_id,
        "outcome_protocol_fingerprint": protocol_identity.fingerprint,
        "outcome_as_of_trade_date": outcome_as_of_trade_date,
        "capture_methodology_fingerprint": None,
        "outcome_engine_contract_version": None,
        "outcome_engine_fingerprint": None,
        "candidate_count": 0,
        "status_counts": {},
        "results": [],
        "outcome_snapshot_id": None,
        "outcome_snapshot_commit_status": None,
        "errors": [],
        "warnings": [],
        "interpretation": {
            "evidence_only": True,
            "is_trade_instruction": False,
            "alpha_inference_allowed": False,
            "win_rate_computed": False,
            "execution_pnl_computed": False,
        },
    }

    try:
        panel, committed = _authoritative_observation_panel(
            transaction_root
        )
    except Exception as exc:
        payload["status"] = "authoritative_evidence_error"
        payload["errors"].append({
            "scope": "authoritative_evidence",
            "error": f"{type(exc).__name__}: {exc}",
        })
        return payload

    if not committed:
        payload["status"] = "no_authoritative_future_capture"
        return payload

    methodology_version = int(
        committed[0].get("methodology_contract_version") or 0
    )
    methodology_fingerprint = str(
        committed[0].get("methodology_fingerprint") or ""
    )
    expected_methodology_version = int(
        protocol["capture_contract"]["methodology_contract_version"]
    )
    if methodology_version != expected_methodology_version:
        payload["status"] = "capture_methodology_mismatch"
        payload["errors"].append({
            "scope": "capture_methodology",
            "error": (
                f"committed methodology v{methodology_version} != "
                f"outcome protocol v{expected_methodology_version}"
            ),
        })
        return payload
    payload["capture_methodology_fingerprint"] = (
        methodology_fingerprint
    )

    as_of = outcome_as_of_trade_date
    if as_of is None:
        try:
            as_of = _latest_catalog_trade_date(
                data_root / "catalog.duckdb"
            )
        except Exception as exc:
            payload["status"] = "market_clock_error"
            payload["errors"].append({
                "scope": "market_clock",
                "error": f"{type(exc).__name__}: {exc}",
            })
            return payload
    payload["outcome_as_of_trade_date"] = as_of

    summaries = list(panel.get("candidate_summaries") or [])
    payload["candidate_count"] = len(summaries)
    if not summaries:
        payload["status"] = "no_outcome_cohort"
        return payload

    service = LocalHarmonicService(data_root)
    results: list[dict[str, Any]] = []
    for summary in sorted(
        summaries,
        key=lambda item: str(item.get("candidate_key") or ""),
    ):
        key = str(summary.get("candidate_key") or "")
        instrument_id = str(summary.get("instrument_id") or "")
        try:
            frame, price_mode, basis_id, warning = (
                _continuous_market_path(
                    service,
                    instrument_id,
                )
            )
            result = evaluate_candidate_outcome(
                summary,
                frame,
                outcome_as_of_trade_date=as_of,
                current_price_mode=price_mode,
                current_price_basis_id=basis_id,
                methodology_fingerprint=methodology_fingerprint,
                protocol=protocol,
            )
            if warning:
                result["market_data_warning"] = warning
            results.append(result)
        except Exception as exc:
            payload["errors"].append({
                "scope": "candidate_evaluation",
                "candidate_key": key,
                "instrument_id": instrument_id,
                "error": f"{type(exc).__name__}: {exc}",
            })

    payload["results"] = results
    payload["status_counts"] = dict(sorted(Counter(
        str(item.get("status") or "unknown")
        for item in results
    ).items()))

    if payload["errors"]:
        payload["status"] = "candidate_evaluation_errors"
        return payload
    if len(results) != len(summaries):
        payload["status"] = "candidate_coverage_mismatch"
        payload["errors"].append({
            "scope": "candidate_coverage",
            "error": (
                f"evaluated={len(results)} expected={len(summaries)}"
            ),
        })
        return payload

    snapshot = build_outcome_snapshot(
        outcome_as_of_trade_date=as_of,
        outcome_protocol_id=protocol_identity.protocol_id,
        outcome_protocol_fingerprint=protocol_identity.fingerprint,
        capture_methodology_fingerprint=methodology_fingerprint,
        results=results,
    )
    payload["outcome_snapshot_id"] = snapshot.snapshot_id
    payload["outcome_engine_contract_version"] = (
        snapshot.outcome_engine_contract_version
    )
    payload["outcome_engine_fingerprint"] = (
        snapshot.outcome_engine_fingerprint
    )
    try:
        committed_snapshot = commit_outcome_snapshot(
            outcome_root,
            snapshot,
        )
    except Exception as exc:
        payload["status"] = "outcome_data_drift_or_commit_error"
        payload["errors"].append({
            "scope": "outcome_snapshot_commit",
            "error": f"{type(exc).__name__}: {exc}",
        })
        return payload

    payload["outcome_snapshot_commit_status"] = (
        committed_snapshot["status"]
    )
    payload["outcome_snapshot_path"] = committed_snapshot["path"]
    payload["status"] = "ready"
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build preregistered M4 outcome-v2 facts from authoritative "
            "prospective cohort + local M1 logical daily history."
        )
    )
    parser.add_argument("--data-root", default="data/market")
    parser.add_argument(
        "--transaction-root",
        default="data/research/m4/captures",
    )
    parser.add_argument(
        "--outcome-root",
        default="data/research/m4/outcomes",
    )
    parser.add_argument("--as-of", default=None)
    parser.add_argument(
        "--output",
        default="artifacts/reports/m4-outcome-v2.json",
    )
    args = parser.parse_args()

    payload = run(
        data_root=Path(args.data_root),
        transaction_root=Path(args.transaction_root),
        outcome_root=Path(args.outcome_root),
        outcome_as_of_trade_date=args.as_of,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        ),
        encoding="utf-8",
    )
    output.with_suffix(".md").write_text(
        render_markdown(payload),
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\n[M4] outcome-v2 report: {output}")
    return 0 if payload["status"] in {
        "ready",
        "no_outcome_cohort",
        "no_authoritative_future_capture",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
