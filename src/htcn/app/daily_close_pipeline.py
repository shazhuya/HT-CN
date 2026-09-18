from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable


@dataclass(frozen=True, slots=True)
class DailyCloseStep:
    name: str
    command: tuple[str, ...]
    log_name: str
    lane: str


@dataclass(frozen=True, slots=True)
class DailyCloseStepResult:
    name: str
    lane: str
    status: str
    exit_code: int | None
    reason: str | None = None

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


STEP_SPECS: dict[str, DailyCloseStep] = {
    "m1_update": DailyCloseStep(
        "m1_update",
        ("scripts/m1_daily_update.py", "--limit", "0", "--sleep", "0.05"),
        "m5-daily-m1-update.log",
        "shared_data",
    ),
    "context_sync": DailyCloseStep(
        "context_sync",
        ("scripts/m3_sync_all_contexts.py",),
        "m5-daily-context-sync.log",
        "m5_product",
    ),
    "m5_operator_cache": DailyCloseStep(
        "m5_operator_cache",
        ("scripts/m5_precompute_operator_snapshot.py", "--force"),
        "m5-daily-operator-cache.log",
        "m5_product",
    ),
    "m5_operator_cache_finalize": DailyCloseStep(
        "m5_operator_cache_finalize",
        ("scripts/m5_precompute_operator_snapshot.py",),
        "m5-daily-operator-cache-finalize.log",
        "m5_product",
    ),
    "m5_operator_history": DailyCloseStep(
        "m5_operator_history",
        ("scripts/m5_record_operator_history.py",),
        "m5-daily-operator-history.log",
        "m5_product_history",
    ),
    "m4_methodology_guard": DailyCloseStep(
        "m4_methodology_guard",
        ("scripts/m4_methodology_freeze_guard.py",),
        "m5-daily-m4-methodology-guard.log",
        "m4_research",
    ),
    "m4_outcome_guard": DailyCloseStep(
        "m4_outcome_guard",
        ("scripts/m4_outcome_engine_freeze_guard.py",),
        "m5-daily-m4-outcome-guard.log",
        "m4_research",
    ),
    "m4_qfq_readiness": DailyCloseStep(
        "m4_qfq_readiness",
        ("scripts/m4_prepare_qfq_universe.py", "--retries", "1", "--sleep", "0.05"),
        "m5-daily-m4-qfq-readiness.log",
        "m4_research",
    ),
    "m4_capture": DailyCloseStep(
        "m4_capture",
        ("scripts/m4_capture_lifecycle_snapshot.py",),
        "m5-daily-m4-capture.log",
        "m4_research",
    ),
    "m4_health": DailyCloseStep(
        "m4_health",
        ("scripts/m4_evidence_health.py",),
        "m5-daily-m4-health.log",
        "m4_research",
    ),
    "m4_transition": DailyCloseStep(
        "m4_transition",
        ("scripts/m4_build_transition_report.py",),
        "m5-daily-m4-transition.log",
        "m4_research",
    ),
    "m4_observation": DailyCloseStep(
        "m4_observation",
        ("scripts/m4_build_observation_report.py",),
        "m5-daily-m4-observation.log",
        "m4_research",
    ),
    "m4_outcome": DailyCloseStep(
        "m4_outcome",
        ("scripts/m4_build_outcome_report.py",),
        "m5-daily-m4-outcome.log",
        "m4_research",
    ),
    "m4_bundle": DailyCloseStep(
        "m4_bundle",
        ("scripts/m4_export_evidence_bundle.py",),
        "m5-daily-m4-bundle.log",
        "m4_research",
    ),
}


RunStep = Callable[[DailyCloseStep], int]


def _ran(step: DailyCloseStep, code: int) -> DailyCloseStepResult:
    return DailyCloseStepResult(
        name=step.name,
        lane=step.lane,
        status="passed" if code == 0 else "failed",
        exit_code=int(code),
    )


def _skipped(name: str, reason: str) -> DailyCloseStepResult:
    step = STEP_SPECS[name]
    return DailyCloseStepResult(
        name=name,
        lane=step.lane,
        status="skipped",
        exit_code=None,
        reason=reason,
    )


