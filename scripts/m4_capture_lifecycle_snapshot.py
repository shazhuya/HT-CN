from __future__ import annotations

import argparse
from dataclasses import replace
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import duckdb

from htcn.app.evidence_identity import read_code_identity
from htcn.app.source_clock_lifecycle_service import M3SourceClockHarmonicService
from htcn.research.capture_transaction import (
    build_committed_capture,
    commit_capture_transaction,
    freeze_legacy_baseline,
    read_committed_captures,
)
from htcn.research.lifecycle_journal import append_entries, entries_from_analysis, read_journal
from htcn.research.mirror_recovery import (
    inspect_compatibility_mirrors,
    repair_compatibility_mirrors,
)
from htcn.research.snapshot_manifest import (
    SnapshotManifestEntry,
    append_snapshot_manifest,
    read_snapshot_manifest,
)


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
    manifest_path: Path,
    transaction_root: Path,
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
        "manifest_path": str(manifest_path),
        "transaction_root": str(transaction_root),
        "errors": [],
        "warnings": [],
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

    existing_committed = read_committed_captures(transaction_root)
    if not existing_committed:
        legacy_rows = read_journal(journal_path)
        legacy_manifest_rows = read_snapshot_manifest(manifest_path)
        legacy_dates = [
            str(row.get("as_of_trade_date"))
            for row in legacy_rows
            if row.get("as_of_trade_date")
        ]
        legacy_dates.extend(
            str(row.get("as_of_trade_date"))
            for row in legacy_manifest_rows
            if row.get("as_of_trade_date")
        )
        baseline_through = max(legacy_dates) if legacy_dates else None
        result["legacy_baseline_freeze"] = freeze_legacy_baseline(
            transaction_root,
            legacy_rows,
            baseline_through_trade_date=baseline_through,
        )

    committed_capture = build_committed_capture(
        code_head=str(identity.head),
        as_of_trade_date=expected,
        captured_at_utc=str(result["captured_at_utc"]),
        instrument_count=len(instruments),
        successful_instruments=successful,
        failed_instruments=len(instruments) - successful,
        worktree_clean=identity.worktree_clean,
        journal_rows=[entry.as_payload() for entry in all_entries],
    )
    result["capture_transaction"] = commit_capture_transaction(
        transaction_root,
        committed_capture,
    )
    result["capture_transaction_id"] = committed_capture.transaction_id

    existing_manifest = read_snapshot_manifest(manifest_path)
    baseline_trade_date = (
        min(str(row["as_of_trade_date"]) for row in existing_manifest)
        if existing_manifest
        else expected
    )

    mirror_entries = [
        replace(
            entry,
            capture_transaction_id=committed_capture.transaction_id,
        )
        for entry in all_entries
    ]
    mirror_status = "complete"
    try:
        append_result = append_entries(
            journal_path,
            mirror_entries,
            baseline_trade_date=baseline_trade_date,
        )
        result["journal_append"] = append_result

        manifest_entry = SnapshotManifestEntry(
            code_head=str(identity.head),
            as_of_trade_date=expected,
            captured_at_utc=str(result["captured_at_utc"]),
            instrument_count=len(instruments),
            successful_instruments=successful,
            failed_instruments=len(instruments) - successful,
            candidate_count=len(all_entries),
            worktree_clean=identity.worktree_clean,
            status="pass",
            capture_transaction_id=committed_capture.transaction_id,
        )
        result["manifest_append"] = append_snapshot_manifest(
            manifest_path,
            manifest_entry,
        )
        integrity = inspect_compatibility_mirrors(
            transaction_root=transaction_root,
            journal_path=journal_path,
            manifest_path=manifest_path,
        )
        result["mirror_integrity"] = integrity.as_payload()
        if integrity.repair_needed:
            result["mirror_repair"] = repair_compatibility_mirrors(
                transaction_root=transaction_root,
                journal_path=journal_path,
                manifest_path=manifest_path,
            )
            mirror_status = "repaired"
    except Exception as exc:
        result["warnings"].append({
            "scope": "compatibility_mirrors",
            "error": f"{type(exc).__name__}: {exc}",
            "authoritative_capture_committed": True,
        })
        try:
            result["mirror_repair"] = repair_compatibility_mirrors(
                transaction_root=transaction_root,
                journal_path=journal_path,
                manifest_path=manifest_path,
            )
            mirror_status = "repaired"
        except Exception as repair_exc:
            mirror_status = "incomplete"
            result["warnings"].append({
                "scope": "compatibility_mirror_repair",
                "error": f"{type(repair_exc).__name__}: {repair_exc}",
                "authoritative_capture_committed": True,
            })
    result["mirror_status"] = mirror_status

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
        "--manifest",
        default="data/research/m4/snapshot_manifest.jsonl",
    )
    parser.add_argument(
        "--transaction-root",
        default="data/research/m4/captures",
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
        manifest_path=Path(args.manifest),
        transaction_root=Path(args.transaction_root),
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
