from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

import duckdb

from htcn.app.evidence_identity import read_code_identity
from htcn.app.product_contract import audit_product_payload
from htcn.app.source_clock_lifecycle_service import M3SourceClockHarmonicService


def _git_head() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:
        return None


PREFERRED = (
    "SSE.688256",
    "SZSE.300394",
    "SSE.600519",
    "SZSE.000001",
)


def _table_exists(con: duckdb.DuckDBPyConnection, name: str) -> bool:
    row = con.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [name],
    ).fetchone()
    return bool(row and int(row[0]) > 0)


def _candidate_ids(con: duckdb.DuckDBPyConnection) -> list[str]:
    rows: list[str] = []
    for instrument_id in PREFERRED:
        hit = con.execute(
            """
            SELECT COUNT(*)
            FROM security_master s
            JOIN daily_dataset d ON d.instrument_id = s.instrument_id
            WHERE s.instrument_id = ? AND s.status = 'listed'
            """,
            [instrument_id],
        ).fetchone()
        if hit and int(hit[0]) > 0:
            rows.append(instrument_id)

    for board in ("MAIN", "STAR", "CHINEXT"):
        board_rows = con.execute(
            """
            SELECT s.instrument_id
            FROM security_master s
            JOIN daily_dataset d ON d.instrument_id = s.instrument_id
            WHERE s.status = 'listed' AND s.board = ?
            ORDER BY d.last_trade_date DESC NULLS LAST, s.instrument_id
            LIMIT 3
            """,
            [board],
        ).fetchall()
        rows.extend(str(row[0]) for row in board_rows)

    deduped: list[str] = []
    seen: set[str] = set()
    for item in rows:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def run(*, data_root: Path, max_samples: int = 8) -> dict[str, Any]:
    catalog = data_root / "catalog.duckdb"
    identity = read_code_identity()
    result: dict[str, Any] = {
        "schema_version": 1,
        "code_head": identity.head,
        "worktree_clean": identity.worktree_clean,
        "dirty_paths": list(identity.dirty_paths),
        "data_root": str(data_root),
        "catalog": str(catalog),
        "status": "failed",
        "samples": [],
        "total_patterns": 0,
        "total_issues": 0,
    }
    if not catalog.exists():
        result["error"] = "catalog_not_found"
        return result

    with duckdb.connect(str(catalog), read_only=True) as con:
        if not _table_exists(con, "security_master"):
            result["error"] = "security_master_missing"
            return result
        if not _table_exists(con, "daily_dataset"):
            result["error"] = "daily_dataset_missing"
            return result
        candidates = _candidate_ids(con)[: max(1, max_samples)]

    if not candidates:
        result["error"] = "no_real_m1_candidates"
        return result

    service = M3SourceClockHarmonicService(data_root)
    sample_payloads: list[dict[str, Any]] = []
    total_patterns = 0
    total_issues = 0
    successful = 0

    for instrument_id in candidates:
        payload: dict[str, Any] = {
            "instrument_id": instrument_id,
            "analysis_status": "failed",
            "pattern_count": 0,
            "contract_passed": False,
            "issue_count": 0,
            "issues": [],
        }
        try:
            analysis = service.analyze(
                instrument_id,
                bars=420,
                scales=(3, 5, 8, 13),
                max_completed=12,
                max_forming=12,
            )
            audit = audit_product_payload(analysis)
            payload["analysis_status"] = "success"
            payload["first_trade_date"] = analysis.get("first_trade_date")
            payload["last_trade_date"] = analysis.get("last_trade_date")
            payload["pattern_count"] = audit.pattern_count
            payload["contract_passed"] = audit.passed
            payload["issue_count"] = audit.issue_count
            payload["issues"] = [
                {
                    "code": item.code,
                    "scope": item.scope,
                    "detail": item.detail,
                }
                for item in audit.issues
            ]
            payload["context_integrity_summary"] = (
                (analysis.get("context_integrity") or {}).get("summary_state")
            )
            payload["market_context_status"] = (
                (analysis.get("market_context") or {}).get("status")
            )
            payload["industry_context_status"] = (
                (analysis.get("sector_context") or {}).get("status")
            )
            payload["concept_context_status"] = (
                (analysis.get("concept_context") or {}).get("status")
            )
            successful += 1
            total_patterns += audit.pattern_count
            total_issues += audit.issue_count
        except Exception as exc:
            payload["error"] = f"{type(exc).__name__}: {exc}"
        sample_payloads.append(payload)

    result["samples"] = sample_payloads
    result["successful_analyses"] = successful
    result["total_patterns"] = total_patterns
    result["total_issues"] = total_issues
    result["pattern_coverage"] = (
        "real_patterns_observed"
        if total_patterns > 0
        else "no_real_patterns_in_selected_samples_unit_gates_still_required"
    )
    result["status"] = (
        "pass"
        if successful == len(sample_payloads) and total_issues == 0
        else "failed"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HT-CN M3 real-M1 product payload contract smoke"
    )
    parser.add_argument("--data-root", default="data/market")
    parser.add_argument("--max-samples", type=int, default=8)
    parser.add_argument(
        "--output",
        default="artifacts/reports/m3-product-contract-smoke.json",
    )
    args = parser.parse_args()

    result = run(
        data_root=Path(args.data_root),
        max_samples=max(1, args.max_samples),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    print(f"\n[M3] product contract smoke: {output}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
