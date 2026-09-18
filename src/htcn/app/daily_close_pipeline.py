from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable


@dataclass(frozen=True, slots=True)
class DailyCloseStep:
    name: str
    command: tuple[str, ...]
    log_name: str


@dataclass(frozen=True, slots=True)
class DailyCloseStepResult:
    name: str
    status: str
    exit_code: int | None
    reason: str | None = None

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


STEP_SPECS: dict[str, DailyCloseStep] = {
    "methodology_guard": DailyCloseStep(
        "methodology_guard",
        ("scripts/m4_methodology_freeze_guard.py",),
        "m5-daily-methodology-guard.log",
    ),
    "outcome_guard": DailyCloseStep(
        "outcome_guard",
        ("scripts/m4_outcome_engine_freeze_guard.py",),
        "m5-daily-outcome-guard.log",
    ),
    "m1_update": DailyCloseStep(
        "m1_update",
        ("scripts/m1_daily_update.py", "--limit", "0", "--sleep", "0.05"),
        "m5-daily-m1-update.log",
    ),
    "qfq_readiness": DailyCloseStep(
        "qfq_readiness",
        ("scripts/m4_prepare_qfq_universe.py", "--retries", "1", "--sleep", "0.05"),
        "m5-daily-qfq-readiness.log",
    ),
    "m5_operator_cache": DailyCloseStep(
        "m5_operator_cache",
        ("scripts/m5_precompute_operator_snapshot.py", "--force"),
        "m5-daily-operator-cache.log",
    ),
    "m4_capture": DailyCloseStep(
        "m4_capture",
        ("scripts/m4_capture_lifecycle_snapshot.py",),
        "m5-daily-m4-capture.log",
    ),
    "m4_health": DailyCloseStep(
        "m4_health",
        ("scripts/m4_evidence_health.py",),
        "m5-daily-m4-health.log",
    ),
    "m4_transition": DailyCloseStep(
        "m4_transition",
        ("scripts/m4_build_transition_report.py",),
        "m5-daily-m4-transition.log",
    ),
    "m4_observation": DailyCloseStep(
        "m4_observation",
        ("scripts/m4_build_observation_report.py",),
        "m5-daily-m4-observation.log",
    ),
    "m4_outcome": DailyCloseStep(
        "m4_outcome",
        ("scripts/m4_build_outcome_report.py",),
        "m5-daily-m4-outcome.log",
    ),
    "m4_bundle": DailyCloseStep(
        "m4_bundle",
        ("scripts/m4_export_evidence_bundle.py",),
        "m5-daily-m4-bundle.log",
    ),
}


RunStep = Callable[[DailyCloseStep], int]


def _ran(name: str, code: int) -> DailyCloseStepResult:
    return DailyCloseStepResult(
        name=name,
        status="passed" if code == 0 else "failed",
        exit_code=int(code),
    )


def _skipped(name: str, reason: str) -> DailyCloseStepResult:
    return DailyCloseStepResult(
        name=name,
        status="skipped",
        exit_code=None,
        reason=reason,
    )


