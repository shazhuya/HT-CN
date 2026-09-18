from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .capture_transaction import (
    frozen_legacy_baseline_through_date,
    read_committed_captures,
    read_frozen_legacy_baseline,
)
from .mirror_recovery import inspect_compatibility_mirrors


@dataclass(frozen=True, slots=True)
class EvidenceHealthFinding:
    code: str
    severity: str
    detail: str

    def as_payload(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "detail": self.detail,
        }


def build_evidence_chain_health(
    *,
    transaction_root: str | Path,
    journal_path: str | Path,
    manifest_path: str | Path,
) -> dict[str, Any]:
    root = Path(transaction_root)
    findings: list[EvidenceHealthFinding] = []

    def finding(code: str, severity: str, detail: str) -> None:
        findings.append(EvidenceHealthFinding(code, severity, detail))

    committed = read_committed_captures(root)
    baseline_rows = read_frozen_legacy_baseline(root)
    baseline_through = frozen_legacy_baseline_through_date(root)

    if not committed:
        return {
            "schema_version": 1,
            "status": "legacy_only",
            "authoritative_evidence_source": "legacy_journal_manifest",
            "frozen_legacy_baseline_present": bool(baseline_rows or baseline_through),
            "frozen_legacy_baseline_through_trade_date": baseline_through,
            "committed_capture_count": 0,
            "committed_capture_dates": [],
            "earliest_committed_capture_date": None,
            "latest_committed_capture_date": None,
            "total_committed_candidate_rows": 0,
            "mirror_integrity": {
                "journal_mirror_status": "transaction_store_not_active",
                "manifest_mirror_status": "transaction_store_not_active",
                "repair_needed": False,
            },
            "blocker_count": 0,
            "warning_count": 0,
            "blockers": [],
            "warnings": [],
            "transition_evidence_chain_ready": False,
            "interpretation": {
                "uses_score": False,
                "alpha_inference_allowed": False,
                "is_trade_instruction": False,
            },
        }

    if not baseline_rows and baseline_through is None:
        finding(
            "frozen_legacy_baseline_missing",
            "blocker",
            "Committed transactions exist but frozen legacy baseline evidence is missing.",
        )

    dates = [str(item["as_of_trade_date"]) for item in committed]
    if dates != sorted(dates) or len(dates) != len(set(dates)):
        finding(
            "transaction_chronology_invalid",
            "blocker",
            "Committed capture dates are not strictly unique/monotonic.",
        )

    if baseline_through is not None and dates:
        if dates[0] <= baseline_through:
            finding(
                "transaction_overlaps_legacy_baseline",
                "blocker",
                f"First committed capture {dates[0]} is not after frozen baseline {baseline_through}.",
            )

    total_rows = sum(int(item.get("candidate_count") or 0) for item in committed)
    zero_candidate_dates = [
        str(item["as_of_trade_date"])
        for item in committed
        if int(item.get("candidate_count") or 0) == 0
    ]

    mirror = inspect_compatibility_mirrors(
        transaction_root=root,
        journal_path=journal_path,
        manifest_path=manifest_path,
    )
    if mirror.repair_needed:
        finding(
            "compatibility_mirror_repair_needed",
            "warning",
            "Compatibility mirror is missing/corrupt/drifted; authoritative committed evidence remains intact.",
        )

    blockers = [item for item in findings if item.severity == "blocker"]
    warnings = [item for item in findings if item.severity == "warning"]

    return {
        "schema_version": 1,
        "status": (
            "not_ready"
            if blockers
            else "ready_with_warnings"
            if warnings
            else "ready"
        ),
        "authoritative_evidence_source": "frozen_baseline_plus_committed_transactions",
        "frozen_legacy_baseline_present": bool(baseline_rows or baseline_through),
        "frozen_legacy_baseline_row_count": len(baseline_rows),
        "frozen_legacy_baseline_through_trade_date": baseline_through,
        "committed_capture_count": len(committed),
        "committed_capture_dates": dates,
        "earliest_committed_capture_date": dates[0] if dates else None,
        "latest_committed_capture_date": dates[-1] if dates else None,
        "zero_candidate_capture_dates": zero_candidate_dates,
        "total_committed_candidate_rows": total_rows,
        "mirror_integrity": mirror.as_payload(),
        "blocker_count": len(blockers),
        "warning_count": len(warnings),
        "blockers": [item.as_payload() for item in blockers],
        "warnings": [item.as_payload() for item in warnings],
        "transition_evidence_chain_ready": len(blockers) == 0,
        "interpretation": {
            "uses_score": False,
            "mirror_is_authoritative": False,
            "alpha_inference_allowed": False,
            "is_trade_instruction": False,
        },
    }
