from __future__ import annotations

import json
import zipfile
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pandas as pd

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
from .outcome_engine_identity import build_outcome_engine_identity
from .outcome_evaluator import evaluate_candidate_outcome
from .outcome_protocol import load_outcome_protocol, load_outcome_protocol_v2
from .outcome_snapshot import read_outcome_snapshots
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


def _write_outcome_tree(
    archive: zipfile.ZipFile,
    root: Path,
) -> None:
    outcomes = root / "outcomes"
    outcomes.mkdir(parents=True, exist_ok=True)
    for info in archive.infolist():
        name = info.filename
        if not (
            name.startswith("outcomes/")
            and name.endswith(".json")
        ):
            continue
        target = outcomes / Path(name).name
        target.write_bytes(archive.read(name))


def _observation_panel_through(
    *,
    baseline_rows: list[dict[str, Any]],
    baseline_through: str | None,
    committed: list[dict[str, Any]],
    outcome_as_of_trade_date: str,
) -> dict[str, Any]:
    selected = [
        item
        for item in committed
        if str(item.get("as_of_trade_date") or "")
        <= outcome_as_of_trade_date
    ]
    if not selected:
        return {
            "schema_version": 4,
            "status": "no_outcome_cohort",
            "candidate_summaries": [],
            "observations": [],
        }
    journal_rows, manifest_rows = committed_capture_view(
        legacy_journal_rows=baseline_rows,
        capture_rows=selected,
    )
    followup_rows = committed_followup_view(selected)
    return build_prospective_observation_report(
        journal_rows,
        manifest_rows=manifest_rows,
        followup_rows=followup_rows,
        legacy_baseline_trade_date=baseline_through,
    )


def _outcome_protocol_bundle_member(protocol_id: str) -> str:
    mapping = {
        "m4-outcome-v1": "protocols/m4-outcome-protocol-v1.json",
        "m4-outcome-v2": "protocols/m4-outcome-protocol-v2.json",
    }
    try:
        return mapping[protocol_id]
    except KeyError as exc:
        raise ValueError(
            f"unsupported bundled outcome protocol id: {protocol_id}"
        ) from exc


