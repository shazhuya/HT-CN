from __future__ import annotations

from copy import deepcopy
from typing import Any

import pandas as pd

from htcn.harmonic.abcd import project_forming_abcd
from htcn.harmonic.abcd_source import with_abcd_source_prz
from htcn.harmonic.five_zero_source import build_five_zero_source_contract
from htcn.harmonic.models import HarmonicPoint
from htcn.harmonic.prz import build_xabcd_prz
from htcn.harmonic.rules import CARNEY_RULES

from .terminal_bar import (
    DEFAULT_TERMINAL_REACTION_HORIZON,
    audit_projected_terminal_price_bar,
)


SOURCE_TERMINAL_RESEARCH_DEFINITION = "m2-source-prz-v5"


def _source_payload(prz) -> dict[str, Any] | None:
    if not prz.has_source_prz:
        return None
    return {
        "price_low": float(prz.source_prz_low),
        "price_high": float(prz.source_prz_high),
        "width": float(prz.source_prz_high - prz.source_prz_low),
        "basis": "source_raw_prz",
        "component_names": list(prz.source_prz_component_names),
        "defining_component": prz.source_prz_defining_component,
        "selection_method": prz.source_prz_selection_method,
        "source_refs": list(prz.source_prz_source_refs),
        "profile_version": 2,
    }


def _points_from_prefix(
    by_label: dict[str, dict[str, Any]],
    labels: tuple[str, ...],
) -> tuple[HarmonicPoint, ...]:
    return tuple(
        HarmonicPoint(
            label=label,
            index=int(by_label[label]["index"]),
            price=float(by_label[label]["price"]),
        )
        for label in labels
    )


