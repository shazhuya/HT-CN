from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import isclose
from typing import Any


@dataclass(frozen=True, slots=True)
class OperatorDeltaContract:
    version: int = 1
    semantics: str = "product_observation_only"
    authoritative_transition: bool = False
    writes_m4_evidence: bool = False
    predictive_score_used: bool = False
    historical_outcome_used: bool = False
    alpha_inference_allowed: bool = False
    is_trade_instruction: bool = False
    mutates_harmonic_identity: bool = False
    mutates_source_raw_prz: bool = False
    owns_lifecycle: bool = False

    def as_payload(self) -> dict[str, object]:
        return {
            "version": self.version,
            "semantics": self.semantics,
            "authoritative_transition": self.authoritative_transition,
            "writes_m4_evidence": self.writes_m4_evidence,
            "predictive_score_used": self.predictive_score_used,
            "historical_outcome_used": self.historical_outcome_used,
            "alpha_inference_allowed": self.alpha_inference_allowed,
            "is_trade_instruction": self.is_trade_instruction,
            "mutates_harmonic_identity": self.mutates_harmonic_identity,
            "mutates_source_raw_prz": self.mutates_source_raw_prz,
            "owns_lifecycle": self.owns_lifecycle,
        }


def _validate_queue_snapshot(
    payload: dict[str, Any],
    *,
    label: str,
) -> tuple[str, dict[str, dict[str, Any]], set[str]]:
    if str(payload.get("observation_integrity") or "") != "single_as_of":
        raise ValueError(
            f"{label} operator queue must have observation_integrity=single_as_of"
        )
    as_of = str(payload.get("as_of_trade_date") or "")
    if not as_of:
        raise ValueError(f"{label} operator queue missing as_of_trade_date")

    contract = payload.get("contract") or {}
    forbidden_truthy = (
        "predictive_score_used",
        "historical_outcome_used",
        "alpha_inference_allowed",
        "is_trade_instruction",
        "mutates_harmonic_identity",
        "mutates_source_raw_prz",
        "owns_lifecycle",
    )
    for field in forbidden_truthy:
        if contract.get(field) is not False:
            raise ValueError(
                f"{label} operator queue contract boundary violation: {field}"
            )

    items_by_key: dict[str, dict[str, Any]] = {}
    for raw in payload.get("items") or []:
        item = dict(raw)
        key = str(item.get("display_key") or "")
        if not key:
            raise ValueError(f"{label} operator queue item missing display_key")
        if key in items_by_key:
            raise ValueError(
                f"{label} operator queue contains duplicate display_key: {key}"
            )
        items_by_key[key] = item

    failed_instruments = {
        str(item.get("instrument_id") or "")
        for item in (payload.get("errors") or [])
        if item.get("instrument_id")
    }
    return as_of, items_by_key, failed_instruments


def _same_price(left: object, right: object) -> bool:
    if left is None or right is None:
        return left is right
    try:
        return isclose(
            float(left),
            float(right),
            rel_tol=1e-9,
            abs_tol=1e-9,
        )
    except (TypeError, ValueError):
        return False


def _snapshot_fields(item: dict[str, Any] | None) -> dict[str, Any] | None:
    if item is None:
        return None
    return {
        "display_key": item.get("display_key"),
        "instrument_id": item.get("instrument_id"),
        "pattern_id": item.get("pattern_id"),
        "schema": item.get("schema"),
        "direction": item.get("direction"),
        "scale": item.get("scale"),
        "pattern_state": item.get("pattern_state"),
        "action_state": item.get("action_state"),
        "lifecycle_state": item.get("lifecycle_state"),
        "next_key_price": item.get("next_key_price"),
        "next_key_price_role": item.get("next_key_price_role"),
        "execution_context_gate": item.get("execution_context_gate"),
        "context_cautions": list(item.get("context_cautions") or []),
        "current_position": item.get("current_position"),
        "first_watch": item.get("first_watch"),
        "upgrade_blocker": item.get("upgrade_blocker"),
    }


def _change_types(
    previous: dict[str, Any],
    current: dict[str, Any],
) -> list[str]:
    changes: list[str] = []
    if previous.get("action_state") != current.get("action_state"):
        changes.append("action_state_changed")
    if previous.get("lifecycle_state") != current.get("lifecycle_state"):
        changes.append("lifecycle_state_changed")
    if previous.get("pattern_state") != current.get("pattern_state"):
        changes.append("pattern_state_changed")
    if (
        not _same_price(
            previous.get("next_key_price"),
            current.get("next_key_price"),
        )
        or previous.get("next_key_price_role")
        != current.get("next_key_price_role")
    ):
        changes.append("next_key_changed")
    if (
        previous.get("execution_context_gate")
        != current.get("execution_context_gate")
    ):
        changes.append("execution_gate_changed")
    if sorted(previous.get("context_cautions") or []) != sorted(
        current.get("context_cautions") or []
    ):
        changes.append("context_cautions_changed")
    return changes


def build_operator_delta(
    previous: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, Any]:
    previous_as_of, previous_items, _ = _validate_queue_snapshot(
        previous,
        label="previous",
    )
    current_as_of, current_items, current_failed = _validate_queue_snapshot(
        current,
        label="current",
    )

    result: dict[str, Any] = {
        "schema_version": 1,
        "contract": OperatorDeltaContract().as_payload(),
        "previous_as_of_trade_date": previous_as_of,
        "current_as_of_trade_date": current_as_of,
        "status": "ready",
        "change_count": 0,
        "change_type_counts": {},
        "changes": [],
        "comparison_incomplete_instruments": sorted(current_failed),
        "warnings": [],
    }

    if current_as_of < previous_as_of:
        raise ValueError(
            "operator delta forbids reverse chronology: "
            f"{current_as_of} < {previous_as_of}"
        )
    if current_as_of == previous_as_of:
        result["status"] = "same_as_of_no_delta"
        return result

    changes: list[dict[str, Any]] = []
    previous_keys = set(previous_items)
    current_keys = set(current_items)

    for key in sorted(current_keys - previous_keys):
        item = current_items[key]
        changes.append({
            "display_key": key,
            "instrument_id": item.get("instrument_id"),
            "change_types": ["new_candidate"],
            "previous": None,
            "current": _snapshot_fields(item),
        })

    for key in sorted(previous_keys - current_keys):
        item = previous_items[key]
        instrument_id = str(item.get("instrument_id") or "")
        if instrument_id in current_failed:
            continue
        changes.append({
            "display_key": key,
            "instrument_id": instrument_id,
            "change_types": ["disappeared_candidate"],
            "previous": _snapshot_fields(item),
            "current": None,
        })

    for key in sorted(previous_keys & current_keys):
        before = previous_items[key]
        after = current_items[key]
        change_types = _change_types(before, after)
        if not change_types:
            continue
        changes.append({
            "display_key": key,
            "instrument_id": after.get("instrument_id"),
            "change_types": change_types,
            "previous": _snapshot_fields(before),
            "current": _snapshot_fields(after),
        })

    if current_failed:
        result["warnings"].append(
            "Current queue contains instrument analysis errors; "
            "disappearance events for those instruments are suppressed."
        )

    type_counts = Counter(
        change_type
        for item in changes
        for change_type in item["change_types"]
    )
    changes.sort(
        key=lambda item: (
            str(item.get("instrument_id") or ""),
            str(item.get("display_key") or ""),
        )
    )
    result["changes"] = changes
    result["change_count"] = len(changes)
    result["change_type_counts"] = dict(sorted(type_counts.items()))
    return result
