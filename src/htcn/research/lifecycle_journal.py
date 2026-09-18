from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
from typing import Any, Iterable


OUTCOME_PRE_TERMINAL_STATES = {
    "approaching_source_prz",
    "entered_source_prz",
    "waiting_terminal",
}
OUTCOME_BLOCKED_PATTERN_IDS = {"alternate_bat", "five_zero"}


ANCHOR_LABELS: dict[str, tuple[str, ...]] = {
    "XABCD": ("X", "A", "B", "C"),
    "ABCD": ("A", "B", "C"),
    "0XABC": ("0", "X", "A", "B"),
}


@dataclass(frozen=True, slots=True)
class LifecycleJournalEntry:
    code_head: str
    instrument_id: str
    as_of_trade_date: str
    candidate_key: str
    pattern_id: str
    schema: str
    direction: str
    scale: int
    pattern_state: str
    source_lifecycle_state: str
    action_state: str
    next_key_price: float | None
    next_key_price_role: str | None
    execution_context_gate: str
    context_integrity_summary: str | None
    source_prz_low: float | None
    source_prz_high: float | None
    source_terminal_trade_date: str | None
    eligible_for_validation: bool
    enrollment_state: str = "pending_append_classification"
    first_observed_trade_date: str | None = None
    prospective_outcome_eligible: bool = False
    outcome_enrollment_trade_date: str | None = None
    outcome_eligibility_reason: str = "not_evaluated"
    evidence_only: bool = True
    is_trade_instruction: bool = False
    alpha_inference_allowed: bool = False

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


def _point_dates(pattern: dict[str, Any]) -> dict[str, str]:
    return {
        str(point.get("label")): str(point.get("trade_date"))
        for point in pattern.get("points") or []
        if point.get("label") is not None and point.get("trade_date") is not None
    }


def candidate_key(instrument_id: str, pattern: dict[str, Any]) -> str:
    schema = str(pattern.get("schema") or "")
    labels = ANCHOR_LABELS.get(schema)
    if labels is None:
        raise ValueError(f"unsupported journal schema: {schema!r}")

    dates = _point_dates(pattern)
    missing = [label for label in labels if label not in dates]
    if missing:
        raise ValueError(f"journal candidate missing anchor dates: {missing}")

    anchor = "|".join(f"{label}:{dates[label]}" for label in labels)
    return (
        f"{instrument_id}|{schema}|{pattern.get('pattern_id')}|"
        f"{pattern.get('direction')}|S{int(pattern.get('scale'))}|{anchor}"
    )


def _bar_trade_date(analysis: dict[str, Any], bar_index: object) -> str | None:
    if bar_index is None:
        return None
    try:
        target = int(bar_index)
    except (TypeError, ValueError):
        return None
    for bar in analysis.get("bars") or []:
        if int(bar.get("index", -1)) == target:
            value = bar.get("trade_date")
            return None if value is None else str(value)
    return None


def entries_from_analysis(
    analysis: dict[str, Any],
    *,
    code_head: str,
) -> list[LifecycleJournalEntry]:
    instrument_id = str(analysis["instrument_id"])
    as_of = str(analysis["last_trade_date"])
    integrity = analysis.get("context_integrity") or {}
    integrity_summary = integrity.get("summary_state")
    out: list[LifecycleJournalEntry] = []

    for pattern in [*(analysis.get("completed") or []), *(analysis.get("forming") or [])]:
        schema = str(pattern.get("schema") or "")
        if schema == "FIVE_ZERO":
            # 5-0 remains production-quarantined and is not admitted into M4 validation.
            continue

        lifecycle = pattern.get("source_lifecycle")
        narrative = pattern.get("decision_narrative")
        if not isinstance(lifecycle, dict):
            raise ValueError(
                f"{instrument_id} {pattern.get('pattern_id')} missing canonical source_lifecycle"
            )
        if not isinstance(narrative, dict):
            raise ValueError(
                f"{instrument_id} {pattern.get('pattern_id')} missing decision_narrative"
            )

        source = (pattern.get("prz") or {}).get("source_prz") or {}
        source_available = source.get("available") is True
        out.append(
            LifecycleJournalEntry(
                code_head=code_head,
                instrument_id=instrument_id,
                as_of_trade_date=as_of,
                candidate_key=candidate_key(instrument_id, pattern),
                pattern_id=str(pattern.get("pattern_id")),
                schema=schema,
                direction=str(pattern.get("direction")),
                scale=int(pattern.get("scale")),
                pattern_state=str(pattern.get("state")),
                source_lifecycle_state=str(lifecycle.get("state")),
                action_state=str(narrative.get("action_state")),
                next_key_price=(
                    None
                    if lifecycle.get("next_key_price") is None
                    else float(lifecycle["next_key_price"])
                ),
                next_key_price_role=(
                    None
                    if lifecycle.get("next_key_price_role") is None
                    else str(lifecycle["next_key_price_role"])
                ),
                execution_context_gate=str(
                    narrative.get("execution_context_gate") or "execution_context_unavailable"
                ),
                context_integrity_summary=(
                    None if integrity_summary is None else str(integrity_summary)
                ),
                source_prz_low=(
                    float(source["price_low"])
                    if source_available and source.get("price_low") is not None
                    else None
                ),
                source_prz_high=(
                    float(source["price_high"])
                    if source_available and source.get("price_high") is not None
                    else None
                ),
                source_terminal_trade_date=_bar_trade_date(
                    analysis, lifecycle.get("source_terminal_bar")
                ),
                eligible_for_validation=True,
            )
        )
    return out