def _outcome_result_without_transport_warning(
    value: dict[str, Any],
) -> dict[str, Any]:
    out = dict(value)
    out.pop("market_data_warning", None)
    return out


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
            _write_outcome_tree(archive, temp_root)
            transaction_root = temp_root / "captures"
            outcome_root = temp_root / "outcomes"

            committed = read_committed_captures(transaction_root)
            outcome_snapshots = read_outcome_snapshots(outcome_root)
            active_outcome_protocol, active_outcome_identity = (
                load_outcome_protocol_v2()
            )
            current_outcome_engine = build_outcome_engine_identity()
            baseline_present = frozen_legacy_baseline_present(transaction_root)
            baseline_rows = read_frozen_legacy_baseline(transaction_root)
            baseline_through = frozen_legacy_baseline_through_date(transaction_root)

            if committed and not baseline_present:
                blockers.append("committed_chain_missing_frozen_baseline")

            if (
                expected_baseline_trade_date is not None
                and baseline_through != expected_baseline_trade_date
            ):
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

            bundled_active_protocol = _json_member(
                archive,
                "protocols/m4-outcome-protocol-v2.json",
            )
            bundle_declares_outcome_contract = any(
                key in manifest
                for key in (
                    "active_outcome_protocol_id",
                    "active_outcome_protocol_fingerprint",
                    "current_outcome_engine_contract_version",
                    "current_outcome_engine_fingerprint",
                    "outcome_snapshot_count",
                )
            )
            if bundled_active_protocol is None:
                if outcome_snapshots or bundle_declares_outcome_contract:
                    blockers.append(
                        "outcome_protocol_bundle_member_missing"
                    )
                else:
                    warnings.append(
                        "legacy_bundle_without_outcome_protocol_member"
                    )
            elif bundled_active_protocol != active_outcome_protocol:
                blockers.append("outcome_protocol_bundle_member_drift")

            if (
                manifest.get("active_outcome_protocol_id")
                not in {None, active_outcome_identity.protocol_id}
            ):
                blockers.append("bundle_active_outcome_protocol_id_drift")
            if (
                manifest.get("active_outcome_protocol_fingerprint")
                not in {None, active_outcome_identity.fingerprint}
            ):
                blockers.append(
                    "bundle_active_outcome_protocol_fingerprint_drift"
                )
            if (
                manifest.get("current_outcome_engine_contract_version")
                not in {None, current_outcome_engine.contract_version}
            ):
                blockers.append("bundle_current_outcome_engine_version_drift")
            if (
                manifest.get("current_outcome_engine_fingerprint")
                not in {None, current_outcome_engine.fingerprint}
            ):
                blockers.append(
                    "bundle_current_outcome_engine_fingerprint_drift"
                )

            manifest_outcome_error = str(
                manifest.get("outcome_snapshot_read_error") or ""
            )
            if manifest_outcome_error:
                blockers.append("bundle_outcome_snapshot_read_error")

            manifest_outcome_count = int(
                manifest.get("outcome_snapshot_count") or 0
            )
            if manifest_outcome_count != len(outcome_snapshots):
                blockers.append("bundle_outcome_snapshot_count_drift")

            latest_outcome = (
                None if not outcome_snapshots else outcome_snapshots[-1]
            )
            if latest_outcome is not None:
                if (
                    manifest.get("latest_outcome_as_of_trade_date")
                    != latest_outcome.get("outcome_as_of_trade_date")
                ):
                    blockers.append("bundle_latest_outcome_date_drift")
                if (
                    manifest.get("latest_outcome_snapshot_id")
                    != latest_outcome.get("snapshot_id")
                ):
                    blockers.append("bundle_latest_outcome_id_drift")

            outcome_status_counts: Counter[str] = Counter()
            outcome_result_count = 0
            for snapshot in outcome_snapshots:
                snapshot_as_of = str(
                    snapshot.get("outcome_as_of_trade_date") or ""
                )
                if not snapshot_as_of:
                    blockers.append("outcome_snapshot_missing_as_of")
                    continue
                snapshot_protocol_id = str(
                    snapshot.get("outcome_protocol_id") or ""
                )
                try:
                    snapshot_protocol, snapshot_protocol_identity = (
                        load_outcome_protocol(snapshot_protocol_id)
                    )
                except Exception as exc:
                    blockers.append(
                        "outcome_snapshot_protocol_unavailable:"
                        + snapshot_protocol_id
                        + ":"
                        + type(exc).__name__
                        + ":"
                        + str(exc)
                    )
                    continue
                bundled_snapshot_protocol = _json_member(
                    archive,
                    _outcome_protocol_bundle_member(
                        snapshot_protocol_id
                    ),
                )
                if bundled_snapshot_protocol is None:
                    blockers.append(
                        "outcome_snapshot_protocol_member_missing:"
                        + snapshot_protocol_id
                    )
                elif bundled_snapshot_protocol != snapshot_protocol:
                    blockers.append(
                        "outcome_snapshot_protocol_member_drift:"
                        + snapshot_protocol_id
                    )
                if (
                    str(
                        snapshot.get(
                            "outcome_protocol_fingerprint"
                        ) or ""
                    )
                    != snapshot_protocol_identity.fingerprint
                ):
                    blockers.append(
                        "outcome_snapshot_protocol_fingerprint_drift"
                    )
                if (
                    int(
                        snapshot.get(
                            "outcome_engine_contract_version"
                        ) or 0
                    )
                    != current_outcome_engine.contract_version
                    or str(
                        snapshot.get("outcome_engine_fingerprint") or ""
                    )
                    != current_outcome_engine.fingerprint
                ):
                    blockers.append(
                        "outcome_snapshot_engine_identity_drift"
                    )
                if (
                    str(
                        snapshot.get(
                            "capture_methodology_fingerprint"
                        ) or ""
                    )
                    != str(chain_methodology_fingerprint or "")
                ):
                    blockers.append(
                        "outcome_snapshot_methodology_drift"
                    )

                panel_as_of = _observation_panel_through(
                    baseline_rows=baseline_rows,
                    baseline_through=baseline_through,
                    committed=committed,
                    outcome_as_of_trade_date=snapshot_as_of,
                )
                summaries_as_of = {
                    str(item.get("candidate_key") or ""): dict(item)
                    for item in panel_as_of.get(
                        "candidate_summaries"
                    ) or []
                    if item.get("candidate_key")
                }
                stored_results = {
                    str(item.get("candidate_key") or ""): dict(item)
                    for item in snapshot.get("results") or []
                    if item.get("candidate_key")
                }
                if set(stored_results) != set(summaries_as_of):
                    blockers.append(
                        "outcome_snapshot_candidate_set_drift:"
                        + snapshot_as_of
                    )
                    continue

                for candidate_key in sorted(stored_results):
                    stored = stored_results[candidate_key]
                    path_rows = stored.get("market_path_rows")
                    if not isinstance(path_rows, list) or not path_rows:
                        blockers.append(
                            "outcome_snapshot_missing_market_path:"
                            + candidate_key
                        )
                        continue
                    try:
                        recomputed = evaluate_candidate_outcome(
                            summaries_as_of[candidate_key],
                            pd.DataFrame(path_rows),
                            outcome_as_of_trade_date=snapshot_as_of,
                            current_price_mode=str(
                                stored.get("current_price_mode") or ""
                            ),
                            current_price_basis_id=str(
                                stored.get("current_price_basis_id") or ""
                            ),
                            methodology_fingerprint=str(
                                chain_methodology_fingerprint or ""
                            ),
                            protocol=snapshot_protocol,
                        )
                    except Exception as exc:
                        blockers.append(
                            "outcome_result_recompute_error:"
                            + candidate_key
                            + ":"
                            + type(exc).__name__
                            + ":"
                            + str(exc)
                        )
                        continue

                    if (
                        _outcome_result_without_transport_warning(stored)
                        != recomputed
                    ):
                        blockers.append(
                            "outcome_result_recompute_drift:"
                            + candidate_key
                        )
                    outcome_status_counts[
                        str(stored.get("status") or "unknown")
                    ] += 1
                    outcome_result_count += 1

            latest_cohort_keys = {
                str(item.get("candidate_key") or "")
                for item in observation.get("candidate_summaries") or []
                if item.get("candidate_key")
            }
            if latest_cohort_keys and latest_outcome is None:
                blockers.append(
                    "outcome_snapshot_missing_for_enrolled_cohort"
                )
            if latest_outcome is not None and committed and (
                str(latest_outcome.get("outcome_as_of_trade_date") or "")
                < str(committed[-1].get("as_of_trade_date") or "")
            ):
                blockers.append(
                    "latest_outcome_predates_latest_capture"
                )

            included_outcome = _json_member(
                archive,
                "reports/m4-outcome-v2.json",
            )
            if included_outcome is None:
                warnings.append("outcome_report_missing")
            elif latest_outcome is not None:
                expected_report_fields = {
                    "status": "ready",
                    "outcome_as_of_trade_date": latest_outcome.get(
                        "outcome_as_of_trade_date"
                    ),
                    "outcome_protocol_id": active_outcome_identity.protocol_id,
                    "outcome_protocol_fingerprint": (
                        active_outcome_identity.fingerprint
                    ),
                    "capture_methodology_fingerprint": (
                        chain_methodology_fingerprint
                    ),
                    "candidate_count": len(
                        latest_outcome.get("results") or []
                    ),
                    "outcome_snapshot_id": latest_outcome.get(
                        "snapshot_id"
                    ),
                    "results": latest_outcome.get("results") or [],
                }
                report_drift = [
                    field
                    for field, expected in expected_report_fields.items()
                    if included_outcome.get(field) != expected
                ]
                if report_drift:
                    blockers.append(
                        "outcome_report_drift:"
                        + ",".join(sorted(report_drift))
                    )
            elif latest_cohort_keys:
                blockers.append(
                    "outcome_report_present_without_required_snapshot"
                )
            elif included_outcome.get("status") not in {
                "no_outcome_cohort",
                "no_authoritative_future_capture",
            }:
                blockers.append("outcome_report_status_drift")

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
            basis_drift_summaries = [
                dict(item)
                for item in observation.get("candidate_summaries") or []
                if int(item.get("price_basis_drift_snapshot_count") or 0) > 0
            ]
            basis_drift_keys = sorted(
                str(item.get("candidate_key") or "")
                for item in basis_drift_summaries
                if item.get("candidate_key")
            )
            if basis_drift_keys:
                warnings.append(
                    "price_basis_drift_present_future_outcome_rebase_required"
                )

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
                "price_basis_drift_candidate_count": len(basis_drift_keys),
                "price_basis_drift_candidate_keys": basis_drift_keys,
                "cohort_followup_row_count": len(followup_rows),
                "confirmed_full_day_suspended_row_count": len(suspension_rows),
                "outcome_protocol_id": active_outcome_identity.protocol_id,
                "outcome_protocol_fingerprint": (
                    active_outcome_identity.fingerprint
                ),
                "current_outcome_engine_contract_version": (
                    current_outcome_engine.contract_version
                ),
                "current_outcome_engine_fingerprint": (
                    current_outcome_engine.fingerprint
                ),
                "outcome_snapshot_count": len(outcome_snapshots),
                "latest_outcome_as_of_trade_date": (
                    None
                    if latest_outcome is None
                    else latest_outcome.get(
                        "outcome_as_of_trade_date"
                    )
                ),
                "latest_outcome_snapshot_id": (
                    None
                    if latest_outcome is None
                    else latest_outcome.get("snapshot_id")
                ),
                "outcome_result_count": outcome_result_count,
                "outcome_status_counts": dict(
                    sorted(outcome_status_counts.items())
                ),
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
