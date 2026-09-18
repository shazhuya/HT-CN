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


def test_daily_close_all_green_runs_product_and_research() -> None:
    seen: list[str] = []
    payload = execute_daily_close_steps(_runner({}, seen))

    assert payload["overall_status"] == "passed"
    assert payload["exit_code"] == 0
    assert payload["data_ready"] is True
    assert payload["m5_product_ready"] is True
    assert payload["m4_research_ready"] is True
    assert "m5_operator_cache" in seen
    assert "m4_capture" in seen
    assert payload["boundaries"]["m5_cache_writes_m4_evidence"] is False


def test_daily_close_m5_failure_does_not_suppress_m4_capture() -> None:
    seen: list[str] = []
    payload = execute_daily_close_steps(
        _runner({"m5_operator_cache": 2}, seen)
    )

    assert "m4_capture" in seen
    assert payload["m5_product_ready"] is False
    assert payload["m4_research_ready"] is True
    assert payload["overall_status"] == "partial"
    assert payload["exit_code"] == 1


def test_daily_close_m4_capture_failure_does_not_suppress_m5_cache() -> None:
    seen: list[str] = []
    payload = execute_daily_close_steps(
        _runner({"m4_capture": 2}, seen)
    )

    assert "m5_operator_cache" in seen
    assert payload["m5_product_ready"] is True
    assert payload["m4_research_ready"] is False
    assert payload["overall_status"] == "partial"


def test_daily_close_m1_failure_skips_qfq_product_and_capture() -> None:
    seen: list[str] = []
    payload = execute_daily_close_steps(
        _runner({"m1_update": 2}, seen)
    )

    assert "qfq_readiness" not in seen
    assert "m5_operator_cache" not in seen
    assert "m4_capture" not in seen
    assert "m4_health" in seen
    assert "m4_transition" in seen
    assert "m4_observation" in seen
    assert payload["data_ready"] is False
    assert payload["overall_status"] == "failed"


def test_daily_close_guard_failure_stops_before_data_mutation() -> None:
    seen: list[str] = []
    payload = execute_daily_close_steps(
        _runner({"methodology_guard": 1}, seen)
    )

    assert seen == ["methodology_guard"]
    assert payload["overall_status"] == "failed_preflight"
    assert payload["exit_code"] == 2
    assert payload["steps"]["m1_update"]["status"] == "skipped"


def test_daily_close_outcome_requires_capture_health_observation() -> None:
    seen: list[str] = []
    payload = execute_daily_close_steps(
        _runner({"m4_health": 1}, seen)
    )

    assert "m4_outcome" not in seen
    assert payload["steps"]["m4_outcome"]["status"] == "skipped"
    assert payload["m4_research_ready"] is False


def test_daily_close_step_commands_keep_m4_and_m5_separate() -> None:
    assert STEP_SPECS["m5_operator_cache"].command[0] == (
        "scripts/m5_precompute_operator_snapshot.py"
    )
    assert STEP_SPECS["m4_capture"].command[0] == (
        "scripts/m4_capture_lifecycle_snapshot.py"
    )