def prospective_outcome_gate(
    payload: dict[str, Any],
    *,
    enrollment_state: str,
) -> tuple[bool, str]:
    """Strict gate for the future prospective outcome cohort."""
    if enrollment_state != "prospective_new":
        return False, "baseline_existing"
    pattern_id = str(payload.get("pattern_id") or "")
    if pattern_id in OUTCOME_BLOCKED_PATTERN_IDS:
        return False, "pattern_source_fidelity_blocked"
    if str(payload.get("pattern_state") or "") != "forming":
        return False, "first_observed_not_forming"
    state = str(payload.get("source_lifecycle_state") or "")
    if state not in OUTCOME_PRE_TERMINAL_STATES:
        return False, "first_observed_not_pre_terminal"
    if payload.get("source_terminal_trade_date") is not None:
        return False, "source_terminal_already_observed"
    low = payload.get("source_prz_low")
    high = payload.get("source_prz_high")
    if low is None or high is None:
        return False, "source_prz_unresolved"
    if float(low) > float(high):
        return False, "source_prz_invalid"
    return True, "prospective_new_pre_terminal_source_resolved"


def read_journal(path: str | Path) -> list[dict[str, Any]]:
    target = Path(path)
    if not target.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, raw in enumerate(
        target.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid journal JSONL at line {line_number}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"invalid journal row at line {line_number}")
        rows.append(value)
    return rows


def append_entries(
    path: str | Path,
    entries: Iterable[LifecycleJournalEntry],
) -> dict[str, int | str | None]:
    incoming = list(entries)
    if not incoming:
        return {"incoming": 0, "appended": 0, "existing": 0, "as_of_trade_date": None}

    dates = {entry.as_of_trade_date for entry in incoming}
    if len(dates) != 1:
        raise ValueError(f"one capture must contain one as-of trade date, got {sorted(dates)}")
    as_of = next(iter(dates))

    target = Path(path)
    existing = read_journal(target)
    existing_dates = [str(row.get("as_of_trade_date")) for row in existing if row.get("as_of_trade_date")]
    if existing_dates and as_of < max(existing_dates):
        raise ValueError(
            f"prospective journal forbids backfill: incoming {as_of} < existing max {max(existing_dates)}"
        )

    identities = {
        (
            str(row.get("code_head")),
            str(row.get("as_of_trade_date")),
            str(row.get("candidate_key")),
        )
        for row in existing
    }
    prior_by_candidate: dict[str, list[dict[str, Any]]] = {}
    for row in existing:
        key = str(row.get("candidate_key") or "")
        if key:
            prior_by_candidate.setdefault(key, []).append(row)

    baseline_capture = len(existing) == 0
    payloads = []
    baseline_appended = 0
    prospective_new_appended = 0

    for entry in incoming:
        identity = (entry.code_head, entry.as_of_trade_date, entry.candidate_key)
        if identity in identities:
            continue
        identities.add(identity)

        prior = prior_by_candidate.get(entry.candidate_key, [])
        if prior:
            prior_dates = sorted(
                str(row.get("first_observed_trade_date") or row.get("as_of_trade_date"))
                for row in prior
                if row.get("first_observed_trade_date") or row.get("as_of_trade_date")
            )
            first_observed = prior_dates[0] if prior_dates else entry.as_of_trade_date
            prior_states = {
                str(row.get("enrollment_state"))
                for row in prior
                if row.get("enrollment_state")
            }
            enrollment_state = (
                "prospective_new"
                if prior_states == {"prospective_new"}
                else "baseline_existing"
            )
        elif baseline_capture:
            first_observed = entry.as_of_trade_date
            enrollment_state = "baseline_existing"
        else:
            first_observed = entry.as_of_trade_date
            enrollment_state = "prospective_new"

        payload = entry.as_payload()
        payload["first_observed_trade_date"] = first_observed
        payload["enrollment_state"] = enrollment_state

        prior_outcome_dates = sorted(
            str(row.get("outcome_enrollment_trade_date"))
            for row in prior
            if row.get("outcome_enrollment_trade_date")
        )
        if enrollment_state == "baseline_existing":
            outcome_eligible = False
            outcome_reason = "baseline_existing"
            outcome_enrollment_date = None
        elif prior_outcome_dates:
            outcome_eligible = True
            outcome_reason = "prospective_outcome_cohort_already_enrolled"
            outcome_enrollment_date = prior_outcome_dates[0]
        else:
            outcome_eligible, outcome_reason = prospective_outcome_gate(
                payload,
                enrollment_state=enrollment_state,
            )
            outcome_enrollment_date = (
                entry.as_of_trade_date if outcome_eligible else None
            )

        payload["prospective_outcome_eligible"] = outcome_eligible
        payload["outcome_eligibility_reason"] = outcome_reason
        payload["outcome_enrollment_trade_date"] = outcome_enrollment_date
        payloads.append(payload)
        prior_by_candidate.setdefault(entry.candidate_key, []).append(payload)

        if enrollment_state == "baseline_existing":
            baseline_appended += 1
        else:
            prospective_new_appended += 1

    if payloads:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8", newline="\n") as handle:
            for payload in payloads:
                handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
                handle.write("\n")

    return {
        "incoming": len(incoming),
        "appended": len(payloads),
        "existing": len(existing),
        "as_of_trade_date": as_of,
        "baseline_existing_appended": baseline_appended,
        "prospective_new_appended": prospective_new_appended,
    }
