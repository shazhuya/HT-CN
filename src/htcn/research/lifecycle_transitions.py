from __future__ import annotations

from dataclasses import asdict, dataclass
from collections import Counter
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class LifecycleTransition:
    candidate_key: str
    instrument_id: str
    from_trade_date: str | None
    to_trade_date: str
    enrollment_state: str
    first_observed_trade_date: str
    transition_kind: str
    from_lifecycle_state: str | None
    to_lifecycle_state: str | None
    from_action_state: str | None
    to_action_state: str | None
    from_next_key_price: float | None
    to_next_key_price: float | None
    scanner_presence: str
    evidence_only: bool = True
    is_trade_instruction: bool = False
    alpha_inference_allowed: bool = False

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


def _group_by_date(rows: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        as_of = str(row.get("as_of_trade_date") or "")
        if not as_of:
            raise ValueError("journal row missing as_of_trade_date")
        key = str(row.get("candidate_key") or "")
        if not key:
            raise ValueError(f"journal row on {as_of} missing candidate_key")
        grouped.setdefault(as_of, []).append(row)
    for as_of, items in grouped.items():
        keys = [str(item["candidate_key"]) for item in items]
        if len(keys) != len(set(keys)):
            raise ValueError(f"duplicate candidate_key within snapshot {as_of}")
    return grouped


def _normalize_enrollment(
    rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    materialized = [dict(row) for row in rows]
    if not materialized:
        return []

    grouped = _group_by_date(materialized)
    dates = sorted(grouped)
    baseline_date = dates[0]
    first_seen: dict[str, str] = {}
    cohort: dict[str, str] = {}

    normalized: list[dict[str, Any]] = []
    for as_of in dates:
        for row in grouped[as_of]:
            key = str(row["candidate_key"])
            if key not in first_seen:
                first_seen[key] = as_of
                explicit = row.get("enrollment_state")
                if explicit in {"baseline_existing", "prospective_new"}:
                    cohort[key] = str(explicit)
                else:
                    cohort[key] = (
                        "baseline_existing"
                        if as_of == baseline_date
                        else "prospective_new"
                    )
            elif cohort[key] == "baseline_existing":
                # A baseline candidate can never be upgraded into prospective-new later.
                pass
            else:
                explicit = row.get("enrollment_state")
                if explicit == "baseline_existing":
                    raise ValueError(
                        f"candidate {key} attempts prospective_new -> baseline_existing reclassification"
                    )

            row["enrollment_state"] = cohort[key]
            row["first_observed_trade_date"] = str(
                row.get("first_observed_trade_date") or first_seen[key]
            )
            if row["first_observed_trade_date"] != first_seen[key]:
                raise ValueError(
                    f"candidate {key} first_observed_trade_date drift: "
                    f"{row['first_observed_trade_date']} != {first_seen[key]}"
                )
            normalized.append(row)
    return normalized


def _transition_kind(
    previous: dict[str, Any],
    current: dict[str, Any],
) -> str:
    before_lifecycle = str(previous.get("source_lifecycle_state"))
    after_lifecycle = str(current.get("source_lifecycle_state"))
    before_action = str(previous.get("action_state"))
    after_action = str(current.get("action_state"))

    if before_lifecycle != after_lifecycle:
        return "lifecycle_changed"
    if before_action != after_action:
        return "action_changed_only"
    return "persisted_same_state"


def build_transitions(
    rows: Iterable[dict[str, Any]],
) -> list[LifecycleTransition]:
    normalized = _normalize_enrollment(rows)
    if not normalized:
        return []

    grouped = _group_by_date(normalized)
    dates = sorted(grouped)
    transitions: list[LifecycleTransition] = []

    previous_by_key: dict[str, dict[str, Any]] = {}
    last_seen_by_key: dict[str, tuple[str, dict[str, Any]]] = {}
    previous_date: str | None = None

    for as_of in dates:
        current_by_key = {
            str(row["candidate_key"]): row
            for row in grouped[as_of]
        }

        if previous_date is None:
            for key, current in current_by_key.items():
                transitions.append(
                    LifecycleTransition(
                        candidate_key=key,
                        instrument_id=str(current.get("instrument_id")),
                        from_trade_date=None,
                        to_trade_date=as_of,
                        enrollment_state=str(current["enrollment_state"]),
                        first_observed_trade_date=str(current["first_observed_trade_date"]),
                        transition_kind="baseline_observed",
                        from_lifecycle_state=None,
                        to_lifecycle_state=str(current.get("source_lifecycle_state")),
                        from_action_state=None,
                        to_action_state=str(current.get("action_state")),
                        from_next_key_price=None,
                        to_next_key_price=(
                            None if current.get("next_key_price") is None
                            else float(current["next_key_price"])
                        ),
                        scanner_presence="present",
                    )
                )
        else:
            for key, current in current_by_key.items():
                previous = previous_by_key.get(key)
                if previous is None:
                    prior_seen = last_seen_by_key.get(key)
                    if prior_seen is None:
                        from_trade_date = None
                        from_lifecycle_state = None
                        from_action_state = None
                        from_next_key_price = None
                        transition_kind = "new_candidate"
                    else:
                        prior_date, prior_row = prior_seen
                        from_trade_date = prior_date
                        from_lifecycle_state = str(prior_row.get("source_lifecycle_state"))
                        from_action_state = str(prior_row.get("action_state"))
                        from_next_key_price = (
                            None if prior_row.get("next_key_price") is None
                            else float(prior_row["next_key_price"])
                        )
                        transition_kind = "scanner_reappeared"

                    transitions.append(
                        LifecycleTransition(
                            candidate_key=key,
                            instrument_id=str(current.get("instrument_id")),
                            from_trade_date=from_trade_date,
                            to_trade_date=as_of,
                            enrollment_state=str(current["enrollment_state"]),
                            first_observed_trade_date=str(current["first_observed_trade_date"]),
                            transition_kind=transition_kind,
                            from_lifecycle_state=from_lifecycle_state,
                            to_lifecycle_state=str(current.get("source_lifecycle_state")),
                            from_action_state=from_action_state,
                            to_action_state=str(current.get("action_state")),
                            from_next_key_price=from_next_key_price,
                            to_next_key_price=(
                                None if current.get("next_key_price") is None
                                else float(current["next_key_price"])
                            ),
                            scanner_presence="present",
                        )
                    )
                    continue

                transitions.append(
                    LifecycleTransition(
                        candidate_key=key,
                        instrument_id=str(current.get("instrument_id")),
                        from_trade_date=previous_date,
                        to_trade_date=as_of,
                        enrollment_state=str(current["enrollment_state"]),
                        first_observed_trade_date=str(current["first_observed_trade_date"]),
                        transition_kind=_transition_kind(previous, current),
                        from_lifecycle_state=str(previous.get("source_lifecycle_state")),
                        to_lifecycle_state=str(current.get("source_lifecycle_state")),
                        from_action_state=str(previous.get("action_state")),
                        to_action_state=str(current.get("action_state")),
                        from_next_key_price=(
                            None if previous.get("next_key_price") is None
                            else float(previous["next_key_price"])
                        ),
                        to_next_key_price=(
                            None if current.get("next_key_price") is None
                            else float(current["next_key_price"])
                        ),
                        scanner_presence="present",
                    )
                )

            disappeared = sorted(set(previous_by_key) - set(current_by_key))
            for key in disappeared:
                previous = previous_by_key[key]
                transitions.append(
                    LifecycleTransition(
                        candidate_key=key,
                        instrument_id=str(previous.get("instrument_id")),
                        from_trade_date=previous_date,
                        to_trade_date=as_of,
                        enrollment_state=str(previous["enrollment_state"]),
                        first_observed_trade_date=str(previous["first_observed_trade_date"]),
                        transition_kind="scanner_disappeared",
                        from_lifecycle_state=str(previous.get("source_lifecycle_state")),
                        to_lifecycle_state=None,
                        from_action_state=str(previous.get("action_state")),
                        to_action_state=None,
                        from_next_key_price=(
                            None if previous.get("next_key_price") is None
                            else float(previous["next_key_price"])
                        ),
                        to_next_key_price=None,
                        scanner_presence="absent",
                    )
                )

        for key, row in current_by_key.items():
            last_seen_by_key[key] = (as_of, row)
        previous_by_key = current_by_key
        previous_date = as_of

    return transitions


def build_transition_report(
    rows: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    normalized = _normalize_enrollment(rows)
    grouped = _group_by_date(normalized) if normalized else {}
    dates = sorted(grouped)
    transitions = build_transitions(normalized)

    cohort_counts = Counter(
        str(row.get("enrollment_state"))
        for row in normalized
        if row.get("enrollment_state")
    )
    transition_counts = Counter(item.transition_kind for item in transitions)
    lifecycle_pair_counts = Counter(
        f"{item.from_lifecycle_state}->{item.to_lifecycle_state}"
        for item in transitions
        if item.transition_kind == "lifecycle_changed"
    )

    latest_date = dates[-1] if dates else None
    latest_rows = grouped.get(latest_date, []) if latest_date else []
    latest_state_counts = Counter(
        str(row.get("source_lifecycle_state")) for row in latest_rows
    )

    return {
        "schema_version": 1,
        "status": (
            "empty"
            if not dates
            else "baseline_only"
            if len(dates) == 1
            else "transitions_available"
        ),
        "date_count": len(dates),
        "dates": dates,
        "baseline_trade_date": dates[0] if dates else None,
        "latest_trade_date": latest_date,
        "journal_row_count": len(normalized),
        "latest_candidate_count": len(latest_rows),
        "cohort_counts": dict(sorted(cohort_counts.items())),
        "transition_counts": dict(sorted(transition_counts.items())),
        "lifecycle_pair_counts": dict(sorted(lifecycle_pair_counts.items())),
        "latest_lifecycle_state_counts": dict(sorted(latest_state_counts.items())),
        "transition_count": len(transitions),
        "transitions": [item.as_payload() for item in transitions],
        "interpretation": {
            "scanner_disappeared_is_invalidated": False,
            "linear_lifecycle_ranking_used": False,
            "alpha_inference_allowed": False,
            "is_trade_instruction": False,
        },
    }
