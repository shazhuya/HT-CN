from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .capture_transaction import (
    frozen_legacy_baseline_present,
    frozen_legacy_baseline_through_date,
    read_committed_captures,
    read_frozen_legacy_baseline,
)
from .methodology_identity import build_methodology_identity
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


def _error(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


def _unavailable_mirror_state(reason: str) -> dict[str, object]:
    return {
        "journal_mirror_status": reason,
        "manifest_mirror_status": reason,
        "repair_needed": False,
        "authoritative_evidence_intact": False,
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

    current_methodology = None
    try:
        current_methodology = build_methodology_identity()
    except Exception as exc:
        finding(
            "current_methodology_identity_error",
            "blocker",
            _error(exc),
        )

    try:
        committed = read_committed_captures(root)
    except Exception as exc:
        finding(
            "committed_capture_read_error",
            "blocker",
            _error(exc),
        )
        blockers = [item.as_payload() for item in findings]
        return {
            "schema_version": 1,
            "status": "not_ready",
            "authoritative_evidence_source": "committed_transaction_store_unreadable",
            "frozen_legacy_baseline_present": None,
            "frozen_legacy_baseline_row_count": None,
            "frozen_legacy_baseline_through_trade_date": None,
            "committed_capture_count": None,
            "committed_capture_dates": [],
            "earliest_committed_capture_date": None,
            "latest_committed_capture_date": None,
            "zero_candidate_capture_dates": [],
            "total_committed_candidate_rows": None,
            "authoritative_methodology_contract_version": None,
            "authoritative_methodology_fingerprint": None,
            "current_methodology_contract_version": (
                None
                if current_methodology is None
                else current_methodology.contract_version
            ),
            "current_methodology_fingerprint": (
                None
                if current_methodology is None
                else current_methodology.fingerprint
            ),
            "current_methodology_matches_authoritative_chain": None,
            "mirror_integrity": _unavailable_mirror_state(
                "not_checked_authoritative_blocker"
            ),
            "blocker_count": 1,
            "warning_count": 0,
            "blockers": blockers,
            "warnings": [],
            "transition_evidence_chain_ready": False,
            "interpretation": {
                "uses_score": False,
                "mirror_is_authoritative": False,
                "alpha_inference_allowed": False,
                "is_trade_instruction": False,
            },
        }

    baseline_present = False
    baseline_rows: list[dict[str, Any]] = []
    baseline_through: str | None = None
    baseline_error: Exception | None = None
    try:
        baseline_present = frozen_legacy_baseline_present(root)
        baseline_rows = read_frozen_legacy_baseline(root)
        baseline_through = frozen_legacy_baseline_through_date(root)
    except Exception as exc:
        baseline_error = exc
        finding(
            "frozen_legacy_baseline_invalid",
            "blocker",
            _error(exc),
        )

    if not committed:
        blockers = [item for item in findings if item.severity == "blocker"]
        return {
            "schema_version": 1,
            "status": "legacy_only_not_ready" if blockers else "legacy_only",
            "authoritative_evidence_source": "legacy_journal_manifest",
            "frozen_legacy_baseline_present": (
                None if baseline_error is not None else baseline_present
            ),
            "frozen_legacy_baseline_through_trade_date": baseline_through,
            "committed_capture_count": 0,
            "committed_capture_dates": [],
            "earliest_committed_capture_date": None,
            "latest_committed_capture_date": None,
            "total_committed_candidate_rows": 0,
            "authoritative_methodology_contract_version": None,
            "authoritative_methodology_fingerprint": None,
            "current_methodology_contract_version": (
                None
                if current_methodology is None
                else current_methodology.contract_version
            ),
            "current_methodology_fingerprint": (
                None
                if current_methodology is None
                else current_methodology.fingerprint
            ),
            "current_methodology_matches_authoritative_chain": None,
            "mirror_integrity": {
                "journal_mirror_status": "transaction_store_not_active",
                "manifest_mirror_status": "transaction_store_not_active",
                "repair_needed": False,
            },
            "blocker_count": len(blockers),
            "warning_count": 0,
            "blockers": [item.as_payload() for item in blockers],
            "warnings": [],
            "transition_evidence_chain_ready": False,
            "interpretation": {
                "uses_score": False,
                "alpha_inference_allowed": False,
                "is_trade_instruction": False,
            },
        }

    if baseline_error is None and not baseline_present:
        finding(
            "frozen_legacy_baseline_missing",
            "blocker",
            "Committed transactions exist but frozen legacy baseline marker is missing.",
        )

    authoritative_methodology_contract_version: int | None = None
    authoritative_methodology_fingerprint: str | None = None
    method_pairs = {
        (
            item.get("methodology_contract_version"),
            str(item.get("methodology_fingerprint") or ""),
        )
        for item in committed
    }
    if len(method_pairs) != 1:
        finding(
            "committed_methodology_identity_ambiguous",
            "blocker",
            "Committed capture chain does not resolve to one methodology identity.",
        )
    else:
        method_version, method_fingerprint = next(iter(method_pairs))
        if method_version is None or not method_fingerprint:
            finding(
                "committed_methodology_identity_missing",
                "blocker",
                "Committed capture predates mandatory methodology identity; explicit migration is required.",
            )
        else:
            authoritative_methodology_contract_version = int(method_version)
            authoritative_methodology_fingerprint = method_fingerprint
            if current_methodology is not None and (
                current_methodology.contract_version
                != authoritative_methodology_contract_version
                or current_methodology.fingerprint
                != authoritative_methodology_fingerprint
            ):
                finding(
                    "current_methodology_differs_from_committed_chain",
                    "blocker",
                    "Current core methodology fingerprint differs from the authoritative committed capture chain.",
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

    authoritative_blockers = [
        item for item in findings if item.severity == "blocker"
    ]
    if authoritative_blockers:
        mirror_payload = _unavailable_mirror_state(
            "not_checked_authoritative_blocker"
        )
    else:
        try:
            mirror = inspect_compatibility_mirrors(
                transaction_root=root,
                journal_path=journal_path,
                manifest_path=manifest_path,
            )
            mirror_payload = mirror.as_payload()
            if mirror.repair_needed:
                finding(
                    "compatibility_mirror_repair_needed",
                    "warning",
                    "Compatibility mirror is missing/corrupt/drifted; authoritative committed evidence remains intact.",
                )
        except Exception as exc:
            mirror_payload = _unavailable_mirror_state(
                "mirror_integrity_check_failed"
            )
            finding(
                "mirror_integrity_check_error",
                "blocker",
                _error(exc),
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
        "authoritative_evidence_source": (
            "frozen_baseline_plus_committed_transactions"
            if baseline_present
            else "committed_transactions_without_valid_baseline"
        ),
        "frozen_legacy_baseline_present": (
            None if baseline_error is not None else baseline_present
        ),
        "frozen_legacy_baseline_row_count": (
            None if baseline_error is not None else len(baseline_rows)
        ),
        "frozen_legacy_baseline_through_trade_date": baseline_through,
        "committed_capture_count": len(committed),
        "committed_capture_dates": dates,
        "earliest_committed_capture_date": dates[0] if dates else None,
        "latest_committed_capture_date": dates[-1] if dates else None,
        "zero_candidate_capture_dates": zero_candidate_dates,
        "total_committed_candidate_rows": total_rows,
        "authoritative_methodology_contract_version": (
            authoritative_methodology_contract_version
        ),
        "authoritative_methodology_fingerprint": (
            authoritative_methodology_fingerprint
        ),
        "current_methodology_contract_version": (
            None
            if current_methodology is None
            else current_methodology.contract_version
        ),
        "current_methodology_fingerprint": (
            None
            if current_methodology is None
            else current_methodology.fingerprint
        ),
        "current_methodology_matches_authoritative_chain": (
            None
            if current_methodology is None
            or authoritative_methodology_fingerprint is None
            else (
                current_methodology.contract_version
                == authoritative_methodology_contract_version
                and current_methodology.fingerprint
                == authoritative_methodology_fingerprint
            )
        ),
        "mirror_integrity": mirror_payload,
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
