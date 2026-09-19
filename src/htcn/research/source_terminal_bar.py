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
from htcn.harmonic.shark_source import build_shark_source_contract

from .terminal_bar import (
    DEFAULT_TERMINAL_REACTION_HORIZON,
    audit_projected_terminal_price_bar,
)

SOURCE_TERMINAL_RESEARCH_DEFINITION = "m2-source-prz-v6"


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

    M2.30 v6 preserves the v5 XABCD / ABCD / 5-0 contracts and adds Shark only through
    its Volume Three source alignment: the overlap of the 0B 0.886-1.13 completion
    corridor and the AB 1.618-2.24 Extreme Harmonic Impulse corridor.  Legacy Ideal Core
    bounds are never accepted as a substitute.
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

    if schema == "0XABC":
        if any(label not in by_label for label in ("0", "X", "A", "B")):
            return None, "shark_0xab_prefix_missing"
        points = _points_from_prefix(by_label, ("0", "X", "A", "B"))
        try:
            contract = build_shark_source_contract(points)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None, "shark_source_prz_rebuild_failed"
        payload = _source_payload(contract.prz)
        if payload is None:
            return None, contract.prz.source_prz_reason or "shark_source_prz_unresolved"
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


def _rewrite_target_outcome(
    audit: dict[str, Any],
    *,
    frame: pd.DataFrame,
    direction: str,
    reaction_horizon: int,
    t1_name: str,
    t1_price: float,
    t2_name: str,
    t2_price: float,
) -> dict[str, Any]:
    terminal_bar = int(audit["terminal_bar"])
    source = frame.sort_values("trade_date").reset_index(drop=True)
    t1_hit = _target_hit_index(
        source,
        start=terminal_bar + 1,
        target=float(t1_price),
        direction=direction,
    )
    t2_hit = _target_hit_index(
        source,
        start=terminal_bar + 1,
        target=float(t2_price),
        direction=direction,
    )
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
            "t1_name": t1_name,
            "t1_price": float(t1_price),
            "t2_name": t2_name,
            "t2_price": float(t2_price),
            "bars_from_terminal_to_t1": bars_to_t1,
            "bars_from_terminal_to_t2": bars_to_t2,
            "t1_within_horizon": bool(t1_within),
            "t2_within_horizon": bool(t2_within),
            "outcome_class": outcome_class,
        }
    )
    return updated


def _apply_shark_management_targets(
    audit: dict[str, Any],
    *,
    record: dict[str, Any],
    frame: pd.DataFrame,
    reaction_horizon: int,
) -> dict[str, Any]:
    """Replace generic Shark 50/61.8 targets with the Volume Three first-target contract.

    At the source-aligned Terminal Bar the terminal extreme acts as the observable C
    completion price.  The initial Shark management target is the first encountered of
    50% B-to-Terminal and Reciprocal AB=CD.  The next target is 50% when reciprocal came
    first; otherwise it is the wider 61.8% B-to-Terminal measurement.
    """

    if str(record.get("schema")) != "0XABC" or audit.get("status") != "terminal_price_bar_observed":
        return audit
    points = {str(point.get("label")): point for point in record.get("prefix_points") or []}
    if "A" not in points or "B" not in points:
        raise ValueError("Shark target calculation requires A and B")

    terminal_price = float(audit["terminal_price"])
    a_price = float(points["A"]["price"])
    b_price = float(points["B"]["price"])
    bc_span = abs(b_price - terminal_price)
    ab_span = abs(a_price - b_price)
    if min(bc_span, ab_span) <= 0:
        raise ValueError("Shark source-aligned management spans must be positive")

    direction = str(record["direction"])
    sign = 1.0 if direction == "bullish" else -1.0
    target_50 = terminal_price + sign * 0.50 * bc_span
    target_618 = terminal_price + sign * 0.618 * bc_span
    reciprocal = terminal_price + sign * ab_span

    distance_50 = abs(target_50 - terminal_price)
    distance_reciprocal = abs(reciprocal - terminal_price)
    eps = 1e-12 * max(1.0, distance_50, distance_reciprocal)
    if abs(distance_50 - distance_reciprocal) <= eps:
        initial = target_50
        initial_basis = "50_percent_and_reciprocal_abcd_tie"
        next_target = target_618
        next_name = "61.8% BC"
    elif distance_reciprocal < distance_50:
        initial = reciprocal
        initial_basis = "reciprocal_abcd"
        next_target = target_50
        next_name = "50% BC"
    else:
        initial = target_50
        initial_basis = "50_percent"
        next_target = target_618
        next_name = "61.8% BC"

    updated = _rewrite_target_outcome(
        audit,
        frame=frame,
        direction=direction,
        reaction_horizon=reaction_horizon,
        t1_name="Shark first 5-0 measurement",
        t1_price=initial,
        t2_name=next_name,
        t2_price=next_target,
    )
    updated.update(
        {
            "automatic_target_basis": "shark_first_5_0_measurement",
            "shark_target_50": float(target_50),
            "shark_target_618": float(target_618),
            "shark_reciprocal_abcd_target": float(reciprocal),
            "shark_initial_target_basis": initial_basis,
        }
    )
    semantics = dict(updated.get("source_semantics") or {})
    semantics["targets"] = (
        "Volume Three Shark management: the first target is whichever is encountered first "
        "from the Terminal extreme, 50% BC or Reciprocal AB=CD. The 61.8% BC measure remains "
        "a wider 5-0 management level and is not part of Shark identity or Source Raw PRZ."
    )
    updated["source_semantics"] = semantics
    return updated


def _apply_five_zero_type_i_targets(
    audit: dict[str, Any],
    *,
    record: dict[str, Any],
    frame: pd.DataFrame,
    reaction_horizon: int,
) -> dict[str, Any]:
    """Correct v6 5-0 automatic targets to the C->Terminal completion leg."""

    if str(record.get("schema")) != "FIVE_ZERO" or audit.get("status") != "terminal_price_bar_observed":
        return audit
    points = {str(point.get("label")): point for point in record.get("prefix_points") or []}
    if "C" not in points:
        raise ValueError("FIVE_ZERO Type-I target calculation requires C")

    terminal_price = float(audit["terminal_price"])
    c_price = float(points["C"]["price"])
    span = abs(c_price - terminal_price)
    if span <= 0:
        raise ValueError("FIVE_ZERO C/terminal reaction span must be positive")
    direction = str(record["direction"])
    sign = 1.0 if direction == "bullish" else -1.0
    t1_price = terminal_price + sign * 0.382 * span
    t2_price = terminal_price + sign * 0.618 * span

    updated = _rewrite_target_outcome(
        audit,
        frame=frame,
        direction=direction,
        reaction_horizon=reaction_horizon,
        t1_name="38.2%",
        t1_price=t1_price,
        t2_name="61.8%",
        t2_price=t2_price,
    )
    updated.update(
        {
            "automatic_target_basis": "five_zero_c_to_terminal",
            "automatic_target_anchor_price": c_price,
        }
    )
    semantics = dict(updated.get("source_semantics") or {})
    semantics["targets"] = (
        "M2.29+ FIVE_ZERO uses 38.2%/61.8% of the C-to-Terminal completion leg. "
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
    audit = _apply_shark_management_targets(
        dict(audit),
        record=rewritten,
        frame=frame,
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
