from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Any, Iterable


DEFAULT_OBSERVATION_HORIZON = 20


def _points_by_label(pattern: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(point["label"]): point for point in pattern.get("points", [])}


def _reference_span(pattern: dict[str, Any]) -> tuple[str, float]:
    """Return the schema-specific price span used only to normalize PRZ width.

    The reference span is a calibration denominator, not a Carney identity rule:
    - XABCD: XA
    - standalone ABCD: AB
    - Shark 0XABC: 0B, because the completion is defined around the 0B retest
    - 5-0: BC, because the completion is defined as a BC retracement
    """

    schema = str(pattern.get("schema", "XABCD"))
    points = _points_by_label(pattern)
    pair: tuple[str, str]
    label: str
    if schema == "ABCD":
        pair, label = ("A", "B"), "AB"
    elif schema == "0XABC":
        pair, label = ("0", "B"), "0B"
    elif schema == "FIVE_ZERO":
        pair, label = ("B", "C"), "BC"
    else:
        pair, label = ("X", "A"), "XA"

    left = points.get(pair[0])
    right = points.get(pair[1])
    if not left or not right:
        return label, 0.0
    return label, abs(float(right["price"]) - float(left["price"]))


def _pivot_quality(pattern: dict[str, Any]) -> dict[str, Any]:
    support = pattern.get("pivot_support") or []
    counts = [int(row.get("support_count", 1)) for row in support]
    labels = {str(row.get("label")): row for row in support}
    points = pattern.get("points") or []
    terminal_label = str(points[-1]["label"]) if points else ""
    terminal = labels.get(terminal_label) or {}
    return {
        "min_support": min(counts) if counts else 0,
        "mean_support": mean(counts) if counts else 0.0,
        "max_support": max(counts) if counts else 0,
        "terminal_label": terminal_label,
        "terminal_support": int(terminal.get("support_count", 0)),
        "terminal_scales": list(terminal.get("scales", [])),
        "all_nodes_multi_scale": bool(counts and min(counts) >= 2),
    }


def _reaction_evidence(
    pattern: dict[str, Any],
    *,
    bars_returned: int,
    horizon: int,
) -> dict[str, Any]:
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    points = pattern.get("points") or []
    if not points:
        raise ValueError("completed pattern must contain points")
    completion_index = int(points[-1]["index"])
    available_future_bars = max(0, int(bars_returned) - 1 - completion_index)

    schema = str(pattern.get("schema", "XABCD"))
    if schema == "0XABC":
        targets = pattern.get("reaction_targets") or {}
        t1_name = "50%"
        t2_name = "61.8%"
        t1_bars = targets.get("bars_to_50")
        t2_bars = targets.get("bars_to_618")
        reciprocal_bars = targets.get("bars_to_reciprocal_abcd")
        type_ii_state = None
        family = "shark_reaction_50_618"
    else:
        audit = pattern.get("reaction_audit") or {}
        t1_name = "38.2%"
        t2_name = "61.8%"
        t1_bars = audit.get("bars_to_382")
        t2_bars = audit.get("bars_to_618")
        reciprocal_bars = None
        type_ii_state = audit.get("type_ii_evidence_state")
        family = "type_i_382_618"

    t1_within = t1_bars is not None and int(t1_bars) <= horizon
    t2_within = t2_bars is not None and int(t2_bars) <= horizon
    if available_future_bars < horizon:
        outcome_class = "immature"
    elif t2_within:
        outcome_class = "t2_within_horizon"
    elif t1_within:
        outcome_class = "t1_only_within_horizon"
    else:
        outcome_class = "no_t1_within_horizon"

    return {
        "family": family,
        "observation_horizon_bars": horizon,
        "available_future_bars": available_future_bars,
        "t1_name": t1_name,
        "t2_name": t2_name,
        "bars_to_t1": None if t1_bars is None else int(t1_bars),
        "bars_to_t2": None if t2_bars is None else int(t2_bars),
        "t1_within_horizon": bool(t1_within),
        "t2_within_horizon": bool(t2_within),
        "bars_to_reciprocal_abcd": None if reciprocal_bars is None else int(reciprocal_bars),
        "type_ii_evidence_state": type_ii_state,
        "outcome_class": outcome_class,
    }