def _source_prz_projection(record: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Rebuild Source Raw PRZ from signal-time geometry only.

    M2.29 v5 preserves all v4 source contracts and additionally admits 5-0 only through its
    reconciled Volume Two structural Raw PRZ: 50% BC retracement + Reciprocal AB=CD.
    The Volume Three 61.8 execution refinement is deliberately excluded from this Terminal-Bar
    Raw PRZ. Legacy Ideal Core bounds are never accepted as a substitute.
    """

    schema = str(record.get("schema"))
    raw_points = list(record.get("prefix_points") or [])
    by_label = {str(point.get("label")): point for point in raw_points}

    if schema == "XABCD":
        pattern_id = str(record.get("pattern_id") or "")
        rule = CARNEY_RULES.get(pattern_id)
        if rule is None or rule.schema != "XABCD":
            return None, "source_prz_profile_missing"
        if any(label not in by_label for label in ("X", "A", "B", "C")):
            return None, "xabc_prefix_missing"
        points = _points_from_prefix(by_label, ("X", "A", "B", "C"))
        try:
            prz = build_xabcd_prz(rule, points)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None, "source_prz_rebuild_failed"
        payload = _source_payload(prz)
        if payload is None:
            return None, prz.source_prz_reason or "source_prz_unresolved"
        return payload, None

    if schema == "ABCD":
        if any(label not in by_label for label in ("A", "B", "C")):
            return None, "abc_prefix_missing"
        points = _points_from_prefix(by_label, ("A", "B", "C"))
        try:
            projection = project_forming_abcd(points)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None, "abcd_source_prz_rebuild_failed"
        if projection is None:
            return None, "abcd_forming_projection_unavailable"
        prz = with_abcd_source_prz(projection.prz)
        payload = _source_payload(prz)
        if payload is None:
            return None, "abcd_source_prz_unresolved"
        return payload, None

    if schema == "FIVE_ZERO":
        if any(label not in by_label for label in ("X", "A", "B", "C")):
            return None, "five_zero_xabc_prefix_missing"
        points = _points_from_prefix(by_label, ("X", "A", "B", "C"))
        try:
            contract = build_five_zero_source_contract(points)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None, "five_zero_source_prz_rebuild_failed"
        payload = _source_payload(contract.prz)
        if payload is None:
            return None, "five_zero_source_prz_unresolved"
        return payload, None

    return None, "source_prz_not_frozen_for_schema"


def _target_hit_index(
    frame: pd.DataFrame,
    *,
    start: int,
    target: float,
    direction: str,
) -> int | None:
    for index in range(max(0, int(start)), len(frame)):
        row = frame.iloc[index]
        if direction == "bullish" and float(row["high"]) >= target:
            return index
        if direction == "bearish" and float(row["low"]) <= target:
            return index
    return None


def _apply_five_zero_type_i_targets(
    audit: dict[str, Any],
    *,
    record: dict[str, Any],
    frame: pd.DataFrame,
    reaction_horizon: int,
) -> dict[str, Any]:
    """Correct v5 5-0 automatic targets to the C->Terminal completion leg.

    The shared legacy Terminal-Bar helper uses A->Terminal for standard XABCD structures.
    That axis is not the completion leg of a 5-0.  M2.29 therefore keeps legacy history intact
    and adjusts only v5 FIVE_ZERO audits to the C->D/Terminal pattern segment before any Type-I
    rates are computed.
    """

    if str(record.get("schema")) != "FIVE_ZERO" or audit.get("status") != "terminal_price_bar_observed":
        return audit
    points = {str(point.get("label")): point for point in record.get("prefix_points") or []}
    if "C" not in points:
        raise ValueError("FIVE_ZERO Type-I target calculation requires C")

    source = frame.sort_values("trade_date").reset_index(drop=True)
    terminal_bar = int(audit["terminal_bar"])
    terminal_price = float(audit["terminal_price"])
    c_price = float(points["C"]["price"])
    span = abs(c_price - terminal_price)
    if span <= 0:
        raise ValueError("FIVE_ZERO C/terminal reaction span must be positive")
    direction = str(record["direction"])
    sign = 1.0 if direction == "bullish" else -1.0
    t1_price = terminal_price + sign * 0.382 * span
    t2_price = terminal_price + sign * 0.618 * span
    t1_hit = _target_hit_index(source, start=terminal_bar + 1, target=t1_price, direction=direction)
    t2_hit = _target_hit_index(source, start=terminal_bar + 1, target=t2_price, direction=direction)
    bars_to_t1 = None if t1_hit is None else int(t1_hit - terminal_bar)
    bars_to_t2 = None if t2_hit is None else int(t2_hit - terminal_bar)
    t1_within = bars_to_t1 is not None and bars_to_t1 <= reaction_horizon
    t2_within = bars_to_t2 is not None and bars_to_t2 <= reaction_horizon
    available = int(audit.get("available_future_bars_after_terminal") or 0)
    if available < reaction_horizon:
        outcome_class = "immature"
    elif t2_within:
        outcome_class = "t2_within_horizon"
    elif t1_within:
        outcome_class = "t1_only_within_horizon"
    else:
        outcome_class = "no_t1_within_horizon"

    updated = dict(audit)
    updated.update(
        {
            "t1_name": "38.2%",
            "t1_price": float(t1_price),
            "t2_name": "61.8%",
            "t2_price": float(t2_price),
            "bars_from_terminal_to_t1": bars_to_t1,
            "bars_from_terminal_to_t2": bars_to_t2,
            "t1_within_horizon": bool(t1_within),
            "t2_within_horizon": bool(t2_within),
            "outcome_class": outcome_class,
            "automatic_target_basis": "five_zero_c_to_terminal",
            "automatic_target_anchor_price": c_price,
        }
    )
    semantics = dict(updated.get("source_semantics") or {})
    semantics["targets"] = (
        "M2.29 FIVE_ZERO uses 38.2%/61.8% of the C-to-Terminal completion leg. "
        "The shared standard XABCD A-to-Terminal target basis is not reused for 5-0."
    )
    updated["source_semantics"] = semantics
    return updated


def audit_source_prz_terminal_price_bar(
    record: dict[str, Any],
    *,
    frame: pd.DataFrame,
    forming_horizon: int,
    reaction_horizon: int = DEFAULT_TERMINAL_REACTION_HORIZON,
) -> dict[str, Any]:
    """Current Terminal-Bar audit using only frozen Source Raw PRZ definitions."""

    source_prz, reason = _source_prz_projection(record)
    if source_prz is None:
        return {
            "status": "source_prz_unresolved",
            "research_definition": SOURCE_TERMINAL_RESEARCH_DEFINITION,
            "prz_basis": "none_fail_closed",
            "pattern_id": record.get("pattern_id"),
            "schema": record.get("schema"),
            "reason": reason,
            "source_semantics": (
                "Source-aligned Terminal-Bar research requires a frozen Source Raw PRZ; "
                "legacy Ideal Core price_low/high are not accepted as a substitute."
            ),
        }

    rewritten = deepcopy(record)
    rewritten["prz"] = {
        "price_low": source_prz["price_low"],
        "price_high": source_prz["price_high"],
        "width": source_prz["width"],
    }
    audit = audit_projected_terminal_price_bar(
        rewritten,
        frame=frame,
        forming_horizon=forming_horizon,
        reaction_horizon=reaction_horizon,
    )
    audit = _apply_five_zero_type_i_targets(
        dict(audit),
        record=rewritten,
        frame=frame,
        reaction_horizon=reaction_horizon,
    )
    audit.update(
        {
            "research_definition": SOURCE_TERMINAL_RESEARCH_DEFINITION,
            "prz_basis": "source_raw_prz",
            "source_prz_profile_version": 2,
            "source_prz_component_names": source_prz["component_names"],
            "source_prz_defining_component": source_prz["defining_component"],
            "source_prz_selection_method": source_prz["selection_method"],
            "source_prz_source_refs": source_prz["source_refs"],
        }
    )
    if isinstance(audit.get("prz"), dict):
        audit["prz"] = {
            **audit["prz"],
            "basis": "source_raw_prz",
            "component_names": source_prz["component_names"],
            "defining_component": source_prz["defining_component"],
            "selection_method": source_prz["selection_method"],
        }
    return audit
