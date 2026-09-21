from __future__ import annotations

import json
import zipfile
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from .evidence_intake import audit_evidence_bundle


@dataclass(frozen=True, slots=True)
class M7EvidenceAcceptance:
    status: str
    classification: str
    bundle_path: str
    blocker_count: int
    warning_count: int
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    summary: dict[str, Any]
    receipt: dict[str, Any] | None

    def as_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["blockers"] = list(self.blockers)
        payload["warnings"] = list(self.warnings)
        return payload


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_member(
    archive: zipfile.ZipFile,
    name: str,
) -> dict[str, Any] | None:
    try:
        raw = archive.read(name)
    except KeyError:
        return None
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON bundle member: {name}") from exc
    if not isinstance(value, dict):
        raise TypeError(f"bundle JSON member is not an object: {name}")
    return value


def _previous_identity(
    receipt: Mapping[str, Any] | None,
) -> tuple[str | None, str | None, int | None, str | None]:
    if receipt is None:
        return None, None, None, None
    value = dict(receipt)
    inspection = dict(value.get("independent_inspection") or {})
    trade_date = value.get("trade_date") or inspection.get(
        "latest_committed_capture_date"
    )
    transaction_id = inspection.get("capture_transaction_id") or value.get(
        "latest_capture_transaction_id"
    )
    capture_count_raw = inspection.get("committed_capture_count")
    capture_count = (
        None
        if capture_count_raw is None
        else int(capture_count_raw)
    )
    outcome_snapshot_id = inspection.get("outcome_snapshot_id") or value.get(
        "latest_outcome_snapshot_id"
    )
    return (
        None if trade_date is None else str(trade_date),
        None if transaction_id is None else str(transaction_id),
        capture_count,
        None if outcome_snapshot_id is None else str(outcome_snapshot_id),
    )


