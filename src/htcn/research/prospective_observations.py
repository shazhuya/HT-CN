from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any, Iterable

from .lifecycle_transitions import normalize_journal_rows
from .snapshot_manifest import resolve_capture_timeline


@dataclass(frozen=True, slots=True)
class ProspectiveObservation:
    candidate_key: str
    instrument_id: str
    outcome_enrollment_trade_date: str
    observation_trade_date: str
    captured_snapshot_index: int
    scanner_presence: str
    consecutive_absent_snapshots: int
    pattern_state: str | None
    source_lifecycle_state: str | None
    action_state: str | None
    execution_context_gate: str | None
    context_integrity_summary: str | None
    next_key_price: float | None
    next_key_price_role: str | None
    source_terminal_trade_date: str | None
    as_of_open: float | None
    as_of_high: float | None
    as_of_low: float | None
    as_of_close: float | None
    as_of_volume: float | None
    evidence_only: bool = True
    is_trade_instruction: bool = False
    alpha_inference_allowed: bool = False

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_prospective_observation_report(
    rows: Iterable[dict[str, Any]],
    *,
    manifest_rows: Iterable[dict[str, Any]] | None = None,
    legacy_baseline_trade_date: str | None = None,
) -> dict[str, Any]:
    materialized = [dict(row) for row in rows]
    manifest_materialized = (
        None
        if manifest_rows is None
        else [dict(row) for row in manifest_rows]
    )
    timeline = resolve_capture_timeline(
        materialized,
        manifest_materialized,
        legacy_baseline_trade_date=legacy_baseline_trade_date,
    )
    dates = list(timeline.dates)
    baseline = dates[0] if dates else None
    normalized = normalize_journal_rows(
        materialized,
        baseline_trade_date=baseline,
    )
    if not normalized and not dates:
        return {
            "schema_version": 1,
            "status": "empty",
            "captured_dates": [],
            "prospective_candidate_count": 0,
            "observation_count": 0,
            "observations": [],
            "candidate_summaries": [],
            "interpretation": {
                "capture_timeline_source": timeline.source,
                "legacy_pre_manifest_dates": list(timeline.legacy_pre_manifest_dates),
                "captured_snapshot_index_is_trade_session_index": False,
                "scanner_absence_is_invalidation": False,
                "return_metrics_computed": False,
                "alpha_inference_allowed": False,
            },
        }

    by_date: dict[str, dict[str, dict[str, Any]]] = {}
    for as_of in dates:
        by_date[as_of] = {
            str(row["candidate_key"]): row
            for row in normalized
            if str(row["as_of_trade_date"]) == as_of
        }

    enrollment: dict[str, str] = {}
    instrument_by_key: dict[str, str] = {}
    for row in normalized:
        key = str(row["candidate_key"])
        instrument_by_key.setdefault(key, str(row.get("instrument_id") or ""))
        enrolled = row.get("outcome_enrollment_trade_date")
        if enrolled:
            value = str(enrolled)
            previous = enrollment.get(key)
            if previous is not None and previous != value:
                raise ValueError(
                    f"candidate {key} outcome_enrollment_trade_date drift: "
                    f"{previous} != {value}"
                )
            enrollment[key] = value

    observations: list[ProspectiveObservation] = []
    candidate_summaries: list[dict[str, Any]] = []

    for key in sorted(enrollment):
        enrolled = enrollment[key]
        if enrolled not in dates:
            raise ValueError(
                f"candidate {key} enrollment date {enrolled} is not a captured snapshot date"
            )
        observation_dates = [value for value in dates if value >= enrolled]
        absent_streak = 0
        ever_absent = False
        first_absent: str | None = None
        first_reappeared: str | None = None
        first_terminal: str | None = None
        first_state_date: dict[str, str] = {}
        present_count = 0
        absent_count = 0

        for captured_index, as_of in enumerate(observation_dates):
            row = by_date[as_of].get(key)
            if row is None:
                absent_streak += 1
                absent_count += 1
                ever_absent = True
                if first_absent is None:
                    first_absent = as_of
                observations.append(
                    ProspectiveObservation(
                        candidate_key=key,
                        instrument_id=instrument_by_key[key],
                        outcome_enrollment_trade_date=enrolled,
                        observation_trade_date=as_of,
                        captured_snapshot_index=captured_index,
                        scanner_presence="absent",
                        consecutive_absent_snapshots=absent_streak,
                        pattern_state=None,
                        source_lifecycle_state=None,
                        action_state=None,
                        execution_context_gate=None,
                        context_integrity_summary=None,
                        next_key_price=None,
                        next_key_price_role=None,
                        source_terminal_trade_date=None,
                        as_of_open=None,
                        as_of_high=None,
                        as_of_low=None,
                        as_of_close=None,
                        as_of_volume=None,
                    )
                )
                continue

            if ever_absent and absent_streak > 0 and first_reappeared is None:
                first_reappeared = as_of
            absent_streak = 0
            present_count += 1

            terminal_raw = row.get("source_terminal_trade_date")
            terminal = None if terminal_raw is None else str(terminal_raw)
            if terminal is not None:
                if date.fromisoformat(terminal) < date.fromisoformat(enrolled):
                    raise ValueError(
                        f"candidate {key} Source Terminal {terminal} predates outcome enrollment {enrolled}"
                    )
                if first_terminal is None:
                    first_terminal = terminal

            lifecycle = str(row.get("source_lifecycle_state") or "")
            if lifecycle:
                first_state_date.setdefault(lifecycle, as_of)

            observations.append(
                ProspectiveObservation(
                    candidate_key=key,
                    instrument_id=instrument_by_key[key],
                    outcome_enrollment_trade_date=enrolled,
                    observation_trade_date=as_of,
                    captured_snapshot_index=captured_index,
                    scanner_presence="present",
                    consecutive_absent_snapshots=0,
                    pattern_state=(
                        None if row.get("pattern_state") is None else str(row.get("pattern_state"))
                    ),
                    source_lifecycle_state=lifecycle or None,
                    action_state=(
                        None if row.get("action_state") is None else str(row.get("action_state"))
                    ),
                    execution_context_gate=(
                        None
                        if row.get("execution_context_gate") is None
                        else str(row.get("execution_context_gate"))
                    ),
                    context_integrity_summary=(
                        None
                        if row.get("context_integrity_summary") is None
                        else str(row.get("context_integrity_summary"))
                    ),
                    next_key_price=_float_or_none(row.get("next_key_price")),
                    next_key_price_role=(
                        None
                        if row.get("next_key_price_role") is None
                        else str(row.get("next_key_price_role"))
                    ),
                    source_terminal_trade_date=terminal,
                    as_of_open=_float_or_none(row.get("as_of_open")),
                    as_of_high=_float_or_none(row.get("as_of_high")),
                    as_of_low=_float_or_none(row.get("as_of_low")),
                    as_of_close=_float_or_none(row.get("as_of_close")),
                    as_of_volume=_float_or_none(row.get("as_of_volume")),
                )
            )

        candidate_summaries.append({
            "candidate_key": key,
            "instrument_id": instrument_by_key[key],
            "outcome_enrollment_trade_date": enrolled,
            "captured_snapshot_count": len(observation_dates),
            "present_snapshot_count": present_count,
            "absent_snapshot_count": absent_count,
            "first_scanner_absent_date": first_absent,
            "first_scanner_reappeared_date": first_reappeared,
            "first_source_terminal_trade_date": first_terminal,
            "first_lifecycle_state_observed": dict(sorted(first_state_date.items())),
        })

    presence_counts = Counter(item.scanner_presence for item in observations)
    lifecycle_counts = Counter(
        item.source_lifecycle_state
        for item in observations
        if item.source_lifecycle_state is not None
    )

    return {
        "schema_version": 1,
        "status": "no_outcome_cohort" if not enrollment else "observations_available",
        "captured_dates": dates,
        "prospective_candidate_count": len(enrollment),
        "observation_count": len(observations),
        "scanner_presence_counts": dict(sorted(presence_counts.items())),
        "lifecycle_observation_counts": dict(sorted(lifecycle_counts.items())),
        "candidate_summaries": candidate_summaries,
        "observations": [item.as_payload() for item in observations],
        "interpretation": {
            "capture_timeline_source": timeline.source,
            "legacy_pre_manifest_dates": list(timeline.legacy_pre_manifest_dates),
            "captured_snapshot_index_is_trade_session_index": False,
            "scanner_absence_is_invalidation": False,
            "return_metrics_computed": False,
            "profit_threshold_defined": False,
            "alpha_inference_allowed": False,
            "is_trade_instruction": False,
        },
    }
