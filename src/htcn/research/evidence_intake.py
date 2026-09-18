from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
import json
import zipfile

from .capture_transaction import (
    committed_capture_view,
    committed_followup_view,
    frozen_legacy_baseline_present,
    frozen_legacy_baseline_through_date,
    read_committed_captures,
    read_frozen_legacy_baseline,
)
from .evidence_bundle import verify_evidence_bundle
from .lifecycle_transitions import build_transition_report
from .prospective_observations import build_prospective_observation_report
from .snapshot_manifest import resolve_capture_timeline


@dataclass(frozen=True, slots=True)
class EvidenceBundleAudit:
    status: str
    bundle_path: str
    blocker_count: int
    warning_count: int
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    summary: dict[str, Any]

    def as_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["blockers"] = list(self.blockers)
        payload["warnings"] = list(self.warnings)
        return payload


def _json_member(archive: zipfile.ZipFile, name: str) -> dict[str, Any] | None:
    try:
        raw = archive.read(name)
    except KeyError:
        return None
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError(f"invalid JSON bundle member: {name}")
    if not isinstance(value, dict):
        raise ValueError(f"bundle JSON member is not an object: {name}")
    return value


def _write_authoritative_tree(
    archive: zipfile.ZipFile,
    root: Path,
) -> None:
    captures = root / "captures"
    captures.mkdir(parents=True, exist_ok=True)
    for info in archive.infolist():
        name = info.filename
        if name == "authoritative/legacy_baseline.json":
            target = captures / "legacy_baseline.json"
        elif name.startswith("authoritative/captures/") and name.endswith(".json"):
            target = captures / Path(name).name
        else:
            continue
        target.write_bytes(archive.read(name))


def _report_fields_match(
    included: dict[str, Any],
    recomputed: dict[str, Any],
    fields: tuple[str, ...],
) -> list[str]:
    mismatches: list[str] = []
    for field in fields:
        if included.get(field) != recomputed.get(field):
            mismatches.append(field)
    return mismatches


