from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any, Iterable

from htcn.app.decision_narrative import build_decision_narrative


@dataclass(frozen=True, slots=True)
class BaselineAuditFinding:
    code: str
    severity: str
    detail: str

    def as_payload(self) -> dict[str, str]:
        return asdict(self)


NEXT_ROLE_BY_STATE = {
    "approaching_source_prz": "source_prz_entry_edge",
    "entered_source_prz": "source_prz_terminal_side",
    "waiting_terminal": "source_prz_terminal_side",
    "source_terminal_complete": "type_i_38_2_target",
    "t_plus_1": "type_i_38_2_target",
    "type_i_early_reaction": "type_i_38_2_target",
    "type_i_failed": "type_i_38_2_target",
    "type_i_confirmed": "type_i_61_8_target",
    "reaction_only": "type_i_61_8_target",
    "type_ii_retest_forming": "source_prz_terminal_side",
    "type_ii_terminal": "type_ii_reversal_exit_edge",
    "reversal_evidence": None,
    "source_clock_unavailable": None,
    "source_prz_unresolved": None,
    "invalidated": None,
}

PRE_TERMINAL_STATES = {
    "approaching_source_prz",
    "entered_source_prz",
    "waiting_terminal",
}
POST_TERMINAL_STATES = {
    "source_terminal_complete",
    "t_plus_1",
    "type_i_early_reaction",
    "type_i_confirmed",
    "type_i_failed",
    "reaction_only",
    "type_ii_retest_forming",
    "type_ii_terminal",
    "reversal_evidence",
}
PRZ_REQUIRED_STATES = PRE_TERMINAL_STATES | POST_TERMINAL_STATES


def _count(rows: Iterable[dict[str, Any]], field: str) -> dict[str, int]:
    values = Counter(str(row.get(field)) for row in rows)
    return dict(sorted(values.items()))


def _terminal_age_bucket(days: int) -> str:
    if days <= 5:
        return "0_5d"
    if days <= 20:
        return "6_20d"
    if days <= 60:
        return "21_60d"
    if days <= 180:
        return "61_180d"
    return "over_180d"


