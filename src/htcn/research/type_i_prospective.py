from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import json
from typing import Any, Iterable


PROSPECTIVE_PROTOCOL_ID = "m2-type-i-prospective-v1"
PROSPECTIVE_CUTOFF = "2026-09-15"


@dataclass(frozen=True, slots=True)
class ProspectiveUpdateSummary:
    protocol_id: str
    total_events: int
    prospective_registered_before_endpoint: int
    backfilled_excluded: int
    awaiting_t5: int
    excluded_t2_by_t5: int
    exposure_group: int
    comparator_group: int
    matured_t20: int

    def as_payload(self) -> dict[str, Any]:
        return {
            "protocol_id": self.protocol_id,
            "total_events": self.total_events,
            "prospective_registered_before_endpoint": self.prospective_registered_before_endpoint,
            "backfilled_excluded": self.backfilled_excluded,
            "awaiting_t5": self.awaiting_t5,
            "excluded_t2_by_t5": self.excluded_t2_by_t5,
            "exposure_group": self.exposure_group,
            "comparator_group": self.comparator_group,
            "matured_t20": self.matured_t20,
        }


def stable_prospective_event_id(event: dict[str, Any]) -> str:
    """Create an index-independent event id suitable for an append-only registry.

    Bar indices shift when a rolling local window advances. Dates + frozen structural labels do
    not, so the registry deliberately does not reuse the UI event id that embeds bar indices.
    """

    required = (
        "instrument_id",
        "pattern_id",
        "schema",
        "direction",
        "source_scale",
        "forming_signal_trade_date",
        "terminal_trade_date",
    )
    missing = [name for name in required if event.get(name) in {None, ""}]
    if missing:
        raise ValueError(f"prospective event missing stable id fields: {missing}")
    return "|".join(
        (
            str(event["instrument_id"]),
            str(event["pattern_id"]),
            str(event["schema"]),
            str(event["direction"]),
            f"S{int(event['source_scale'])}",
            str(event["forming_signal_trade_date"]),
            str(event["terminal_trade_date"]),
        )
    )


def _core_payload(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "instrument_id": str(event["instrument_id"]),
        "pattern_id": str(event["pattern_id"]),
        "schema": str(event["schema"]),
        "direction": str(event["direction"]),
        "source_scale": int(event["source_scale"]),
        "forming_signal_trade_date": str(event["forming_signal_trade_date"]),
        "terminal_trade_date": str(event["terminal_trade_date"]),
    }


def _observation_payload(
    event: dict[str, Any],
    *,
    observed_through_trade_date: str,
) -> dict[str, Any]:
    state = event.get("t5_evidence") or {}
    return {
        "observed_through_trade_date": str(observed_through_trade_date),
        "available_future_bars_after_terminal": int(
            event.get("available_future_bars_after_terminal") or 0
        ),
        "state": str(state.get("state")),
        "historical_group": state.get("historical_group"),
        "eligible_for_frozen_contrast": bool(state.get("eligible_for_frozen_contrast")),
        "endpoint_state": str(state.get("endpoint_state")),
        "bars_from_terminal_to_full_prz_exit": event.get(
            "bars_from_terminal_to_full_prz_exit"
        ),
        "bars_from_terminal_to_t1": event.get("bars_from_terminal_to_t1"),
        "bars_from_terminal_to_t2": event.get("bars_from_terminal_to_t2"),
        "terminal_price": float(event["terminal_price"]),
        "prz": {
            "price_low": float(event["prz"]["price_low"]),
            "price_high": float(event["prz"]["price_high"]),
        },
        "t1_price": float(event["t1_price"]),
        "t2_price": float(event["t2_price"]),
    }


def _validate_transition(previous: dict[str, Any], current: dict[str, Any]) -> None:
    old_available = int(previous["available_future_bars_after_terminal"])
    new_available = int(current["available_future_bars_after_terminal"])
    if new_available < old_available:
        raise ValueError("prospective observation cannot move backwards in available bars")

    old_state = str(previous["state"])
    new_state = str(current["state"])
    if old_state == "pending_t5_observation":
        allowed_states = {
            "pending_t5_observation",
            "t2_already_reached_by_t5",
            "full_prz_exit_by_t5",
            "no_full_prz_exit_by_t5",
        }
    else:
        allowed_states = {old_state}
    if new_state not in allowed_states:
        raise ValueError(f"invalid prospective T+5 state transition: {old_state} -> {new_state}")

    old_endpoint = str(previous["endpoint_state"])
    new_endpoint = str(current["endpoint_state"])
    allowed_endpoint = {
        "not_applicable": {"not_applicable"},
        "t2_hit_by_t5": {"t2_hit_by_t5"},
        "pending_t20": {"pending_t20", "t2_hit_t6_t20", "no_t2_by_t20"},
        "t2_hit_t6_t20": {"t2_hit_t6_t20"},
        "no_t2_by_t20": {"no_t2_by_t20"},
    }
    if new_endpoint not in allowed_endpoint.get(old_endpoint, {old_endpoint}):
        raise ValueError(
            f"invalid prospective endpoint transition: {old_endpoint} -> {new_endpoint}"
        )