def execute_daily_close_steps(run_step: RunStep) -> dict[str, object]:
    """Execute M1 -> M5 product -> M4 evidence with independent failure domains.

    The M4 and M5 branches share the frozen source methodology but do not share
    evidence ownership. M5 cache failure must not suppress an otherwise valid
    M4 capture, and M4 capture failure must not suppress an otherwise valid M5
    cache after M1/QFQ readiness.
    """
    results: dict[str, DailyCloseStepResult] = {}

    for guard_name in ("methodology_guard", "outcome_guard"):
        code = int(run_step(STEP_SPECS[guard_name]))
        results[guard_name] = _ran(guard_name, code)
        if code != 0:
            for name in STEP_SPECS:
                if name not in results:
                    results[name] = _skipped(
                        name,
                        f"preflight_guard_failed:{guard_name}",
                    )
            return build_daily_close_summary(results, hard_preflight_failure=True)

    m1_code = int(run_step(STEP_SPECS["m1_update"]))
    results["m1_update"] = _ran("m1_update", m1_code)

    if m1_code == 0:
        qfq_code = int(run_step(STEP_SPECS["qfq_readiness"]))
        results["qfq_readiness"] = _ran("qfq_readiness", qfq_code)
    else:
        qfq_code = 1
        results["qfq_readiness"] = _skipped(
            "qfq_readiness",
            "m1_update_failed",
        )

    data_ready = m1_code == 0 and qfq_code == 0

    if data_ready:
        m5_code = int(run_step(STEP_SPECS["m5_operator_cache"]))
        results["m5_operator_cache"] = _ran(
            "m5_operator_cache",
            m5_code,
        )
        capture_code = int(run_step(STEP_SPECS["m4_capture"]))
        results["m4_capture"] = _ran("m4_capture", capture_code)
    else:
        results["m5_operator_cache"] = _skipped(
            "m5_operator_cache",
            "m1_or_qfq_not_ready",
        )
        results["m4_capture"] = _skipped(
            "m4_capture",
            "m1_or_qfq_not_ready",
        )
        capture_code = 1

    # Health and derived historical reports remain safe to run even when no
    # new capture was appended. They inspect the existing authoritative chain.
    health_code = int(run_step(STEP_SPECS["m4_health"]))
    results["m4_health"] = _ran("m4_health", health_code)

    transition_code = int(run_step(STEP_SPECS["m4_transition"]))
    results["m4_transition"] = _ran(
        "m4_transition",
        transition_code,
    )

    observation_code = int(run_step(STEP_SPECS["m4_observation"]))
    results["m4_observation"] = _ran(
        "m4_observation",
        observation_code,
    )

    if (
        data_ready
        and capture_code == 0
        and health_code == 0
        and observation_code == 0
    ):
        outcome_code = int(run_step(STEP_SPECS["m4_outcome"]))
        results["m4_outcome"] = _ran("m4_outcome", outcome_code)
    else:
        results["m4_outcome"] = _skipped(
            "m4_outcome",
            "capture_health_or_observation_not_ready",
        )

    bundle_code = int(run_step(STEP_SPECS["m4_bundle"]))
    results["m4_bundle"] = _ran("m4_bundle", bundle_code)

    return build_daily_close_summary(results)


def build_daily_close_summary(
    results: dict[str, DailyCloseStepResult],
    *,
    hard_preflight_failure: bool = False,
) -> dict[str, object]:
    def passed(name: str) -> bool:
        item = results.get(name)
        return bool(
            item is not None
            and item.status == "passed"
            and item.exit_code == 0
        )

    data_ready = passed("m1_update") and passed("qfq_readiness")
    product_ready = data_ready and passed("m5_operator_cache")
    research_ready = (
        data_ready
        and passed("m4_capture")
        and passed("m4_health")
        and passed("m4_transition")
        and passed("m4_observation")
        and passed("m4_outcome")
        and passed("m4_bundle")
    )

    if hard_preflight_failure:
        overall = "failed_preflight"
        exit_code = 2
    elif product_ready and research_ready:
        overall = "passed"
        exit_code = 0
    elif data_ready and (product_ready or research_ready):
        overall = "partial"
        exit_code = 1
    else:
        overall = "failed"
        exit_code = 1

    return {
        "schema_version": 1,
        "overall_status": overall,
        "exit_code": exit_code,
        "data_ready": data_ready,
        "m5_product_ready": product_ready,
        "m4_research_ready": research_ready,
        "steps": {
            name: result.as_payload()
            for name, result in results.items()
        },
        "boundaries": {
            "m5_cache_is_authoritative_evidence": False,
            "m5_cache_writes_m4_evidence": False,
            "m4_evidence_owned_by_authoritative_capture_chain": True,
            "branch_name_owns_methodology_identity": False,
            "freeze_guards_own_cross_branch_capture_permission": True,
        },
    }
