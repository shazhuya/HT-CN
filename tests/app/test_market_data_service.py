from __future__ import annotations

from datetime import date

from htcn.app.market_data_service import (
    MarketDataServiceStep,
    RetryPolicy,
    empty_market_data_service_status,
    evaluate_market_data_schedule,
    execute_market_data_cycle,
    read_market_data_service_status,
    write_market_data_service_status,
)


def _steps() -> tuple[MarketDataServiceStep, ...]:
    return (
        MarketDataServiceStep("incremental_a_share_update", ("raw",), "raw.log", True),
        MarketDataServiceStep("qfq_readiness", ("qfq",), "qfq.log"),
        MarketDataServiceStep("local_data_health", ("health",), "health.log"),
    )


def test_schedule_is_idempotent_for_already_successful_closed_session() -> None:
    decision = evaluate_market_data_schedule(
        target_trade_date=date(2026, 9, 22),
        last_success_trade_date="2026-09-22",
    )
    assert decision.due is False
    assert decision.reason == "already_current"


def test_schedule_runs_exactly_when_new_closed_session_exists() -> None:
    decision = evaluate_market_data_schedule(
        target_trade_date="2026-09-22",
        last_success_trade_date="2026-09-21",
    )
    assert decision.due is True
    assert decision.reason == "new_closed_trade_session"


def test_step_retry_recovers_without_restarting_whole_cycle() -> None:
    calls: dict[str, int] = {}

    def runner(step: MarketDataServiceStep) -> int:
        calls[step.name] = calls.get(step.name, 0) + 1
        if step.name == "qfq_readiness" and calls[step.name] == 1:
            return 2
        return 0

    payload = execute_market_data_cycle(
        run_step=runner,
        retry_policy=RetryPolicy(max_attempts=2, base_delay_seconds=0),
        steps=_steps(),
        sleep_fn=lambda _: None,
    )

    assert payload["healthy"] is True
    assert payload["overall_status"] == "healthy"
    assert payload["steps"]["qfq_readiness"]["attempts"] == 2
    assert calls == {
        "incremental_a_share_update": 1,
        "qfq_readiness": 2,
        "local_data_health": 1,
    }


def test_raw_update_failure_blocks_qfq_and_health() -> None:
    def runner(step: MarketDataServiceStep) -> int:
        return 2 if step.name == "incremental_a_share_update" else 0

    payload = execute_market_data_cycle(
        run_step=runner,
        retry_policy=RetryPolicy(max_attempts=2, base_delay_seconds=0),
        steps=_steps(),
        sleep_fn=lambda _: None,
    )

    assert payload["overall_status"] == "failed"
    assert payload["raw_market_data_ready"] is False
    assert payload["steps"]["incremental_a_share_update"]["attempts"] == 2
    assert payload["steps"]["qfq_readiness"]["status"] == "skipped"
    assert payload["steps"]["local_data_health"]["status"] == "skipped"
    assert any("增量行情更新失败" in item for item in payload["diagnostics_zh"])


def test_qfq_failure_keeps_health_observable_but_cycle_degraded() -> None:
    def runner(step: MarketDataServiceStep) -> int:
        return 2 if step.name == "qfq_readiness" else 0

    payload = execute_market_data_cycle(
        run_step=runner,
        retry_policy=RetryPolicy(max_attempts=1, base_delay_seconds=0),
        steps=_steps(),
        sleep_fn=lambda _: None,
    )

    assert payload["overall_status"] == "degraded"
    assert payload["raw_market_data_ready"] is True
    assert payload["qfq_ready"] is False
    assert payload["local_health_ready"] is True


def test_status_file_is_atomic_readable_and_chinese_diagnostic_survives(tmp_path) -> None:
    path = tmp_path / "runtime" / "status.json"
    payload = empty_market_data_service_status()
    payload["status"] = "healthy"
    payload["diagnostics_zh"] = ["行情服务正常。"]

    write_market_data_service_status(path, payload)
    restored = read_market_data_service_status(path)

    assert restored["status"] == "healthy"
    assert restored["diagnostics_zh"] == ["行情服务正常。"]
    assert not path.with_suffix(".json.tmp").exists()


def test_missing_status_file_returns_explicit_not_started_state(tmp_path) -> None:
    payload = read_market_data_service_status(tmp_path / "missing.json")
    assert payload["status"] == "not_started"
    assert payload["healthy"] is False
    assert "尚未产生运行状态" in payload["diagnostics_zh"][0]
