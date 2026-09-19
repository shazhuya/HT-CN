from __future__ import annotations

from copy import deepcopy
from typing import Any

import pandas as pd

from .terminal_bar import DEFAULT_TERMINAL_REACTION_HORIZON, audit_projected_terminal_price_bar
from .walk_forward import DEFAULT_FORWARD_HORIZON, walk_forward_forming_signals

TYPE_I_T5_EVIDENCE_VERSION = "m2-type-i-holdout-v1"
TYPE_I_T5_EXTERNAL_REPLICATION_VERSION = "m2-type-i-external-replication-v1"

# Frozen historical evidence references. These values are not live probabilities and never
# participate in Carney geometry/identity. The 45-symbol Holdout and the disjoint 60-symbol
# external replication are deliberately kept separate instead of being silently pooled.
_FROZEN_REFERENCE: dict[str, Any] = {
    "status": "confirmed",
    "preregistration_id": TYPE_I_T5_EVIDENCE_VERSION,
    "dataset_id": "a-share-research-v2-45",
    "snapshot_cutoff": "2026-09-15",
    "cohort": "Terminal Price Bar events still pending T2 at T+5",
    "endpoint": "first T2 hit during T+6..T+20",
    "exposure": {
        "name": "full_prz_exit_by_t5",
        "records": 115,
        "endpoint_hits": 40,
        "endpoint_rate": 0.34782608695652173,
    },
    "comparator": {
        "name": "no_full_exit_by_t5",
        "records": 198,
        "endpoint_hits": 39,
        "endpoint_rate": 0.19696969696969696,
    },
    "absolute_rate_difference": 0.15085638998682477,
    "newcombe_95_ci": {
        "lower": 0.049612411917687296,
        "upper": 0.2541290679331789,
    },
    "external_replication": {
        "status": "confirmed",
        "preregistration_id": TYPE_I_T5_EXTERNAL_REPLICATION_VERSION,
        "dataset_id": "a-share-type-i-external-replication-v1-60",
        "snapshot_cutoff": "2026-09-15",
        "requested_symbols": 60,
        "successful_symbols": 60,
        "eligible_pending_t2_at_t5": 1918,
        "exposure": {
            "name": "full_prz_exit_by_t5",
            "records": 736,
            "endpoint_hits": 257,
            "endpoint_rate": 0.3491847826086957,
        },
        "comparator": {
            "name": "no_full_exit_by_t5",
            "records": 1182,
            "endpoint_hits": 213,
            "endpoint_rate": 0.1802030456852792,
        },
        "absolute_rate_difference": 0.16898173692341648,
        "newcombe_95_ci": {
            "lower": 0.12831888515284715,
            "upper": 0.2098515212802209,
        },
        "concentration": {
            "eligible_symbols": 60,
            "largest_symbol_share": 0.026068821689259645,
        },
        "interpretation": (
            "独立60股、与原45股零重叠的历史复现再次确认相同T+5关系。"
            "复现集是预先冻结的跨行业convenience set，不是随机全A股样本。"
        ),
    },
    "interpretation": (
        "冻结45股Holdout与独立60股外部复现均支持同一个source-aligned Type-I T+5关系："
        "仅对T+5时仍未到达T2的Terminal Price Bar事件，T+5内完整脱离PRZ与随后"
        "T+6..T+20更高的T2 progression比例相关。这不是个股收益概率、胜率或交易建议，"
        "也不修改Carney形态身份。"
    ),
}


def frozen_type_i_t5_reference() -> dict[str, Any]:
    """Return an isolated copy of the consumed Holdout + external replication references."""

    return deepcopy(_FROZEN_REFERENCE)


def classify_type_i_t5_audit(audit: dict[str, Any]) -> dict[str, Any]:
    """Translate one source-aligned Terminal-Bar audit into a live T+5 evidence state.

    The classification deliberately starts from the M2.17 Terminal Price Bar rather than
    the later right-confirmed D Pivot. This keeps the live state aligned with the frozen
    M2.22 confirmatory test and M2.24 external replication. It never changes geometry,
    pattern identity or PRZ.
    """

    if audit.get("status") != "terminal_price_bar_observed":
        return {
            "state": "not_applicable",
            "display_label": "不适用",
            "eligible_for_frozen_contrast": False,
            "historical_group": None,
            "bars_until_t5": None,
            "endpoint_state": "not_applicable",
        }

    available = int(audit.get("available_future_bars_after_terminal") or 0)
    bars_to_t2 = audit.get("bars_from_terminal_to_t2")
    bars_to_t2 = None if bars_to_t2 is None else int(bars_to_t2)
    exit_bar = audit.get("bars_from_terminal_to_full_prz_exit")
    exit_bar = None if exit_bar is None else int(exit_bar)

    # Once T2 has already arrived by T+5, the event is no longer a member of the
    # preregistered "pending T2 at T+5" cohort, even if five future bars are not yet all visible.
    if bars_to_t2 is not None and bars_to_t2 <= 5:
        state = "t2_already_reached_by_t5"
        label = "T2已在T+5前到达"
        eligible = False
        historical_group = None
        bars_until_t5 = 0
    elif available < 5:
        state = "pending_t5_observation"
        label = "等待T+5观察完成"
        eligible = False
        historical_group = None
        bars_until_t5 = 5 - available
    elif exit_bar is not None and 1 <= exit_bar <= 5:
        state = "full_prz_exit_by_t5"
        label = "T+5内完整脱离PRZ"
        eligible = True
        historical_group = "exposure"
        bars_until_t5 = 0
    else:
        state = "no_full_prz_exit_by_t5"
        label = "T+5内未完整脱离PRZ"
        eligible = True
        historical_group = "comparator"
        bars_until_t5 = 0

    if bars_to_t2 is not None and bars_to_t2 <= 5:
        endpoint_state = "t2_hit_by_t5"
    elif bars_to_t2 is not None and 6 <= bars_to_t2 <= 20:
        endpoint_state = "t2_hit_t6_t20"
    elif available < 20:
        endpoint_state = "pending_t20"
    else:
        endpoint_state = "no_t2_by_t20"

    return {
        "state": state,
        "display_label": label,
        "eligible_for_frozen_contrast": eligible,
        "historical_group": historical_group,
        "bars_until_t5": bars_until_t5,
        "endpoint_state": endpoint_state,
    }


