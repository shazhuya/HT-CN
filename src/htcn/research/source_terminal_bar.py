from __future__ import annotations

from copy import deepcopy
from typing import Any

import pandas as pd

from htcn.harmonic.models import HarmonicPoint
from htcn.harmonic.prz import build_xabcd_prz
from htcn.harmonic.rules import CARNEY_RULES

from .terminal_bar import (
    DEFAULT_TERMINAL_REACTION_HORIZON,
    audit_projected_terminal_price_bar,
)


SOURCE_TERMINAL_RESEARCH_DEFINITION = "m2-source-prz-v3"


def _source_prz_projection(record: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Rebuild the source Raw PRZ from signal-time geometry only.

    M2.17/M2.26 historical research serialized ``prz.price_low/high`` from the generic
    ``PotentialReversalZone.price_*`` aliases.  M2.26 later clarified that those aliases mean
    the HT-CN ideal convergence core, not the source Raw PRZ.  M2.27 therefore reconstructs
    source bounds from the already-observable XABC prefix and the frozen pattern profile rather
    than reusing the legacy serialized pair.
    """

    if str(record.get("schema")) != "XABCD":
        return None, "source_prz_not_frozen_for_schema"

    pattern_id = str(record.get("pattern_id") or "")
    rule = CARNEY_RULES.get(pattern_id)
    if rule is None or rule.schema != "XABCD":
        return None, "source_prz_profile_missing"

    raw_points = list(record.get("prefix_points") or [])
    by_label = {str(point.get("label")): point for point in raw_points}
    if any(label not in by_label for label in ("X", "A", "B", "C")):
        return None, "xabc_prefix_missing"

    points = tuple(
        HarmonicPoint(
            label=label,
            index=int(by_label[label]["index"]),
            price=float(by_label[label]["price"]),
        )
        for label in ("X", "A", "B", "C")
    )
    try:
        prz = build_xabcd_prz(rule, points)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None, "source_prz_rebuild_failed"

    if not prz.has_source_prz:
        return None, prz.source_prz_reason or "source_prz_unresolved"

    return (
        {
            "price_low": float(prz.source_prz_low),
            "price_high": float(prz.source_prz_high),
            "width": float(prz.source_prz_high - prz.source_prz_low),
            "basis": "source_raw_prz",
            "component_names": list(prz.source_prz_component_names),
            "defining_component": prz.source_prz_defining_component,
            "selection_method": prz.source_prz_selection_method,
            "source_refs": list(prz.source_prz_source_refs),
            "profile_version": 1,
        },
        None,
    )


def audit_source_prz_terminal_price_bar(
    record: dict[str, Any],
    *,
    frame: pd.DataFrame,
    forming_horizon: int,
    reaction_horizon: int = DEFAULT_TERMINAL_REACTION_HORIZON,
) -> dict[str, Any]:
    """M2.27 v3 Terminal-Bar audit using the actual frozen source Raw PRZ.

    The legacy M2.17/M2.26 audit remains untouched for historical reproducibility.  This
    current research definition refuses to promote ideal-core bounds for schemas whose source
    Raw PRZ has not yet been frozen.
    """

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
                "M2.27 source-aligned Terminal-Bar research requires a frozen source Raw PRZ; "
                "legacy ideal-core price_low/high are not accepted as a substitute."
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
    audit = dict(audit)
    audit.update(
        {
            "research_definition": SOURCE_TERMINAL_RESEARCH_DEFINITION,
            "prz_basis": "source_raw_prz",
            "source_prz_profile_version": 1,
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
