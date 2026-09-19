from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from .lifecycle_transitions import normalize_journal_rows


@dataclass(frozen=True, slots=True)
class CohortFollowupObservation:
    code_head: str
    instrument_id: str
    as_of_trade_date: str
    candidate_key: str
    outcome_enrollment_trade_date: str
    scanner_presence: str
    underlying_last_trade_date: str | None
    market_observation_status: str
    execution_context_gate: str
    price_mode: str
    price_basis_id: str
    daily_event_source: str | None = None
    daily_event_reason: str | None = None
    capture_transaction_id: str | None = None
    as_of_open: float | None = None
    as_of_high: float | None = None
    as_of_low: float | None = None
    as_of_close: float | None = None
    as_of_volume: float | None = None
    evidence_only: bool = True
    is_trade_instruction: bool = False
    alpha_inference_allowed: bool = False

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


def _latest_bar_value(analysis: dict[str, Any], field: str) -> float | None:
    bars = analysis.get("bars") or []
    if not bars:
        return None
    value = bars[-1].get(field)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def followup_from_analysis(
    analysis: dict[str, Any],
    *,
    code_head: str,
    capture_trade_date: str,
    candidate_key: str,
    outcome_enrollment_trade_date: str,
    market_observation_status: str,
    include_latest_bar_facts: bool,
    daily_event_source: str | None = None,
    daily_event_reason: str | None = None,
) -> CohortFollowupObservation:
    instrument_id = str(analysis["instrument_id"])
    underlying_last_trade_date = str(analysis["last_trade_date"])
    as_of = str(capture_trade_date)
    price_mode = str(analysis.get("price_mode") or "")
    price_basis_id = str(analysis.get("price_basis_id") or "")
    if (
        price_mode not in {"qfq", "qfq_carry_forward"}
        or not price_basis_id.startswith("qfq:")
    ):
        raise ValueError(
            "cohort follow-up requires formal QFQ price basis"
        )

    if market_observation_status == "traded":
        if underlying_last_trade_date != as_of:
            raise ValueError(
                "traded cohort follow-up requires underlying_last_trade_date == capture date"
            )
        if not include_latest_bar_facts:
            raise ValueError(
                "traded cohort follow-up requires current-day OHLC/volume facts"
            )
        execution_gate = "followup_observation_only"
    elif market_observation_status == "confirmed_full_day_suspended":
        if underlying_last_trade_date >= as_of:
            raise ValueError(
                "suspended cohort follow-up requires prior underlying trade date"
            )
        if include_latest_bar_facts:
            raise ValueError(
                "suspended cohort follow-up must not expose stale OHLC as current"
            )
        if not daily_event_source:
            raise ValueError(
                "suspended cohort follow-up requires positive daily-event source"
            )
        execution_gate = "blocked_suspended"
    else:
        raise ValueError(
            f"unsupported cohort follow-up market status: {market_observation_status}"
        )

    return CohortFollowupObservation(
        code_head=code_head,
        instrument_id=instrument_id,
        as_of_trade_date=as_of,
        candidate_key=str(candidate_key),
        outcome_enrollment_trade_date=str(outcome_enrollment_trade_date),
        scanner_presence="absent",
        underlying_last_trade_date=underlying_last_trade_date,
        market_observation_status=market_observation_status,
        execution_context_gate=execution_gate,
        price_mode=price_mode,
        price_basis_id=price_basis_id,
        daily_event_source=daily_event_source,
        daily_event_reason=daily_event_reason,
        as_of_open=(
            _latest_bar_value(analysis, "open")
            if include_latest_bar_facts
            else None
        ),
        as_of_high=(
            _latest_bar_value(analysis, "high")
            if include_latest_bar_facts
            else None
        ),
        as_of_low=(
            _latest_bar_value(analysis, "low")
            if include_latest_bar_facts
            else None
        ),
        as_of_close=(
            _latest_bar_value(analysis, "close")
            if include_latest_bar_facts
            else None
        ),
        as_of_volume=(
            _latest_bar_value(analysis, "volume")
            if include_latest_bar_facts
            else None
        ),
    )


def enrolled_outcome_cohort(
    journal_rows: Iterable[dict[str, Any]],
    *,
    baseline_trade_date: str | None,
) -> dict[str, dict[str, str]]:
    normalized = normalize_journal_rows(
        journal_rows,
        baseline_trade_date=baseline_trade_date,
    )
    enrolled: dict[str, dict[str, str]] = {}
    for row in normalized:
        if row.get("prospective_outcome_eligible") is not True:
            continue
        key = str(row.get("candidate_key") or "")
        instrument_id = str(row.get("instrument_id") or "")
        enrollment = str(row.get("outcome_enrollment_trade_date") or "")
        if not key or not instrument_id or not enrollment:
            raise ValueError(
                "prospective outcome cohort row missing key/instrument/enrollment"
            )
        prior = enrolled.get(key)
        value = {
            "candidate_key": key,
            "instrument_id": instrument_id,
            "outcome_enrollment_trade_date": enrollment,
        }
        if prior is not None and prior != value:
            raise ValueError(f"prospective outcome cohort identity drift: {key}")
        enrolled[key] = value
    return enrolled