def execute_daily_close_steps(
    run_step: RunStep,
    *,
    research_preflight_ready: bool = True,
    research_preflight_reason: str | None = None,
) -> dict[str, object]:
    """Run M5 early, isolate M4, then revalidate final M5 cache identity.

    Shared M1 freshness may gate both lanes. M4 methodology/QFQ requirements
    never gate M5 Operator Queue readiness. A final non-force product cache
    validation closes any input-identity change caused by the later M4 QFQ
    provisioning step.
    """
    results: dict[str, DailyCloseStepResult] = {}

    m1_step = STEP_SPECS["m1_update"]
    m1_code = int(run_step(m1_step))
    results["m1_update"] = _ran(m1_step, m1_code)
    market_data_ready = m1_code == 0

    if market_data_ready:
        context_step = STEP_SPECS["context_sync"]
        context_code = int(run_step(context_step))
        results["context_sync"] = _ran(context_step, context_code)

        product_step = STEP_SPECS["m5_operator_cache"]
        product_code = int(run_step(product_step))
        results["m5_operator_cache"] = _ran(
            product_step,
            product_code,
        )
    else:
        context_code = 1
        product_code = 1
        results["context_sync"] = _skipped(
            "context_sync",
            "m1_update_failed",
        )
        results["m5_operator_cache"] = _skipped(
            "m5_operator_cache",
            "m1_update_failed",
        )

    research_names = (
        "m4_methodology_guard",
        "m4_outcome_guard",
        "m4_qfq_readiness",
        "m4_capture",
        "m4_health",
        "m4_transition",
        "m4_observation",
        "m4_outcome",
        "m4_bundle",
    )

    if not research_preflight_ready:
        reason = (
            research_preflight_reason
            or "m4_research_preflight_not_ready"
        )
        for name in research_names:
            results[name] = _skipped(name, reason)
    else:
        methodology_step = STEP_SPECS["m4_methodology_guard"]
        methodology_code = int(run_step(methodology_step))
        results["m4_methodology_guard"] = _ran(
            methodology_step,
            methodology_code,
        )

        outcome_guard_step = STEP_SPECS["m4_outcome_guard"]
        outcome_guard_code = int(run_step(outcome_guard_step))
        results["m4_outcome_guard"] = _ran(
            outcome_guard_step,
            outcome_guard_code,
        )
        guards_ready = (
            methodology_code == 0
            and outcome_guard_code == 0
        )

        if guards_ready and market_data_ready:
            qfq_step = STEP_SPECS["m4_qfq_readiness"]
            qfq_code = int(run_step(qfq_step))
            results["m4_qfq_readiness"] = _ran(
                qfq_step,
                qfq_code,
            )
        else:
            qfq_code = 1
            results["m4_qfq_readiness"] = _skipped(
                "m4_qfq_readiness",
                (
                    "m4_guard_failed"
                    if not guards_ready
                    else "m1_update_failed"
                ),
            )

        if guards_ready and market_data_ready and qfq_code == 0:
            capture_step = STEP_SPECS["m4_capture"]
            capture_code = int(run_step(capture_step))
            results["m4_capture"] = _ran(
                capture_step,
                capture_code,
            )
        else:
            capture_code = 1
            results["m4_capture"] = _skipped(
                "m4_capture",
                (
                    "m4_qfq_not_ready"
                    if guards_ready and market_data_ready
                    else "m4_guard_or_market_data_not_ready"
                ),
            )

        if guards_ready:
            for name in (
                "m4_health",
                "m4_transition",
                "m4_observation",
            ):
                step = STEP_SPECS[name]
                code = int(run_step(step))
                results[name] = _ran(step, code)
        else:
            for name in (
                "m4_health",
                "m4_transition",
                "m4_observation",
            ):
                results[name] = _skipped(
                    name,
                    "m4_guard_failed",
                )

        health_ready = (
            results["m4_health"].status == "passed"
            and results["m4_health"].exit_code == 0
        )
        observation_ready = (
            results["m4_observation"].status == "passed"
            and results["m4_observation"].exit_code == 0
        )

        if (
            capture_code == 0
            and health_ready
            and observation_ready
        ):
            step = STEP_SPECS["m4_outcome"]
            code = int(run_step(step))
            results["m4_outcome"] = _ran(step, code)
        else:
            results["m4_outcome"] = _skipped(
                "m4_outcome",
                "capture_health_or_observation_not_ready",
            )

        if guards_ready:
            step = STEP_SPECS["m4_bundle"]
            code = int(run_step(step))
            results["m4_bundle"] = _ran(step, code)
        else:
            results["m4_bundle"] = _skipped(
                "m4_bundle",
                "m4_guard_failed",
            )

    # M4 QFQ provisioning can change adjustment/qfq, which is part of the
    # Phase-7 M5 data identity. Revalidate product cache *after* the research
    # lane. This call is non-force: unchanged input becomes a cheap cache hit;
    # changed input causes exactly one current-identity rebuild.
    if market_data_ready:
        final_step = STEP_SPECS["m5_operator_cache_finalize"]
        final_code = int(run_step(final_step))
        results["m5_operator_cache_finalize"] = _ran(
            final_step,
            final_code,
        )
    else:
        final_code = 1
        results["m5_operator_cache_finalize"] = _skipped(
            "m5_operator_cache_finalize",
            "m1_update_failed",
        )

    # Phase 11 records only the final, post-research product snapshot.
    # History is product observation, not a readiness prerequisite: a history
    # write/query failure must not rewrite an otherwise valid M5 product.
    if market_data_ready and final_code == 0:
        history_step = STEP_SPECS["m5_operator_history"]
        history_code = int(run_step(history_step))
        results["m5_operator_history"] = _ran(
            history_step,
            history_code,
        )
    else:
        results["m5_operator_history"] = _skipped(
            "m5_operator_history",
            (
                "m5_final_product_not_ready"
                if market_data_ready
                else "m1_update_failed"
            ),
        )

    return build_daily_close_summary(results)


