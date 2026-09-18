from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Protocol


WORKFLOW_BUCKET_ORDER: dict[str, int] = {
    "execution_evaluation": 0,
    "reaction_observation": 1,
    "waiting": 2,
    "evidence_insufficient": 3,
}


class AnalysisService(Protocol):
    def analyze(
        self,
        instrument_id: str,
        *,
        bars: int,
        scales: tuple[int, ...],
    ) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class OperatorQueueContract:
    version: int = 1
    source_of_truth: str = "existing_source_lifecycle_and_decision_narrative"
    ranking_mode: str = "workflow_bucket_only"
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
            "source_of_truth": self.source_of_truth,
            "ranking_mode": self.ranking_mode,
            "predictive_score_used": self.predictive_score_used,
            "historical_outcome_used": self.historical_outcome_used,
            "alpha_inference_allowed": self.alpha_inference_allowed,
            "is_trade_instruction": self.is_trade_instruction,
            "mutates_harmonic_identity": self.mutates_harmonic_identity,
            "mutates_source_raw_prz": self.mutates_source_raw_prz,
            "owns_lifecycle": self.owns_lifecycle,
        }


def discover_local_instruments(
    data_root: str | Path,
    *,
    limit: int = 0,
) -> list[str]:
    daily_root = Path(data_root) / "daily"
    if not daily_root.exists():
        return []
    items = sorted(path.stem for path in daily_root.glob("*.parquet"))
    return items if limit <= 0 else items[:limit]


def _display_key(instrument_id: str, pattern: dict[str, Any]) -> str:
    """Stable product identity for comparing queue observations.

    Trade dates are preferred because rolling a fixed-size chart window can
    renumber bar indexes even when the underlying harmonic candidate is the
    same. This key is product-only and does not replace M4 candidate identity.
    """
    points = pattern.get("points") or []
    signature_parts: list[str] = []
    for point in points:
        trade_date = str(point.get("trade_date") or "").strip()
        if trade_date:
            signature_parts.append(trade_date)
        elif point.get("index") is not None:
            signature_parts.append(f"i{point.get('index')}")
    point_signature = "-".join(signature_parts)
    return (
        f"{instrument_id}:{pattern.get('pattern_id')}:{pattern.get('schema')}:"
        f"{pattern.get('direction')}:S{pattern.get('scale')}:{point_signature}"
    )


def _primary_patterns(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    patterns = [
        *(analysis.get("completed") or []),
        *(analysis.get("forming") or []),
    ]
    return [
        dict(pattern)
        for pattern in patterns
        if pattern.get("is_primary_identity") is not False
    ]


def _queue_item(
    *,
    instrument_id: str,
    analysis: dict[str, Any],
    pattern: dict[str, Any],
) -> dict[str, Any] | None:
    lifecycle = pattern.get("source_lifecycle")
    narrative = pattern.get("decision_narrative")
    if not isinstance(lifecycle, dict) or not isinstance(narrative, dict):
        return None

    action_state = str(
        narrative.get("action_state") or "evidence_insufficient"
    )
    lifecycle_state = str(
        lifecycle.get("state") or "source_clock_unavailable"
    )
    if action_state not in WORKFLOW_BUCKET_ORDER:
        action_state = "evidence_insufficient"

    return {
        "display_key": _display_key(instrument_id, pattern),
        "instrument_id": instrument_id,
        "last_trade_date": analysis.get("last_trade_date"),
        "price_mode": analysis.get("price_mode"),
        "warning": analysis.get("warning"),
        "pattern_id": pattern.get("pattern_id"),
        "schema": pattern.get("schema"),
        "direction": pattern.get("direction"),
        "scale": pattern.get("scale"),
        "pattern_state": pattern.get("state"),
        "action_state": action_state,
        "workflow_bucket_order": WORKFLOW_BUCKET_ORDER[action_state],
        "lifecycle_state": lifecycle_state,
        "state_reason": lifecycle.get("state_reason"),
        "current_position": narrative.get("current_position"),
        "first_watch": narrative.get("first_watch"),
        "next_watch": narrative.get("next_watch"),
        "upgrade_blocker": narrative.get("upgrade_blocker"),
        "next_key_price": narrative.get("next_key_price"),
        "next_key_price_role": narrative.get("next_key_price_role"),
        "execution_context_gate": narrative.get("execution_context_gate"),
        "context_cautions": list(narrative.get("context_cautions") or []),
        "source_prz_low": lifecycle.get("source_prz_low"),
        "source_prz_high": lifecycle.get("source_prz_high"),
        "bars_since_terminal": lifecycle.get("bars_since_terminal"),
        "is_trade_instruction": False,
        "predictive_score_used": False,
        "alpha_inference_allowed": False,
    }


def build_operator_queue(
    service: AnalysisService,
    instrument_ids: Iterable[str],
    *,
    bars: int = 420,
    scales: tuple[int, ...] = (3, 5, 8, 13),
    include_evidence_insufficient: bool = True,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    analyzed = 0
    observed_trade_dates: set[str] = set()

    instrument_list = [str(value) for value in instrument_ids]
    for instrument_id in instrument_list:
        try:
            analysis = service.analyze(
                instrument_id,
                bars=bars,
                scales=scales,
            )
            analyzed += 1
            last_trade_date = str(
                analysis.get("last_trade_date") or ""
            ).strip()
            if last_trade_date:
                observed_trade_dates.add(last_trade_date)
            for pattern in _primary_patterns(analysis):
                item = _queue_item(
                    instrument_id=instrument_id,
                    analysis=analysis,
                    pattern=pattern,
                )
                if item is None:
                    continue
                if (
                    not include_evidence_insufficient
                    and item["action_state"] == "evidence_insufficient"
                ):
                    continue
                items.append(item)
        except Exception as exc:
            errors.append({
                "instrument_id": instrument_id,
                "error": f"{type(exc).__name__}: {exc}",
            })

    items.sort(
        key=lambda item: (
            int(item["workflow_bucket_order"]),
            str(item["instrument_id"]),
            str(item["display_key"]),
        )
    )

    action_counts = Counter(str(item["action_state"]) for item in items)
    lifecycle_counts = Counter(str(item["lifecycle_state"]) for item in items)
    instrument_with_candidates = len({
        str(item["instrument_id"]) for item in items
    })

    sorted_trade_dates = sorted(observed_trade_dates)
    as_of_trade_date = (
        sorted_trade_dates[0]
        if len(sorted_trade_dates) == 1
        else None
    )
    observation_integrity = (
        "single_as_of"
        if len(sorted_trade_dates) == 1
        else ("empty" if not sorted_trade_dates else "mixed_as_of")
    )

    return {
        "schema_version": 2,
        "contract": OperatorQueueContract().as_payload(),
        "as_of_trade_date": as_of_trade_date,
        "observed_trade_dates": sorted_trade_dates,
        "observation_integrity": observation_integrity,
        "instrument_count": len(instrument_list),
        "analyzed_instrument_count": analyzed,
        "failed_instrument_count": len(errors),
        "candidate_count": len(items),
        "candidate_instrument_count": instrument_with_candidates,
        "action_state_counts": dict(sorted(action_counts.items())),
        "lifecycle_state_counts": dict(sorted(lifecycle_counts.items())),
        "items": items,
        "errors": errors,
    }