def build_type_i_t5_events(
    frame: pd.DataFrame,
    *,
    instrument_id: str,
    scales: tuple[int, ...],
    forming_horizon: int = DEFAULT_FORWARD_HORIZON,
    reaction_horizon: int = DEFAULT_TERMINAL_REACTION_HORIZON,
    max_events: int = 12,
) -> list[dict[str, Any]]:
    """Build recent source-aligned Type-I T+5 evidence events for the workbench.

    This is intentionally a separate evidence stream. Static completed-pattern payloads use
    later confirmed Pivots and therefore must not be retrofitted with the Terminal-Bar evidence.
    The replay here reproduces the no-lookahead forming signal and then audits the first
    source-aligned Terminal Price Bar from that projection.
    """

    if max_events < 1:
        raise ValueError("max_events must be >= 1")
    if frame.empty:
        return []

    source = frame.sort_values("trade_date").reset_index(drop=True).copy()
    records = walk_forward_forming_signals(
        source,
        scales=scales,
        horizon=forming_horizon,
    )
    reference = frozen_type_i_t5_reference()
    events: list[dict[str, Any]] = []
    for record in records:
        audit = audit_projected_terminal_price_bar(
            record,
            frame=source,
            forming_horizon=forming_horizon,
            reaction_horizon=reaction_horizon,
        )
        if audit.get("status") != "terminal_price_bar_observed":
            continue
        classification = classify_type_i_t5_audit(audit)
        terminal_bar = int(audit["terminal_bar"])
        source_scale = int(record["source_scale"])
        pattern_id = str(record["pattern_id"])
        schema = str(record["schema"])
        direction = str(record["direction"])
        events.append(
            {
                "event_id": (
                    f"{instrument_id}:{pattern_id}:{schema}:{direction}:"
                    f"S{source_scale}:signal{int(record['signal_bar'])}:terminal{terminal_bar}"
                ),
                "instrument_id": instrument_id,
                "pattern_id": pattern_id,
                "schema": schema,
                "direction": direction,
                "source_scale": source_scale,
                "signal_scales": list(record.get("signal_scales") or [source_scale]),
                "forming_signal_bar": int(record["signal_bar"]),
                "forming_signal_trade_date": str(record["signal_trade_date"]),
                "terminal_bar": terminal_bar,
                "terminal_trade_date": str(audit["terminal_trade_date"]),
                "terminal_price": float(audit["terminal_price"]),
                "prz": {
                    "price_low": float(audit["prz"]["price_low"]),
                    "price_high": float(audit["prz"]["price_high"]),
                },
                "t1_name": str(audit["t1_name"]),
                "t1_price": float(audit["t1_price"]),
                "t2_name": str(audit["t2_name"]),
                "t2_price": float(audit["t2_price"]),
                "bars_from_terminal_to_t1": audit.get("bars_from_terminal_to_t1"),
                "bars_from_terminal_to_t2": audit.get("bars_from_terminal_to_t2"),
                "bars_from_terminal_to_full_prz_exit": audit.get(
                    "bars_from_terminal_to_full_prz_exit"
                ),
                "available_future_bars_after_terminal": int(
                    audit["available_future_bars_after_terminal"]
                ),
                "t5_evidence": classification,
                "historical_evidence": reference,
                "identity_separation": (
                    "该事件来自source-aligned forming→Terminal-Bar回放；它是完成后证据层，"
                    "不创建、不删除、不改写Carney几何身份。"
                ),
            }
        )

    events.sort(
        key=lambda row: (
            -int(row["terminal_bar"]),
            -int(row["forming_signal_bar"]),
            str(row["pattern_id"]),
            -int(row["source_scale"]),
        )
    )
    return events[:max_events]
