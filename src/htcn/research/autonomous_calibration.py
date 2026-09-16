from __future__ import annotations

from typing import Any, Iterable

import pandas as pd

from .quality_gate import evaluate_gate_library
from .source_terminal_bar import (
    SOURCE_TERMINAL_RESEARCH_DEFINITION,
    audit_source_prz_terminal_price_bar,
)
from .terminal_bar import (
    DEFAULT_TERMINAL_REACTION_HORIZON,
    build_terminal_bar_calibration,
)
from .time_split import (
    assign_purged_split,
    derive_boundaries,
    learn_numeric_thresholds,
    mature_forward_records,
    outcome_summary,
    split_manifest,
)
from .type_i_confirmation import build_type_i_early_path_report
from .type_i_exit_timing import build_type_i_exit_timing_report
from .type_i_robustness import build_type_i_early_path_robustness_report


_TERMINAL_AUDIT_REQUIRED_FIELDS = {
    "pattern_id",
    "schema",
    "direction",
    "prz",
    "prefix_points",
}


def _terminal_audit_payload(
    row: dict[str, Any],
    *,
    frame: pd.DataFrame,
    horizon: int,
) -> dict[str, Any]:
    """Attach the current source-Raw-PRZ Terminal Price Bar audit where possible.

    Historical M2.17/M2.26 research remains reproducible through the legacy terminal-bar
    function.  Current M2.27 research uses ``m2-source-prz-v3``: it reconstructs a frozen
    source Raw PRZ from signal-time XABC geometry and fails closed for schemas/patterns whose
    source PRZ is still unresolved.  Legacy ideal-core bounds are never promoted to source PRZ.
    """
    missing = sorted(field for field in _TERMINAL_AUDIT_REQUIRED_FIELDS if field not in row)
    if missing:
        return {
            "status": "not_applicable_missing_projection_fields",
            "research_definition": SOURCE_TERMINAL_RESEARCH_DEFINITION,
            "missing_fields": missing,
            "source_semantics": "Terminal Price Bar audit applies only to a fully described harmonic projection; legacy timing-only records remain valid enrichment inputs.",
        }
    return audit_source_prz_terminal_price_bar(
        row,
        frame=frame,
        forming_horizon=horizon,
        reaction_horizon=DEFAULT_TERMINAL_REACTION_HORIZON,
    )


def enrich_walk_forward_records(
    records: Iterable[dict[str, Any]],
    *,
    frame: pd.DataFrame,
    instrument_id: str,
    horizon: int,
) -> list[dict[str, Any]]:
    """Attach symbol identity, observation dates and the current v3 Terminal-Bar audit."""
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    if "trade_date" not in frame.columns:
        raise ValueError("frame must contain trade_date")
    source = frame.sort_values("trade_date").reset_index(drop=True)
    out: list[dict[str, Any]] = []
    for original in records:
        row = dict(original)
        row["instrument_id"] = instrument_id
        signal_bar = int(row["signal_bar"])
        end_bar = signal_bar + horizon
        if end_bar < len(source):
            row["observation_end_bar"] = end_bar
            row["observation_end_trade_date"] = pd.Timestamp(
                source.iloc[end_bar]["trade_date"]
            ).date().isoformat()
        row["terminal_bar_audit"] = _terminal_audit_payload(
            row,
            frame=source,
            horizon=horizon,
        )
        out.append(row)
    return out