def build_daily_close_summary(
    results: dict[str, DailyCloseStepResult],
) -> dict[str, object]:
    def passed(name: str) -> bool:
        item = results.get(name)
        return bool(
            item is not None
            and item.status == "passed"
            and item.exit_code == 0
        )

    market_data_ready = passed("m1_update")
    m5_context_refresh_ready = passed("context_sync")
    m5_initial_product_ready = (
        market_data_ready and passed("m5_operator_cache")
    )
    m5_product_ready = (
        market_data_ready
        and passed("m5_operator_cache_finalize")
    )
    m5_history_ready = (
        m5_product_ready
        and passed("m5_operator_history")
    )
    m4_research_ready = (
        market_data_ready
        and passed("m4_methodology_guard")
        and passed("m4_outcome_guard")
        and passed("m4_qfq_readiness")
        and passed("m4_capture")
        and passed("m4_health")
        and passed("m4_transition")
        and passed("m4_observation")
        and passed("m4_outcome")
        and passed("m4_bundle")
    )

    if m5_product_ready:
        exit_code = 0
        if m4_research_ready and m5_context_refresh_ready:
            overall = "passed"
        elif m4_research_ready:
            overall = "product_ready_context_degraded"
        elif m5_context_refresh_ready:
            overall = "product_ready_research_degraded"
        else:
            overall = "product_ready_context_and_research_degraded"
    elif m4_research_ready:
        overall = "product_failed_research_ready"
        exit_code = 2
    else:
        overall = "failed"
        exit_code = 2

    return {
        "schema_version": 2,
        "overall_status": overall,
        "exit_code": exit_code,
        "market_data_ready": market_data_ready,
        "m5_product_ready": m5_product_ready,
        "m5_initial_product_ready": m5_initial_product_ready,
        "m5_final_cache_revalidated_after_research_lane": True,
        "m5_context_refresh_ready": m5_context_refresh_ready,
        "m5_context_degraded_but_product_allowed": (
            m5_product_ready and not m5_context_refresh_ready
        ),
        "m5_history_ready": m5_history_ready,
        "m5_history_degraded_but_product_allowed": (
            m5_product_ready and not m5_history_ready
        ),
        "m4_research_ready": m4_research_ready,
        "research_degraded_does_not_block_product_exit": True,
        "steps": {
            name: result.as_payload()
            for name, result in results.items()
        },
        "boundaries": {
            "m5_product_requires_m4_qfq": False,
            "m5_product_requires_m4_guards": False,
            "m5_product_requires_context_sync_success": False,
            "m5_final_cache_revalidation_after_m4": True,
            "m5_history_runs_only_after_final_cache": True,
            "m5_history_required_for_product_ready": False,
            "m5_history_is_authoritative_evidence": False,
            "m5_history_writes_m4_evidence": False,
            "m5_history_uses_historical_outcome_for_ranking": False,
            "m5_cache_is_authoritative_evidence": False,
            "m5_cache_writes_m4_evidence": False,
            "m4_evidence_owned_by_authoritative_capture_chain": True,
            "shared_m1_freshness_is_cross_lane_prerequisite": True,
        },
    }
