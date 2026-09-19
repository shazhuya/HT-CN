from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any

from htcn.app.operator_history import query_operator_history

WORKFLOW_REVIEW_ORDER = (
    "execution_evaluation",
    "reaction_observation",
    "waiting",
    "evidence_insufficient",
    "disappeared_candidate",
)

CHANGE_TYPE_ORDER = (
    "new_candidate",
    "disappeared_candidate",
    "action_state_changed",
    "lifecycle_state_changed",
    "pattern_state_changed",
    "next_key_changed",
    "execution_gate_changed",
    "context_cautions_changed",
)


@dataclass(frozen=True, slots=True)
class DailyReviewDigestContract:
    version: int = 1
    semantics: str = "product_change_triage_only"
    source: str = "m5_operator_history_latest_revision"
    ordering_mode: str = (
        "workflow_bucket_then_change_type_order_then_instrument"
    )
    transparent_workflow_order: bool = True
    exhaustive_changes: bool = True
    authoritative_transition: bool = False
    authoritative_evidence: bool = False
    writes_m4_evidence: bool = False
    predictive_score_used: bool = False
    historical_outcome_used_for_ranking: bool = False
    alpha_inference_allowed: bool = False
    is_trade_instruction: bool = False
    mutates_harmonic_identity: bool = False
    mutates_source_raw_prz: bool = False
    owns_lifecycle: bool = False

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


def _validate_history_payload(payload: dict[str, Any]) -> None:
    if int(payload.get("schema_version") or 0) != 1:
        raise ValueError("operator history schema mismatch")
    required_false = (
        "authoritative_evidence",
        "writes_m4_evidence",
        "historical_outcome_used_for_ranking",
        "alpha_inference_allowed",
        "is_trade_instruction",
    )
    for field in required_false:
        if payload.get(field) is not False:
            raise ValueError(
                f"operator history boundary violation: {field}"
            )


def _change_type_sort_key(change_types: list[str]) -> tuple[int, ...]:
    rank = {value: index for index, value in enumerate(CHANGE_TYPE_ORDER)}
    return tuple(sorted(rank.get(value, 999) for value in change_types))


def _review_bucket(change: dict[str, Any]) -> str:
    current = change.get("current")
    previous = change.get("previous")
    change_types = list(change.get("change_types") or [])

    if "disappeared_candidate" in change_types or current is None:
        return "disappeared_candidate"

    source = current if isinstance(current, dict) else previous
    if isinstance(source, dict):
        action = str(source.get("action_state") or "")
        if action in WORKFLOW_REVIEW_ORDER:
            return action
    return "evidence_insufficient"


def _normalized_change(change: dict[str, Any]) -> dict[str, Any]:
    change_types = [
        str(value)
        for value in (change.get("change_types") or [])
        if value
    ]
    return {
        "display_key": str(change.get("display_key") or ""),
        "instrument_id": str(change.get("instrument_id") or ""),
        "review_bucket": _review_bucket(change),
        "change_types": change_types,
        "previous": change.get("previous"),
        "current": change.get("current"),
    }


