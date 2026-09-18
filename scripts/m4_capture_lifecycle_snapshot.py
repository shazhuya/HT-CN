from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import duckdb

from htcn.app.evidence_identity import read_code_identity
from htcn.app.source_clock_lifecycle_service import M3SourceClockHarmonicService
from htcn.research.lifecycle_journal import append_entries, entries_from_analysis


def _expected_trade_date(catalog: Path) -> str:
    with duckdb.connect(str(catalog), read_only=True) as con:
        row = con.execute("SELECT MAX(trade_date) FROM trade_calendar").fetchone()
    if row is None or row[0] is None:
        raise RuntimeError("trade_calendar has no closed trade date")
    return str(row[0])


def _instrument_ids(catalog: Path) -> list[str]:
    with duckdb.connect(str(catalog), read_only=True) as con:
        rows = con.execute(
            """
            SELECT s.instrument_id
            FROM security_master s
            JOIN daily_dataset d ON d.instrument_id = s.instrument_id
            WHERE s.status = 'listed'
              AND (s.instrument_id LIKE 'SSE.%' OR s.instrument_id LIKE 'SZSE.%')
            ORDER BY s.instrument_id
            """
        ).fetchall()
    return [str(row[0]) for row in rows]


def _summary_counter(values: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def run(
    *,
    data_root: Path,
    journal_path: Path,
    max_symbols: int = 0,
) -> dict[str, Any]:
    catalog = data_root / "catalog.duckdb"
    identity = read_code_identity()
    result: dict[str, Any] = {
        "schema_version": 1,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "code_head": identity.head,
        "worktree_clean": identity.worktree_clean,
        "dirty_paths": list(identity.dirty_paths),
        "status": "failed",
        "alpha_inference_allowed": False,
        "is_trade_instruction": False,
        "journal_path": str(journal_path),
        "errors": [],
    }

    if not identity.worktree_clean:
        result["errors"].append({
            "scope": "code_identity",
            "error": f"dirty worktree: {list(identity.dirty_paths)}",
        })
        return result
    if identity.head is None:
        result["errors"].append({"scope": "code_identity", "error": "git HEAD unavailable"})
        return result
    if not catalog.exists():
        result["errors"].append({"scope": "catalog", "error": f"missing {catalog}"})
        return result

    expected = _expected_trade_date(catalog)
    instruments = _instrument_ids(catalog)
    if max_symbols > 0:
        instruments = instruments[:max_symbols]
    result["expected_trade_date"] = expected
    result["instrument_count"] = len(instruments)

    service = M3SourceClockHarmonicService(data_root)
    all_entries = []
    successful = 0
    pattern_counts: list[int] = []

    for instrument_id in instruments:
        try:
            analysis = service.analyze(
                instrument_id,
                bars=420,
                scales=(3, 5, 8, 13),
                max_completed=20,
                max_forming=20,
            )
            as_of = str(analysis.get("last_trade_date"))
            if as_of != expected:
                raise RuntimeError(
                    f"analysis date {as_of} != expected closed trade date {expected}"
                )
            entries = entries_from_analysis(analysis, code_head=identity.head)
            all_entries.extend(entries)
            pattern_counts.append(len(entries))
            successful += 1
        except Exception as exc:
            result["errors"].append({
                "scope": instrument_id,
                "error": f"{type(exc).__name__}: {exc}",
            })

    result["successful_instruments"] = successful
    result["failed_instruments"] = len(instruments) - successful
    result["candidate_count"] = len(all_entries)
    result["candidate_count_by_instrument"] = {
        "min": min(pattern_counts) if pattern_counts else 0,
        "max": max(pattern_counts) if pattern_counts else 0,
        "total": sum(pattern_counts),
    }

    if result["errors"]:
        result["status"] = "failed_no_journal_append"
        return result

    append_result = append_entries(journal_path, all_entries)
    result["journal_append"] = append_result
    result["source_lifecycle_states"] = _summary_counter(
        [entry.source_lifecycle_state for entry in all_entries]
    )
    result["action_states"] = _summary_counter(
        [entry.action_state for entry in all_entries]
    )
    result["execution_context_gates"] = _summary_counter(
        [entry.execution_context_gate for entry in all_entries]
    )
    result["schemas"] = _summary_counter([entry.schema for entry in all_entries])
    result["status"] = "pass"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture one prospective M4 lifecycle snapshot from the latest closed A-share day."
    )
    parser.add_argument("--data-root", default="data/market")
    parser.add_argument(
        "--journal",
        default="data/research/m4/lifecycle_journal.jsonl",
    )
    parser.add_argument(
        "--output",
        default="artifacts/reports/m4-lifecycle-snapshot.json",
    )
    parser.add_argument("--max-symbols", type=int, default=0)
    args = parser.parse_args()

    payload = run(
        data_root=Path(args.data_root),
        journal_path=Path(args.journal),
        max_symbols=max(0, args.max_symbols),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\n[M4] prospective lifecycle snapshot: {output}")
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