def canonical_case_key(record: dict[str, Any]) -> tuple[Any, ...]:
    identity = record["identity"]
    return (
        record["instrument_id"],
        identity["pattern_id"],
        identity["schema"],
        identity["direction"],
        tuple((point["label"], int(point["index"])) for point in identity["points"]),
    )


def build_completed_case_record(
    pattern: dict[str, Any],
    *,
    instrument_id: str,
    price_mode: str,
    bars_returned: int,
    observation_horizon: int = DEFAULT_OBSERVATION_HORIZON,
) -> dict[str, Any]:
    """Build one calibration record with geometry and outcome in separate namespaces.

    ``pattern`` is expected to come from ``LocalHarmonicService.completed`` and therefore
    represents a source-valid completed identity.  The later outcome is deliberately stored
    separately so no success/failure label can retroactively promote or invalidate geometry.
    """

    if pattern.get("state") != "completed":
        raise ValueError("case calibration accepts completed patterns only")
    if pattern.get("is_primary_identity") is False:
        raise ValueError("non-primary identity must be filtered before case calibration")

    span_name, span = _reference_span(pattern)
    prz = pattern.get("prz") or {}
    prz_width = float(prz.get("width", 0.0))
    width_ratio = None if span <= 0 else prz_width / span
    pivot = _pivot_quality(pattern)
    outcome = _reaction_evidence(
        pattern,
        bars_returned=bars_returned,
        horizon=observation_horizon,
    )

    points = [
        {
            "label": str(point["label"]),
            "index": int(point["index"]),
            "price": float(point["price"]),
            "trade_date": point.get("trade_date"),
        }
        for point in pattern.get("points", [])
    ]
    terminal_date = points[-1].get("trade_date") if points else None

    return {
        "instrument_id": instrument_id,
        "price_mode": price_mode,
        "terminal_trade_date": terminal_date,
        "identity": {
            "identity_valid": True,
            "pattern_id": str(pattern["pattern_id"]),
            "schema": str(pattern.get("schema", "XABCD")),
            "direction": str(pattern["direction"]),
            "scale": int(pattern["scale"]),
            "geometry_score": float(pattern["geometry_score"]),
            "points": points,
            "metrics": dict(pattern.get("metrics") or {}),
            "checks": list(pattern.get("checks") or []),
            "completion_class": pattern.get("completion_class"),
        },
        "quality": {
            "reference_span_name": span_name,
            "reference_span": span,
            "prz_low": float(prz.get("price_low", 0.0)),
            "prz_high": float(prz.get("price_high", 0.0)),
            "prz_width": prz_width,
            "prz_width_ratio": width_ratio,
            "pivot": pivot,
        },
        "outcome": outcome,
        "audit_policy": {
            "geometry_score_is_probability": False,
            "pivot_support_changes_identity": False,
            "outcome_changes_identity": False,
            "observation_horizon_is_htcn_policy": True,
        },
    }


def _dedupe_rank(record: dict[str, Any]) -> tuple[float, float, float, float, int]:
    pivot = record["quality"]["pivot"]
    identity = record["identity"]
    return (
        float(pivot["min_support"]),
        float(pivot["mean_support"]),
        float(pivot["terminal_support"]),
        float(identity["geometry_score"]),
        int(identity["scale"]),
    )


def dedupe_case_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse the same physical structure repeated on multiple Pivot scales.

    The retained representative is selected only by geometry/pivot robustness.  Outcome fields
    are intentionally excluded from the ranking to prevent success-biased case construction.
    """

    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[canonical_case_key(record)].append(record)

    out: list[dict[str, Any]] = []
    for rows in grouped.values():
        chosen = max(rows, key=_dedupe_rank)
        chosen = {
            **chosen,
            "observed_scales": sorted({int(row["identity"]["scale"]) for row in rows}),
            "duplicate_scale_count": len({int(row["identity"]["scale"]) for row in rows}),
        }
        out.append(chosen)

    out.sort(
        key=lambda row: (
            str(row.get("terminal_trade_date") or ""),
            str(row["instrument_id"]),
            str(row["identity"]["pattern_id"]),
        )
    )
    return out
