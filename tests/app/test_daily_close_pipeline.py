from __future__ import annotations

from htcn.app.daily_close_pipeline import (
    STEP_SPECS,
    execute_daily_close_steps,
)


def _runner(codes: dict[str, int], seen: list[str]):
    def run(step):
        seen.append(step.name)
        return codes.get(step.name, 0)
    return run


def test_daily_close_all_green_runs_product_before_research() -> None:
    seen: list[str] = []
    payload = execute_daily_close_steps(_runner({}, seen))

    assert payload["overall_status"] == "passed"
    assert payload["exit_code"] == 0
    assert payload["market_data_ready"] is True
    assert payload["m5_product_ready"] is True
    assert payload["m4_research_ready"] is True
    assert seen.index("m5_operator_cache") < seen.index(
        "m4_qfq_readiness"
    )
    assert seen.index("m4_qfq_readiness") < seen.index(
        "m5_operator_cache_finalize"
    )
    assert payload["boundaries"]["m5_product_requires_m4_qfq"] is False


def test_m4_qfq_failure_does_not_block_m5_product() -> None:
    seen: list[str] = []
    payload = execute_daily_close_steps(
        _runner({"m4_qfq_readiness": 2}, seen)
    )

    assert "m5_operator_cache" in seen
    assert seen.index("m5_operator_cache") < seen.index(
        "m4_qfq_readiness"
    )
    assert payload["m5_product_ready"] is True
    assert "m5_operator_cache_finalize" in seen
    assert seen.index("m4_qfq_readiness") < seen.index(
        "m5_operator_cache_finalize"
    )
    assert payload["m4_research_ready"] is False
    assert payload["overall_status"] == (
        "product_ready_research_degraded"
    )
    assert payload["exit_code"] == 0
    assert payload["steps"]["m4_capture"]["status"] == "skipped"


def test_m4_guard_failure_does_not_block_m5_product() -> None:
    seen: list[str] = []
    payload = execute_daily_close_steps(
        _runner({"m4_methodology_guard": 1}, seen)
    )

    assert "m5_operator_cache" in seen
    assert payload["m5_product_ready"] is True
    assert payload["m4_research_ready"] is False
    assert payload["exit_code"] == 0
    assert "m4_qfq_readiness" not in seen


def test_context_sync_failure_does_not_block_m5_product() -> None:
    seen: list[str] = []
    payload = execute_daily_close_steps(
        _runner({"context_sync": 2}, seen)
    )

    assert "m5_operator_cache" in seen
    assert payload["m5_product_ready"] is True
    assert payload["m5_context_refresh_ready"] is False
    assert payload["m5_context_degraded_but_product_allowed"] is True
    assert payload["overall_status"] == "product_ready_context_degraded"
    assert payload["exit_code"] == 0


def test_m1_failure_blocks_current_day_product_and_capture() -> None:
    seen: list[str] = []
    payload = execute_daily_close_steps(
        _runner({"m1_update": 2}, seen)
    )

    assert "context_sync" not in seen
    assert "m5_operator_cache" not in seen
    assert "m5_operator_cache_finalize" not in seen
    assert "m4_qfq_readiness" not in seen
    assert "m4_capture" not in seen
    assert payload["market_data_ready"] is False
    assert payload["m5_product_ready"] is False
    assert payload["exit_code"] == 2


def test_initial_m5_failure_can_recover_at_final_validation() -> None:
    seen: list[str] = []
    payload = execute_daily_close_steps(
        _runner({"m5_operator_cache": 2}, seen)
    )

    assert "m4_capture" in seen
    assert payload["m5_initial_product_ready"] is False
    assert payload["m5_product_ready"] is True
    assert payload["m4_research_ready"] is True
    assert payload["overall_status"] == "passed"
    assert payload["exit_code"] == 0


def test_persistent_m5_failure_does_not_suppress_valid_m4_lane() -> None:
    seen: list[str] = []
    payload = execute_daily_close_steps(
        _runner({
            "m5_operator_cache": 2,
            "m5_operator_cache_finalize": 2,
        }, seen)
    )

    assert "m4_capture" in seen
    assert payload["m5_product_ready"] is False
    assert payload["m4_research_ready"] is True
    assert payload["overall_status"] == "product_failed_research_ready"
    assert payload["exit_code"] == 2


def test_research_preflight_failure_only_skips_m4_lane() -> None:
    seen: list[str] = []
    payload = execute_daily_close_steps(
        _runner({}, seen),
        research_preflight_ready=False,
        research_preflight_reason="worktree_not_clean",
    )

    assert "m5_operator_cache" in seen
    assert payload["m5_product_ready"] is True
    assert payload["m4_research_ready"] is False
    assert payload["steps"]["m4_methodology_guard"]["status"] == "skipped"
    assert "m5_operator_cache_finalize" in seen
    assert payload["exit_code"] == 0


def test_outcome_requires_current_capture_health_and_observation() -> None:
    seen: list[str] = []
    payload = execute_daily_close_steps(
        _runner({"m4_health": 1}, seen)
    )

    assert "m4_outcome" not in seen
    assert payload["steps"]["m4_outcome"]["status"] == "skipped"
    assert payload["m4_research_ready"] is False


def test_daily_step_commands_keep_product_and_research_separate() -> None:
    assert STEP_SPECS["m5_operator_cache"].lane == "m5_product"
    assert STEP_SPECS["m5_operator_cache_finalize"].lane == "m5_product"
    assert STEP_SPECS["m4_qfq_readiness"].lane == "m4_research"
    assert STEP_SPECS["m5_operator_cache"].command[0] == (
        "scripts/m5_precompute_operator_snapshot.py"
    )
    assert STEP_SPECS["m4_capture"].command[0] == (
        "scripts/m4_capture_lifecycle_snapshot.py"
    )
    assert STEP_SPECS["m5_operator_cache_finalize"].command == (
        "scripts/m5_precompute_operator_snapshot.py",
    )


def test_final_product_validation_runs_after_research_lane() -> None:
    seen: list[str] = []
    payload = execute_daily_close_steps(_runner({}, seen))

    assert seen[-1] == "m5_operator_cache_finalize"
    assert payload["m5_final_cache_revalidated_after_research_lane"] is True