def gate_rows(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten signal-time features plus labelled outcomes for Train/Validation only."""
    rows: list[dict[str, Any]] = []
    for row in records:
        quality = row.get("quality_at_signal") or {}
        outcome = row.get("outcome") or {}
        rows.append(
            {
                "instrument_id": row.get("instrument_id"),
                "signal_trade_date": row.get("signal_trade_date"),
                "pattern_id": row.get("pattern_id"),
                "schema": row.get("schema"),
                "direction": row.get("direction"),
                "source_scale": int(row.get("source_scale", 0)),
                "scale_support_count": len(row.get("signal_scales") or []),
                "confirmation_lag_bars": int(row.get("confirmation_lag_bars", 0)),
                "prz_width_ratio": quality.get("prz_width_ratio"),
                "distance_to_prz_ratio": quality.get("distance_to_prz_ratio"),
                "source_tolerance_used": bool(quality.get("source_tolerance_used", False)),
                "bars_to_first_future_prz_touch": outcome.get("bars_to_first_future_prz_touch"),
                "touch_before_retirement": outcome.get("touch_before_retirement"),
                "bars_to_completion_confirmation": outcome.get("bars_to_completion_confirmation"),
                "completion_before_retirement": outcome.get("completion_before_retirement"),
                "bars_to_frontier_retirement": outcome.get("bars_to_frontier_retirement"),
            }
        )
    return rows


def build_autonomous_quality_report(
    records: Iterable[dict[str, Any]],
    *,
    horizon: int = 60,
    minimum_mature_records: int = 30,
) -> dict[str, Any]:
    """Build a purged Train/Validation report while keeping Holdout outcomes sealed."""
    all_rows = list(records)
    terminal_bar_calibration = build_terminal_bar_calibration(
        all_rows,
        reaction_horizon=DEFAULT_TERMINAL_REACTION_HORIZON,
    )
    terminal_bar_calibration["research_definition"] = SOURCE_TERMINAL_RESEARCH_DEFINITION
    terminal_bar_calibration["prz_basis"] = "source_raw_prz_only_fail_closed_otherwise"
    type_i_early_path = build_type_i_early_path_report(
        all_rows,
        terminal_bar_calibration,
        reaction_horizon=DEFAULT_TERMINAL_REACTION_HORIZON,
    )
    type_i_early_path["research_definition"] = SOURCE_TERMINAL_RESEARCH_DEFINITION
    type_i_early_path_robustness = build_type_i_early_path_robustness_report(
        all_rows,
        terminal_bar_calibration,
        type_i_early_path,
        reaction_horizon=DEFAULT_TERMINAL_REACTION_HORIZON,
    )
    type_i_early_path_robustness["research_definition"] = SOURCE_TERMINAL_RESEARCH_DEFINITION
    type_i_exit_timing = build_type_i_exit_timing_report(
        all_rows,
        terminal_bar_calibration,
        type_i_early_path,
        type_i_early_path_robustness,
        reaction_horizon=DEFAULT_TERMINAL_REACTION_HORIZON,
    )
    type_i_exit_timing["research_definition"] = SOURCE_TERMINAL_RESEARCH_DEFINITION
    mature = mature_forward_records(all_rows, horizon=horizon)
    if len(mature) < minimum_mature_records:
        return {
            "status": "insufficient_mature_records",
            "research_definition": SOURCE_TERMINAL_RESEARCH_DEFINITION,
            "horizon_bars": horizon,
            "mature_records": len(mature),
            "minimum_mature_records": minimum_mature_records,
            "terminal_bar_calibration": terminal_bar_calibration,
            "type_i_early_path": type_i_early_path,
            "type_i_early_path_robustness": type_i_early_path_robustness,
            "type_i_exit_timing": type_i_exit_timing,
            "policy_frozen": False,
            "holdout": {"sealed": True, "outcomes_reported": False},
        }

    boundaries = derive_boundaries(mature)
    splits, purged = assign_purged_split(mature, boundaries)
    if not splits["train"] or not splits["validation"] or not splits["holdout"]:
        return {
            "status": "insufficient_split_coverage",
            "research_definition": SOURCE_TERMINAL_RESEARCH_DEFINITION,
            "horizon_bars": horizon,
            "mature_records": len(mature),
            "terminal_bar_calibration": terminal_bar_calibration,
            "type_i_early_path": type_i_early_path,
            "type_i_early_path_robustness": type_i_early_path_robustness,
            "type_i_exit_timing": type_i_exit_timing,
            "policy_frozen": False,
            "holdout": {"sealed": True, "outcomes_reported": False},
        }

    thresholds = learn_numeric_thresholds(splits["train"])
    threshold_payload = {
        "prz_width_ratio": list(thresholds.prz_width_ratio),
        "distance_to_prz_ratio": list(thresholds.distance_to_prz_ratio),
        "confirmation_lag_bars": list(thresholds.confirmation_lag_bars),
    }
    gates = evaluate_gate_library(
        gate_rows(splits["train"]),
        gate_rows(splits["validation"]),
        thresholds=threshold_payload,
        horizon=horizon,
    )
    manifest = split_manifest(splits, purged=purged, boundaries=boundaries)
    return {
        "status": "research_quality_evidence_holdout_sealed",
        "research_definition": SOURCE_TERMINAL_RESEARCH_DEFINITION,
        "horizon_bars": horizon,
        "mature_records": len(mature),
        "manifest": manifest,
        "train_learned_thresholds": threshold_payload,
        "train_outcome_summary": outcome_summary(splits["train"], horizon=horizon),
        "validation_outcome_summary": outcome_summary(splits["validation"], horizon=horizon),
        "quality_gate": gates,
        "terminal_bar_calibration": terminal_bar_calibration,
        "type_i_early_path": type_i_early_path,
        "type_i_early_path_robustness": type_i_early_path_robustness,
        "type_i_exit_timing": type_i_exit_timing,
        "holdout": {
            "sealed": True,
            "records": len(splits["holdout"]),
            "outcomes_reported": False,
        },
        "policy_frozen": False,
        "anti_leakage": {
            "carney_identity_fitted": False,
            "numeric_thresholds_train_only": True,
            "validation_redefines_gates": False,
            "holdout_outcomes_opened": False,
            "terminal_bar_outcomes_use_independent_purged_split": True,
            "type_i_early_path_reuses_m2_17_boundaries": True,
            "type_i_robustness_reuses_m2_17_boundaries": True,
            "type_i_exit_timing_reuses_m2_17_boundaries": True,
            "source_prz_rebuilt_from_signal_time_geometry": True,
            "legacy_ideal_core_used_as_source_prz": False,
        },
    }