def assess_m7_evidence_bundle(
    path: str | Path,
    *,
    previous_receipt: Mapping[str, Any] | None = None,
    expected_baseline_trade_date: str | None = None,
) -> M7EvidenceAcceptance:
    bundle_path = Path(path)
    blockers: list[str] = []
    warnings: list[str] = []

    audit = audit_evidence_bundle(
        bundle_path,
        expected_baseline_trade_date=expected_baseline_trade_date,
    )
    blockers.extend(audit.blockers)
    warnings.extend(audit.warnings)
    summary = dict(audit.summary)

    manifest: dict[str, Any] = {}
    methodology_guard: dict[str, Any] | None = None
    outcome_guard: dict[str, Any] | None = None
    qfq: dict[str, Any] | None = None
    try:
        with zipfile.ZipFile(bundle_path, "r") as archive:
            manifest = _json_member(archive, "bundle-manifest.json") or {}
            methodology_guard = _json_member(
                archive,
                "reports/m4-methodology-freeze-guard.json",
            )
            outcome_guard = _json_member(
                archive,
                "reports/m4-outcome-engine-freeze-guard.json",
            )
            qfq = _json_member(
                archive,
                "reports/m4-qfq-readiness.json",
            )
    except (OSError, zipfile.BadZipFile, ValueError) as exc:
        blockers.append(
            "acceptance_read_error:"
            + type(exc).__name__
            + ":"
            + str(exc)
        )

    if methodology_guard is None:
        blockers.append("methodology_freeze_guard_missing")
    else:
        if methodology_guard.get("status") != "frozen_match":
            blockers.append("methodology_freeze_guard_not_frozen_match")
        if int(methodology_guard.get("methodology_component_count") or 0) != 37:
            blockers.append("methodology_freeze_component_count_drift")
        if int(methodology_guard.get("error_count") or 0) != 0:
            blockers.append("methodology_freeze_guard_errors")

    if outcome_guard is None:
        blockers.append("outcome_engine_freeze_guard_missing")
    else:
        if outcome_guard.get("status") != "frozen_match":
            blockers.append("outcome_engine_freeze_guard_not_frozen_match")
        if int(outcome_guard.get("outcome_engine_component_count") or 0) != 4:
            blockers.append("outcome_engine_freeze_component_count_drift")
        if int(outcome_guard.get("error_count") or 0) != 0:
            blockers.append("outcome_engine_freeze_guard_errors")

    if qfq is None:
        blockers.append("qfq_readiness_report_missing")
    else:
        initialized = int(qfq.get("initialized_instruments") or 0)
        ready = int(qfq.get("formal_ready_after") or 0)
        failed = int(qfq.get("failed_count") or 0)
        if qfq.get("status") != "formal_qfq_ready":
            blockers.append("qfq_universe_not_formal_ready")
        if initialized <= 0 or ready != initialized or failed != 0:
            blockers.append("qfq_universe_coverage_incomplete")

    capture_count = int(summary.get("committed_capture_count") or 0)
    capture_date_raw = summary.get("latest_committed_capture_date")
    capture_date = (
        None if capture_date_raw is None else str(capture_date_raw)
    )
    transaction_raw = summary.get("latest_capture_transaction_id")
    transaction_id = (
        None if transaction_raw is None else str(transaction_raw)
    )
    outcome_snapshot_raw = summary.get("latest_outcome_snapshot_id")
    outcome_snapshot_id = (
        None
        if outcome_snapshot_raw is None
        else str(outcome_snapshot_raw)
    )

    if capture_count <= 0 or capture_date is None or transaction_id is None:
        blockers.append("no_accepted_m7_capture_state")

    prospective_count = int(
        summary.get("prospective_outcome_eligible_candidate_count") or 0
    )
    if blockers:
        accumulation_status = "blocked"
    elif capture_count == 0:
        accumulation_status = "waiting_first_future_capture"
    elif prospective_count == 0:
        accumulation_status = "accumulating_no_outcome_cohort"
    else:
        accumulation_status = "accumulating"

    classification = "new_capture"
    (
        previous_date,
        previous_transaction,
        previous_count,
        previous_outcome_snapshot,
    ) = _previous_identity(previous_receipt)
    if previous_date is not None:
        if capture_date is None or capture_date < previous_date:
            blockers.append("capture_chain_date_regression")
        elif previous_count is not None and capture_count < previous_count:
            blockers.append("capture_chain_count_regression")
        elif capture_date == previous_date:
            if previous_transaction is not None and transaction_id != previous_transaction:
                blockers.append("same_date_capture_transaction_drift")
            elif previous_count is not None and capture_count != previous_count:
                blockers.append("same_date_capture_count_drift")
            elif (
                previous_outcome_snapshot is not None
                and outcome_snapshot_id != previous_outcome_snapshot
            ):
                blockers.append("same_date_outcome_snapshot_drift")
            else:
                classification = "idempotent_rerun"
        else:
            if previous_count is not None and capture_count <= previous_count:
                blockers.append("new_date_without_capture_count_growth")
            classification = "new_capture"

    if manifest.get("authoritative_evidence_modified") is not False:
        blockers.append("authoritative_evidence_modified_boundary_invalid")

    blockers = sorted(set(blockers))
    warnings = sorted(set(warnings))
    status = "accepted" if not blockers else "not_ready"
    if blockers:
        accumulation_status = "blocked"
        classification = "not_ready"

    summary.update({
        "bundle_sha256": (
            _sha256_file(bundle_path)
            if bundle_path.is_file()
            else None
        ),
        "bundle_size_bytes": (
            bundle_path.stat().st_size
            if bundle_path.is_file()
            else None
        ),
        "bundle_generation_code_head": (
            manifest.get("bundle_generation_code_head")
            or manifest.get("code_head")
        ),
        "latest_capture_code_head": (
            manifest.get("latest_capture_code_head")
            or summary.get("latest_capture_code_head")
        ),
        "accumulation_status": accumulation_status,
        "classification": classification,
        "statistical_inference_allowed": False,
        "alpha_inference_allowed": False,
        "win_rate_inference_allowed": False,
        "profitability_inference_allowed": False,
        "is_trade_instruction": False,
    })

    receipt = None
    if status == "accepted":
        receipt = {
            "schema_version": 1,
            "status": "accepted",
            "classification": classification,
            "bundle_sha256": summary["bundle_sha256"],
            "bundle_size_bytes": summary["bundle_size_bytes"],
            "bundle_generation_code_head": summary[
                "bundle_generation_code_head"
            ],
            "latest_capture_code_head": summary[
                "latest_capture_code_head"
            ],
            "trade_date": capture_date,
            "latest_capture_transaction_id": transaction_id,
            "committed_capture_count": capture_count,
            "latest_outcome_snapshot_id": outcome_snapshot_id,
            "accumulation_status": accumulation_status,
            "warnings": warnings,
            "authority_boundary": {
                "authoritative_evidence_modified": False,
                "statistical_inference_allowed": False,
                "alpha_inference_allowed": False,
                "win_rate_inference_allowed": False,
                "profitability_inference_allowed": False,
                "is_trade_instruction": False,
            },
        }

    return M7EvidenceAcceptance(
        status=status,
        classification=classification,
        bundle_path=str(bundle_path),
        blocker_count=len(blockers),
        warning_count=len(warnings),
        blockers=tuple(blockers),
        warnings=tuple(warnings),
        summary=summary,
        receipt=receipt,
    )