def build_daily_review_digest(
    history_payload: dict[str, Any],
) -> dict[str, Any]:
    """Turn the latest immutable product observation into review navigation.

    This is intentionally a transparent triage view over Phase-11 product
    history. It does not estimate return, probability, quality, alpha, or
    preferred trades.
    """
    _validate_history_payload(history_payload)
    observations = list(history_payload.get("observations") or [])
    if not observations:
        return {
            "schema_version": 1,
            "contract": DailyReviewDigestContract().as_payload(),
            "status": "no_history",
            "review_ready": False,
            "trade_date": None,
            "source_observation_id": None,
            "source_revision_ordinal": None,
            "previous_recorded_trade_date": None,
            "delta_status": None,
            "change_count": 0,
            "change_type_counts": {},
            "workflow_bucket_counts": {},
            "workflow_sections": [],
            "analysis_incomplete_instruments": [],
            "authoritative_evidence": False,
            "writes_m4_evidence": False,
            "historical_outcome_used_for_ranking": False,
            "predictive_score_used": False,
            "alpha_inference_allowed": False,
            "is_trade_instruction": False,
        }

    observation = dict(observations[0])
    changes = [
        _normalized_change(dict(value))
        for value in (observation.get("changes") or [])
    ]
    declared_total = int(
        observation.get("delta_total_change_count") or 0
    )
    declared_visible = int(observation.get("change_count") or 0)
    if declared_total != len(changes) or declared_visible != len(changes):
        raise ValueError(
            "operator history latest observation is not an exhaustive "
            "unfiltered delta"
        )
    incomplete = sorted({
        str(value)
        for value in (
            observation.get("comparison_incomplete_instruments") or []
        )
        if value
    })

    type_counts = Counter(
        change_type
        for change in changes
        for change_type in change["change_types"]
    )
    bucket_counts = Counter(
        change["review_bucket"]
        for change in changes
    )

    bucket_rank = {
        value: index
        for index, value in enumerate(WORKFLOW_REVIEW_ORDER)
    }
    changes.sort(
        key=lambda item: (
            bucket_rank.get(item["review_bucket"], 999),
            _change_type_sort_key(item["change_types"]),
            item["instrument_id"],
            item["display_key"],
        )
    )

    sections: list[dict[str, Any]] = []
    for bucket in WORKFLOW_REVIEW_ORDER:
        items = [
            item
            for item in changes
            if item["review_bucket"] == bucket
        ]
        if items:
            sections.append({
                "workflow_bucket": bucket,
                "change_count": len(items),
                "items": items,
            })

    delta_status = str(observation.get("delta_status") or "")
    if delta_status == "baseline_no_previous_observation":
        status = "baseline"
    elif changes and incomplete:
        status = "changes_ready_with_analysis_gaps"
    elif changes:
        status = "changes_ready"
    elif incomplete:
        status = "no_changes_with_analysis_gaps"
    else:
        status = "no_changes"

    return {
        "schema_version": 1,
        "contract": DailyReviewDigestContract().as_payload(),
        "status": status,
        "review_ready": True,
        "trade_date": observation.get("trade_date"),
        "source_observation_id": observation.get("observation_id"),
        "source_revision_ordinal": observation.get("revision_ordinal"),
        "source_generated_at_utc": observation.get(
            "source_generated_at_utc"
        ),
        "previous_recorded_trade_date": observation.get(
            "previous_recorded_trade_date"
        ),
        "delta_status": delta_status,
        "change_count": len(changes),
        "change_type_counts": {
            key: int(type_counts.get(key, 0))
            for key in CHANGE_TYPE_ORDER
            if type_counts.get(key, 0)
        },
        "workflow_bucket_counts": {
            key: int(bucket_counts.get(key, 0))
            for key in WORKFLOW_REVIEW_ORDER
            if bucket_counts.get(key, 0)
        },
        "workflow_sections": sections,
        "analysis_incomplete_instruments": incomplete,
        "analysis_incomplete_count": len(incomplete),
        "review_order": list(WORKFLOW_REVIEW_ORDER),
        "change_type_order": list(CHANGE_TYPE_ORDER),
        "ordering_is_product_workflow_not_expected_return": True,
        "all_changes_are_retained": True,
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "historical_outcome_used_for_ranking": False,
        "predictive_score_used": False,
        "alpha_inference_allowed": False,
        "is_trade_instruction": False,
    }


def build_latest_daily_review_digest(
    *,
    history_root: str,
) -> dict[str, Any]:
    payload = query_operator_history(
        history_root=history_root,
        latest_revision_per_day=True,
        summary_only=False,
        limit=1,
    )
    return build_daily_review_digest(payload)


def filter_daily_review_digest(
    payload: dict[str, Any],
    *,
    workflow_bucket: str | None = None,
    change_type: str | None = None,
    instrument_id: str | None = None,
) -> dict[str, Any]:
    """Presentation-only filtering; never changes source digest totals."""
    if (
        workflow_bucket is not None
        and workflow_bucket not in WORKFLOW_REVIEW_ORDER
    ):
        raise ValueError(
            f"unknown review workflow bucket: {workflow_bucket}"
        )
    if (
        change_type is not None
        and change_type not in CHANGE_TYPE_ORDER
    ):
        raise ValueError(f"unknown review change type: {change_type}")

    sections: list[dict[str, Any]] = []
    filtered_count = 0

    normalized_instrument = (
        instrument_id.strip().upper()
        if instrument_id
        else None
    )
    for raw_section in payload.get("workflow_sections") or []:
        section = dict(raw_section)
        bucket = str(section.get("workflow_bucket") or "")
        if workflow_bucket and bucket != workflow_bucket:
            continue

        items = []
        for raw_item in section.get("items") or []:
            item = dict(raw_item)
            if (
                change_type
                and change_type not in (item.get("change_types") or [])
            ):
                continue
            if (
                normalized_instrument
                and str(item.get("instrument_id") or "").upper()
                != normalized_instrument
            ):
                continue
            items.append(item)

        if items:
            sections.append({
                "workflow_bucket": bucket,
                "change_count": len(items),
                "items": items,
            })
            filtered_count += len(items)

    result = dict(payload)
    result["presentation_filter"] = {
        "workflow_bucket": workflow_bucket,
        "change_type": change_type,
        "instrument_id": normalized_instrument,
    }
    result["filtered_change_count"] = filtered_count
    result["filtered_workflow_sections"] = sections
    result["source_change_count_unchanged"] = payload.get("change_count")
    return result