def audit_evidence_bundle(
    path: str | Path,
    *,
    expected_baseline_trade_date: str | None = None,
) -> EvidenceBundleAudit:
    bundle_path = Path(path)
    blockers: list[str] = []
    warnings: list[str] = []
    summary: dict[str, Any] = {
        "alpha_inference_allowed": False,
        "is_trade_instruction": False,
        "authoritative_evidence_modified": False,
    }

    transport = verify_evidence_bundle(bundle_path)
    summary["transport_verification"] = transport.as_payload()
    if transport.status != "valid":
        blockers.append("transport_integrity_invalid")
        return EvidenceBundleAudit(
            status="not_ready",
            bundle_path=str(bundle_path),
            blocker_count=len(blockers),
            warning_count=len(warnings),
            blockers=tuple(blockers),
            warnings=tuple(warnings),
            summary=summary,
        )

    if "bundle_reports_evidence_health_blocked" in transport.warnings:
        warnings.append("bundle_reports_evidence_health_blocked")
        blockers.append("bundle_evidence_health_blocked")

    manifest = transport.manifest or {}
    summary["bundle_status"] = manifest.get("status")
    summary["bundle_methodology_contract_version"] = manifest.get(
        "methodology_contract_version"
    )
    summary["bundle_methodology_fingerprint"] = manifest.get(
        "methodology_fingerprint"
    )

    try:
        with zipfile.ZipFile(bundle_path, "r") as archive, TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            _write_authoritative_tree(archive, temp_root)
            transaction_root = temp_root / "captures"

            committed = read_committed_captures(transaction_root)
            baseline_present = frozen_legacy_baseline_present(transaction_root)
            baseline_rows = read_frozen_legacy_baseline(transaction_root)
            baseline_through = frozen_legacy_baseline_through_date(transaction_root)

            if committed and not baseline_present:
                blockers.append("committed_chain_missing_frozen_baseline")

            if expected_baseline_trade_date is not None:
                if baseline_through != expected_baseline_trade_date:
                    blockers.append("unexpected_frozen_baseline_trade_date")

            if not committed:
                blockers.append("no_post_baseline_committed_capture")
                journal_rows = baseline_rows
                manifest_rows: list[dict[str, Any]] = []
            else:
                journal_rows, manifest_rows = committed_capture_view(
                    legacy_journal_rows=baseline_rows,
                    capture_rows=committed,
                )
            followup_rows = committed_followup_view(committed)

            timeline = resolve_capture_timeline(
                journal_rows,
                manifest_rows,
                legacy_baseline_trade_date=baseline_through,
            )
            transition = build_transition_report(
                journal_rows,
                captured_dates=timeline.dates,
            )
            observation = build_prospective_observation_report(
                journal_rows,
                manifest_rows=manifest_rows,
                followup_rows=followup_rows,
                legacy_baseline_trade_date=baseline_through,
            )

            methodology_pairs = {
                (
                    item.get("methodology_contract_version"),
                    str(item.get("methodology_fingerprint") or ""),
                )
                for item in committed
            }
            chain_methodology_version = None
            chain_methodology_fingerprint = None
            if len(methodology_pairs) > 1:
                blockers.append("mixed_methodology_inside_committed_chain")
            elif len(methodology_pairs) == 1:
                (
                    chain_methodology_version,
                    chain_methodology_fingerprint,
                ) = next(iter(methodology_pairs))
                if (
                    manifest.get("methodology_contract_version")
                    != chain_methodology_version
                    or str(manifest.get("methodology_fingerprint") or "")
                    != chain_methodology_fingerprint
                ):
                    blockers.append("bundle_methodology_differs_from_committed_chain")

            if len(committed) != int(manifest.get("committed_capture_count") or 0):
                blockers.append("bundle_committed_capture_count_drift")
            if committed:
                latest_capture = committed[-1]
                if (
                    manifest.get("latest_committed_capture_date")
                    != latest_capture.get("as_of_trade_date")
                ):
                    blockers.append("bundle_latest_capture_date_drift")
                if (
                    manifest.get("latest_capture_transaction_id")
                    != latest_capture.get("transaction_id")
                ):
                    blockers.append("bundle_latest_transaction_id_drift")
                if manifest.get("code_head") != latest_capture.get("code_head"):
                    blockers.append("bundle_code_head_differs_from_latest_capture")
                if manifest.get("worktree_clean") is not True:
                    blockers.append("bundle_worktree_not_clean")

            health = _json_member(archive, "reports/m4-evidence-health.json")
            if health is None:
                warnings.append("evidence_health_report_missing")
            else:
                if int(health.get("blocker_count") or 0) > 0:
                    blockers.append("evidence_health_report_has_blockers")
                if committed:
                    latest_capture = committed[-1]
                    if (
                        health.get("latest_committed_capture_date")
                        != latest_capture.get("as_of_trade_date")
                    ):
                        blockers.append("evidence_health_latest_capture_drift")
                    if (
                        health.get("authoritative_methodology_fingerprint")
                        != chain_methodology_fingerprint
                    ):
                        blockers.append("evidence_health_methodology_drift")
                    if (
                        health.get("authoritative_methodology_contract_version")
                        != chain_methodology_version
                    ):
                        blockers.append("evidence_health_methodology_version_drift")

            included_transition = _json_member(
                archive,
                "reports/m4-lifecycle-transitions.json",
            )
            if included_transition is None:
                warnings.append("transition_report_missing_recomputed_from_authoritative")
            else:
                transition_fields = (
                    "status",
                    "date_count",
                    "baseline_trade_date",
                    "latest_trade_date",
                    "journal_row_count",
                    "latest_candidate_count",
                    "prospective_outcome_eligible_row_count",
                    "cohort_counts",
                    "transition_counts",
                    "lifecycle_pair_counts",
                    "latest_lifecycle_state_counts",
                    "normalized_rows",
                    "transitions",
                )
                mismatch = _report_fields_match(
                    included_transition,
                    transition,
                    transition_fields,
                )
                if mismatch:
                    blockers.append(
                        "transition_report_drift:" + ",".join(sorted(mismatch))
                    )
                if (
                    included_transition.get("methodology_fingerprint")
                    != chain_methodology_fingerprint
                ):
                    blockers.append("transition_report_methodology_drift")
                if (
                    included_transition.get("methodology_contract_version")
                    != chain_methodology_version
                ):
                    blockers.append("transition_report_methodology_version_drift")

            included_observation = _json_member(
                archive,
                "reports/m4-prospective-observations.json",
            )
            if included_observation is None:
                warnings.append("observation_report_missing_recomputed_from_authoritative")
            else:
                observation_fields = (
                    "status",
                    "captured_dates",
                    "prospective_candidate_count",
                    "observation_count",
                    "scanner_presence_counts",
                    "lifecycle_observation_counts",
                    "market_observation_counts",
                    "candidate_summaries",
                    "observations",
                )
                mismatch = _report_fields_match(
                    included_observation,
                    observation,
                    observation_fields,
                )
                if mismatch:
                    blockers.append(
                        "observation_report_drift:" + ",".join(sorted(mismatch))
                    )
                if (
                    included_observation.get("methodology_fingerprint")
                    != chain_methodology_fingerprint
                ):
                    blockers.append("observation_report_methodology_drift")
                if (
                    included_observation.get("methodology_contract_version")
                    != chain_methodology_version
                ):
                    blockers.append("observation_report_methodology_version_drift")

            all_rows = [dict(row) for row in transition.get("normalized_rows") or []]
            latest_trade_date = transition.get("latest_trade_date")
            latest_rows = [
                row
                for row in all_rows
                if row.get("as_of_trade_date") == latest_trade_date
            ]
            prospective_keys = sorted({
                str(row.get("candidate_key"))
                for row in all_rows
                if row.get("enrollment_state") == "prospective_new"
            })
            eligible_keys = sorted({
                str(row.get("candidate_key"))
                for row in all_rows
                if row.get("prospective_outcome_eligible") is True
            })
            suspension_rows = [
                row
                for row in all_rows
                if row.get("market_observation_status")
                == "confirmed_full_day_suspended"
            ]

            lifecycle_latest = Counter(
                str(row.get("source_lifecycle_state"))
                for row in latest_rows
            )
            enrollment_latest = Counter(
                str(row.get("enrollment_state"))
                for row in latest_rows
            )

            summary.update({
                "frozen_baseline_present": baseline_present,
                "frozen_baseline_through_trade_date": baseline_through,
                "frozen_baseline_row_count": len(baseline_rows),
                "committed_capture_count": len(committed),
                "committed_capture_dates": [
                    str(item.get("as_of_trade_date"))
                    for item in committed
                ],
                "latest_committed_capture_date": (
                    None
                    if not committed
                    else committed[-1].get("as_of_trade_date")
                ),
                "latest_capture_transaction_id": (
                    None
                    if not committed
                    else committed[-1].get("transaction_id")
                ),
                "chain_methodology_contract_version": chain_methodology_version,
                "chain_methodology_fingerprint": chain_methodology_fingerprint,
                "capture_timeline": list(timeline.dates),
                "transition_status": transition.get("status"),
                "latest_candidate_count": transition.get("latest_candidate_count"),
                "transition_counts": transition.get("transition_counts"),
                "latest_lifecycle_state_counts": dict(sorted(lifecycle_latest.items())),
                "latest_enrollment_state_counts": dict(sorted(enrollment_latest.items())),
                "prospective_new_candidate_count": len(prospective_keys),
                "prospective_new_candidate_keys": prospective_keys,
                "prospective_outcome_eligible_candidate_count": len(eligible_keys),
                "prospective_outcome_eligible_candidate_keys": eligible_keys,
                "prospective_observation_status": observation.get("status"),
                "prospective_observation_count": observation.get("observation_count"),
                "cohort_followup_row_count": len(followup_rows),
                "confirmed_full_day_suspended_row_count": len(suspension_rows),
            })

            if committed:
                first_capture = str(committed[0].get("as_of_trade_date") or "")
                if baseline_through is not None and first_capture <= baseline_through:
                    blockers.append("first_committed_capture_not_after_frozen_baseline")

            if manifest.get("status") == "transport_bundle_ready" and blockers:
                blockers.append("bundle_claimed_ready_but_intake_found_blockers")

    except (
        OSError,
        ValueError,
        zipfile.BadZipFile,
        json.JSONDecodeError,
    ) as exc:
        blockers.append(
            "authoritative_intake_error:"
            + type(exc).__name__
            + ":"
            + str(exc)
        )

    # Keep the result deterministic for the same bundle contents.
    blockers = sorted(set(blockers))
    warnings = sorted(set(warnings))
    status = (
        "not_ready"
        if blockers
        else "ready_with_warnings"
        if warnings
        else "ready"
    )
    return EvidenceBundleAudit(
        status=status,
        bundle_path=str(bundle_path),
        blocker_count=len(blockers),
        warning_count=len(warnings),
        blockers=tuple(blockers),
        warnings=tuple(warnings),
        summary=summary,
    )
