from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any


def _as_dicts(items: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    if items is None:
        return []
    return [dict(item) for item in items]


def build_m7_accumulation_status(
    *,
    evidence_health: Mapping[str, Any],
    observation_report: Mapping[str, Any],
    outcome_snapshots: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    health = dict(evidence_health)
    observations = dict(observation_report)
    snapshots = _as_dicts(outcome_snapshots)

    blocker_count = int(health.get("blocker_count") or 0)
    committed_capture_count = int(health.get("committed_capture_count") or 0)
    committed_dates = [
        str(value) for value in (health.get("committed_capture_dates") or [])
    ]
    candidate_summaries = [
        dict(item) for item in (observations.get("candidate_summaries") or [])
    ]
    prospective_candidate_count = int(
        observations.get("prospective_candidate_count") or 0
    )
    observation_count = int(observations.get("observation_count") or 0)

    if blocker_count:
        status = "blocked"
        next_action = (
            "Resolve authoritative evidence-chain blockers before another M7 evidence append."
        )
    elif committed_capture_count == 0:
        status = "waiting_first_future_capture"
        next_action = (
            "Run the M7 one-click entry after the next closed A-share session on current canonical main."
        )
    elif prospective_candidate_count == 0:
        status = "accumulating_no_outcome_cohort"
        next_action = (
            "Continue frozen daily prospective capture; do not relax enrollment rules to create a cohort."
        )
    else:
        status = "accumulating"
        next_action = (
            "Continue frozen daily prospective capture and outcome follow-up; statistical conclusions remain gated."
        )

    latest_snapshot: dict[str, Any] | None = None
    if snapshots:
        snapshots.sort(key=lambda item: str(item.get("outcome_as_of_trade_date") or ""))
        latest_snapshot = snapshots[-1]

    latest_results = (
        []
        if latest_snapshot is None
        else [dict(item) for item in (latest_snapshot.get("results") or [])]
    )
    latest_outcome_status_counts = dict(
        sorted(
            Counter(
                str(item.get("status") or "unknown")
                for item in latest_results
            ).items()
        )
    )
    path_depths = [
        int(item.get("market_path_traded_bar_count") or 0)
        for item in latest_results
    ]

    source_terminal_observed_count = sum(
        item.get("first_source_terminal_trade_date") is not None
        for item in candidate_summaries
    )
    scanner_absent_ever_count = sum(
        int(item.get("absent_snapshot_count") or 0) > 0
        for item in candidate_summaries
    )
    basis_drift_candidate_count = sum(
        int(item.get("price_basis_drift_snapshot_count") or 0) > 0
        for item in candidate_summaries
    )
    snapshot_depths = [
        int(item.get("captured_snapshot_count") or 0)
        for item in candidate_summaries
    ]

    return {
        "schema_version": 1,
        "status": status,
        "evidence_health_status": health.get("status"),
        "blocker_count": blocker_count,
        "committed_capture_count": committed_capture_count,
        "committed_capture_dates": committed_dates,
        "latest_committed_capture_date": health.get("latest_committed_capture_date"),
        "zero_candidate_capture_count": len(
            health.get("zero_candidate_capture_dates") or []
        ),
        "prospective_candidate_count": prospective_candidate_count,
        "observation_count": observation_count,
        "scanner_absent_ever_candidate_count": scanner_absent_ever_count,
        "source_terminal_observed_candidate_count": source_terminal_observed_count,
        "price_basis_drift_candidate_count": basis_drift_candidate_count,
        "max_captured_snapshot_depth": max(snapshot_depths, default=0),
        "outcome_snapshot_count": len(snapshots),
        "latest_outcome_as_of_trade_date": (
            None
            if latest_snapshot is None
            else latest_snapshot.get("outcome_as_of_trade_date")
        ),
        "latest_outcome_result_count": len(latest_results),
        "latest_outcome_status_counts": latest_outcome_status_counts,
        "latest_market_path_traded_bar_depth": {
            "min": min(path_depths, default=0),
            "max": max(path_depths, default=0),
        },
        "issue_gate": "ISSUE-0066",
        "inference_boundary": {
            "statistical_inference_allowed": False,
            "alpha_inference_allowed": False,
            "win_rate_inference_allowed": False,
            "profitability_inference_allowed": False,
            "is_trade_instruction": False,
        },
        "next_action": next_action,
    }