def audit_t0_baseline(
    rows: Iterable[dict[str, Any]],
    *,
    snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    materialized = [dict(row) for row in rows]
    findings: list[BaselineAuditFinding] = []

    def finding(code: str, severity: str, detail: str) -> None:
        findings.append(BaselineAuditFinding(code, severity, detail))

    if not materialized:
        finding("journal_empty", "blocker", "Lifecycle journal contains no rows.")
        return {
            "schema_version": 1,
            "status": "not_ready",
            "blocker_count": 1,
            "warning_count": 0,
            "blockers": [item.as_payload() for item in findings],
            "warnings": [],
            "transition_ready": False,
            "prospective_outcome_ready": False,
        }

    dates = sorted({str(row.get("as_of_trade_date") or "") for row in materialized})
    heads = sorted({str(row.get("code_head") or "") for row in materialized})
    keys = [str(row.get("candidate_key") or "") for row in materialized]
    baseline_date = dates[0] if dates else None

    if "" in dates or len(dates) != 1:
        finding(
            "baseline_date_not_single",
            "blocker",
            f"T0 audit requires exactly one as-of date, got {dates}.",
        )
    if "" in heads or len(heads) != 1:
        finding(
            "baseline_code_head_not_single",
            "blocker",
            f"T0 audit requires exactly one code head, got {heads}.",
        )
    if "" in keys or len(keys) != len(set(keys)):
        finding(
            "candidate_key_not_unique",
            "blocker",
            "T0 contains missing or duplicate candidate keys.",
        )

    action_mismatches: list[str] = []
    role_mismatches: list[str] = []
    prz_errors: list[str] = []
    terminal_errors: list[str] = []
    boundary_errors: list[str] = []
    terminal_age_counts: Counter[str] = Counter()
    terminal_age_days: list[int] = []

    for row in materialized:
        key = str(row.get("candidate_key") or "")
        state = str(row.get("source_lifecycle_state") or "")
        action = str(row.get("action_state") or "")
        expected_action = build_decision_narrative(
            source_lifecycle={"state": state},
            context_integrity=None,
        ).action_state
        if action != expected_action:
            action_mismatches.append(key)

        expected_role = NEXT_ROLE_BY_STATE.get(state)
        if row.get("next_key_price_role") != expected_role:
            role_mismatches.append(key)

        low = row.get("source_prz_low")
        high = row.get("source_prz_high")
        if low is not None and high is not None and float(low) > float(high):
            prz_errors.append(key)
        if state in PRZ_REQUIRED_STATES and (low is None or high is None):
            prz_errors.append(key)
        if state == "source_prz_unresolved" and (low is not None or high is not None):
            prz_errors.append(key)

        terminal_raw = row.get("source_terminal_trade_date")
        if terminal_raw:
            try:
                terminal_date = date.fromisoformat(str(terminal_raw))
                as_of_date = date.fromisoformat(str(row.get("as_of_trade_date")))
            except ValueError:
                terminal_errors.append(key)
            else:
                if terminal_date > as_of_date:
                    terminal_errors.append(key)
                days = (as_of_date - terminal_date).days
                terminal_age_days.append(days)
                terminal_age_counts[_terminal_age_bucket(days)] += 1
                if state in PRE_TERMINAL_STATES or state in {
                    "source_clock_unavailable",
                    "source_prz_unresolved",
                }:
                    terminal_errors.append(key)
        elif state in POST_TERMINAL_STATES:
            terminal_errors.append(key)

        if str(row.get("pattern_id")) == "five_zero":
            boundary_errors.append(key)
        if str(row.get("pattern_id")) == "alternate_bat" and state not in {
            "source_prz_unresolved",
            "source_clock_unavailable",
        }:
            boundary_errors.append(key)
        if row.get("alpha_inference_allowed") is not False:
            boundary_errors.append(key)
        if row.get("is_trade_instruction") is not False:
            boundary_errors.append(key)

    if action_mismatches:
        finding(
            "action_state_mismatch",
            "blocker",
            f"{len(action_mismatches)} row(s) disagree with frozen lifecycle-to-action mapping.",
        )
    if role_mismatches:
        finding(
            "next_key_role_mismatch",
            "blocker",
            f"{len(role_mismatches)} row(s) have next-key role inconsistent with lifecycle.",
        )
    if prz_errors:
        finding(
            "source_prz_contract_error",
            "blocker",
            f"{len(set(prz_errors))} row(s) violate Source PRZ field contract.",
        )
    if terminal_errors:
        finding(
            "source_terminal_contract_error",
            "blocker",
            f"{len(set(terminal_errors))} row(s) violate Source Terminal date contract.",
        )
    if boundary_errors:
        finding(
            "source_fidelity_boundary_error",
            "blocker",
            f"{len(set(boundary_errors))} row(s) violate frozen M3/M4 boundaries.",
        )

    pattern_counts = Counter(str(row.get("pattern_id")) for row in materialized)
    schema_counts = Counter(str(row.get("schema")) for row in materialized)
    direction_counts = Counter(str(row.get("direction")) for row in materialized)
    scale_counts = Counter(str(row.get("scale")) for row in materialized)
    lifecycle_counts = Counter(str(row.get("source_lifecycle_state")) for row in materialized)
    action_counts = Counter(str(row.get("action_state")) for row in materialized)
    execution_counts = Counter(str(row.get("execution_context_gate")) for row in materialized)
    context_counts = Counter(str(row.get("context_integrity_summary")) for row in materialized)
    instrument_counts = Counter(str(row.get("instrument_id")) for row in materialized)

    largest_pattern, largest_pattern_count = pattern_counts.most_common(1)[0]
    largest_pattern_share = largest_pattern_count / len(materialized)
    if largest_pattern_share >= 0.50:
        finding(
            "pattern_concentration",
            "warning",
            f"{largest_pattern} contributes {largest_pattern_count}/{len(materialized)} "
            f"({largest_pattern_share:.1%}) of T0 candidates; aggregate counts are not shape-balanced.",
        )
    if execution_counts.get("execution_unresolved", 0) == len(materialized):
        finding(
            "execution_context_all_unresolved",
            "warning",
            "Every T0 candidate has execution_unresolved; lifecycle is auditable but execution feasibility is not fully resolved.",
        )
    if context_counts.get("issues_present", 0) == len(materialized):
        finding(
            "context_integrity_all_issues_present",
            "warning",
            "Every T0 candidate carries context_integrity=issues_present; context may not be used as clean comparative evidence.",
        )

    alternate_bat_count = pattern_counts.get("alternate_bat", 0)
    if alternate_bat_count:
        finding(
            "alternate_bat_fail_closed_present",
            "warning",
            f"{alternate_bat_count} Alternate Bat row(s) are retained only as fail-closed observability evidence.",
        )
    terminal_over_20d = sum(
        count
        for bucket, count in terminal_age_counts.items()
        if bucket in {"21_60d", "61_180d", "over_180d"}
    )
    if terminal_age_days:
        finding(
            "mature_baseline_inventory",
            "warning",
            (
                f"{len(terminal_age_days)} T0 row(s) already have Source Terminal history; "
                f"{terminal_over_20d} are older than 20 calendar days and the oldest is "
                f"{max(terminal_age_days)} days. They are baseline inventory, not from-formation prospective evidence."
            ),
        )

    source_gap_count = (
        lifecycle_counts.get("source_clock_unavailable", 0)
        + lifecycle_counts.get("source_prz_unresolved", 0)
    )
    if source_gap_count:
        finding(
            "source_observability_gap",
            "warning",
            f"{source_gap_count} row(s) lack a usable Source clock or resolved Source PRZ and remain evidence-insufficient.",
        )

    snapshot_checks: dict[str, Any] = {"provided": snapshot is not None}
    if snapshot is not None:
        snapshot_checks["status"] = snapshot.get("status")
        snapshot_checks["candidate_count"] = snapshot.get("candidate_count")
        snapshot_checks["successful_instruments"] = snapshot.get("successful_instruments")
        snapshot_checks["failed_instruments"] = snapshot.get("failed_instruments")
        if snapshot.get("status") != "pass":
            finding("snapshot_not_pass", "blocker", "T0 snapshot status is not pass.")
        if int(snapshot.get("candidate_count") or -1) != len(materialized):
            finding(
                "snapshot_candidate_count_mismatch",
                "blocker",
                "Snapshot candidate_count does not match journal row count.",
            )
        if int(snapshot.get("failed_instruments") or 0) != 0:
            finding(
                "snapshot_instrument_failure",
                "blocker",
                "Snapshot contains failed instrument analyses.",
            )
        instrument_count = int(snapshot.get("instrument_count") or 0)
        successful_count = int(snapshot.get("successful_instruments") or 0)
        if instrument_count <= 0 or successful_count != instrument_count:
            finding(
                "snapshot_instrument_coverage_mismatch",
                "blocker",
                f"Snapshot successful/instrument count mismatch: {successful_count}/{instrument_count}.",
            )
        if dict(snapshot.get("source_lifecycle_states") or {}) != dict(sorted(lifecycle_counts.items())):
            finding(
                "snapshot_lifecycle_count_mismatch",
                "blocker",
                "Snapshot source_lifecycle_states do not match journal counts.",
            )
        if dict(snapshot.get("action_states") or {}) != dict(sorted(action_counts.items())):
            finding(
                "snapshot_action_count_mismatch",
                "blocker",
                "Snapshot action_states do not match journal counts.",
            )
        if dict(snapshot.get("schemas") or {}) != dict(sorted(schema_counts.items())):
            finding(
                "snapshot_schema_count_mismatch",
                "blocker",
                "Snapshot schemas do not match journal counts.",
            )
        if snapshot.get("worktree_clean") is not True:
            finding(
                "snapshot_dirty_worktree",
                "blocker",
                "Snapshot was not captured from a clean worktree.",
            )
        if snapshot.get("alpha_inference_allowed") is not False:
            finding(
                "snapshot_alpha_boundary_mismatch",
                "blocker",
                "Snapshot unexpectedly permits alpha inference.",
            )
        if snapshot.get("is_trade_instruction") is not False:
            finding(
                "snapshot_trade_instruction_boundary_mismatch",
                "blocker",
                "Snapshot unexpectedly declares trade-instruction semantics.",
            )
        snapshot_head = snapshot.get("code_head")
        if heads and snapshot_head != heads[0]:
            finding(
                "snapshot_head_mismatch",
                "blocker",
                "Snapshot code_head does not match journal code_head.",
            )
        expected = snapshot.get("expected_trade_date")
        if baseline_date and expected != baseline_date:
            finding(
                "snapshot_trade_date_mismatch",
                "blocker",
                "Snapshot expected_trade_date does not match journal as-of date.",
            )

    blockers = [item for item in findings if item.severity == "blocker"]
    warnings = [item for item in findings if item.severity == "warning"]
    transition_ready = len(blockers) == 0 and len(dates) == 1

    return {
        "schema_version": 1,
        "status": "pass_with_warnings" if not blockers and warnings else "pass" if not blockers else "not_ready",
        "baseline_trade_date": baseline_date,
        "journal_row_count": len(materialized),
        "unique_candidate_count": len(set(keys)),
        "candidate_bearing_instrument_count": len(instrument_counts),
        "zero_candidate_instrument_count": (
            max(0, int(snapshot.get("instrument_count") or 0) - len(instrument_counts))
            if snapshot is not None
            else None
        ),
        "pattern_counts": dict(sorted(pattern_counts.items())),
        "schema_counts": dict(sorted(schema_counts.items())),
        "direction_counts": dict(sorted(direction_counts.items())),
        "scale_counts": dict(sorted(scale_counts.items(), key=lambda item: item[0])),
        "lifecycle_counts": dict(sorted(lifecycle_counts.items())),
        "action_counts": dict(sorted(action_counts.items())),
        "execution_gate_counts": dict(sorted(execution_counts.items())),
        "context_integrity_counts": dict(sorted(context_counts.items())),
        "top_instruments": [
            {"instrument_id": key, "candidate_count": value}
            for key, value in instrument_counts.most_common(10)
        ],
        "source_terminal_observed_count": len(terminal_age_days),
        "source_terminal_age_buckets": dict(sorted(terminal_age_counts.items())),
        "oldest_source_terminal_age_days": max(terminal_age_days) if terminal_age_days else None,
        "pre_terminal_candidate_count": sum(lifecycle_counts.get(state, 0) for state in PRE_TERMINAL_STATES),
        "post_terminal_candidate_count": sum(lifecycle_counts.get(state, 0) for state in POST_TERMINAL_STATES),
        "source_clock_unavailable_count": lifecycle_counts.get("source_clock_unavailable", 0),
        "source_prz_unresolved_count": lifecycle_counts.get("source_prz_unresolved", 0),
        "alternate_bat_count": alternate_bat_count,
        "snapshot_checks": snapshot_checks,
        "blocker_count": len(blockers),
        "warning_count": len(warnings),
        "blockers": [item.as_payload() for item in blockers],
        "warnings": [item.as_payload() for item in warnings],
        "transition_ready": transition_ready,
        "prospective_outcome_ready": False,
        "prospective_outcome_reason": (
            "T0 is baseline inventory; outcome analysis requires post-T0 eligible candidates and future observations."
        ),
        "interpretation": {
            "uses_score": False,
            "alpha_inference_allowed": False,
            "is_trade_instruction": False,
            "baseline_is_outcome_cohort": False,
        },
    }