def empty_registry(
    *,
    protocol_id: str = PROSPECTIVE_PROTOCOL_ID,
    cutoff: str = PROSPECTIVE_CUTOFF,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "protocol_id": protocol_id,
        "registered_cutoff": cutoff,
        "events": {},
        "research_contract": {
            "append_only_events": True,
            "delete_on_rescan_missing": False,
            "prospective_registration_requires_first_observation_by_t5": True,
            "confirmatory_test_in_this_registry": False,
            "dynamic_probability_output": False,
            "identity_rules_mutated": False,
        },
    }


def update_registry(
    registry: dict[str, Any],
    events: Iterable[dict[str, Any]],
    *,
    observed_through_trade_date: str,
    protocol_id: str = PROSPECTIVE_PROTOCOL_ID,
    cutoff: str = PROSPECTIVE_CUTOFF,
) -> dict[str, Any]:
    """Append/update observations without deleting previously registered events.

    An event first seen no later than T+5 is prospectively registered before the T+6..T+20
    endpoint window can be observed. Events discovered only after T+5 remain in the ledger as
    audit/backfill records but are permanently excluded from any future prospective primary
    evaluation. This prevents retrospective cherry-picking when a local scan starts late.
    """

    out = deepcopy(registry)
    if not out:
        out = empty_registry(protocol_id=protocol_id, cutoff=cutoff)
    if out.get("protocol_id") != protocol_id:
        raise ValueError("prospective registry protocol_id mismatch")
    if out.get("registered_cutoff") != cutoff:
        raise ValueError("prospective registry cutoff mismatch")
    rows: dict[str, Any] = out.setdefault("events", {})

    for event in events:
        if str(event.get("terminal_trade_date")) <= cutoff:
            continue
        event_id = stable_prospective_event_id(event)
        core = _core_payload(event)
        observation = _observation_payload(
            event,
            observed_through_trade_date=observed_through_trade_date,
        )
        record = rows.get(event_id)
        if record is None:
            available = int(observation["available_future_bars_after_terminal"])
            rows[event_id] = {
                "event_id": event_id,
                "core": core,
                "registration": {
                    "first_observed_through_trade_date": str(observed_through_trade_date),
                    "first_observed_available_future_bars": available,
                    "registration_mode": (
                        "prospective_before_endpoint_window"
                        if available <= 5
                        else "backfilled_after_t5"
                    ),
                    "prospective_registration_valid": bool(available <= 5),
                },
                "observations": [observation],
            }
            continue

        if record.get("core") != core:
            raise ValueError(f"prospective event core changed for {event_id}")
        observations = record.setdefault("observations", [])
        if observations:
            latest = observations[-1]
            latest_date = str(latest["observed_through_trade_date"])
            current_date = str(observation["observed_through_trade_date"])
            if current_date < latest_date:
                raise ValueError("prospective observations must be appended in date order")
            if current_date == latest_date:
                comparable = {
                    key: value
                    for key, value in observation.items()
                    if key not in {"terminal_price", "prz", "t1_price", "t2_price"}
                }
                old_comparable = {
                    key: value
                    for key, value in latest.items()
                    if key not in {"terminal_price", "prz", "t1_price", "t2_price"}
                }
                if comparable != old_comparable:
                    raise ValueError(
                        f"same-date prospective state changed for {event_id}; audit data revision"
                    )
                continue
            _validate_transition(latest, observation)
        observations.append(observation)

    return out


def registry_summary(registry: dict[str, Any]) -> ProspectiveUpdateSummary:
    events = list((registry.get("events") or {}).values())
    prospective = [
        row
        for row in events
        if (row.get("registration") or {}).get("prospective_registration_valid") is True
    ]
    latest = [row["observations"][-1] for row in prospective if row.get("observations")]
    return ProspectiveUpdateSummary(
        protocol_id=str(registry.get("protocol_id") or PROSPECTIVE_PROTOCOL_ID),
        total_events=len(events),
        prospective_registered_before_endpoint=len(prospective),
        backfilled_excluded=len(events) - len(prospective),
        awaiting_t5=sum(row.get("state") == "pending_t5_observation" for row in latest),
        excluded_t2_by_t5=sum(row.get("state") == "t2_already_reached_by_t5" for row in latest),
        exposure_group=sum(row.get("state") == "full_prz_exit_by_t5" for row in latest),
        comparator_group=sum(row.get("state") == "no_full_prz_exit_by_t5" for row in latest),
        matured_t20=sum(
            row.get("endpoint_state") in {"t2_hit_t6_t20", "no_t2_by_t20"}
            for row in latest
            if row.get("state") in {"full_prz_exit_by_t5", "no_full_prz_exit_by_t5"}
        ),
    )


class ProspectiveRegistryStore:
    """Small atomic JSON store for the local append-only prospective ledger."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            return empty_registry()
        return json.loads(self.path.read_text(encoding="utf-8"))

    def write(self, registry: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(registry, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)
