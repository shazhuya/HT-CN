from __future__ import annotations

from scripts.m5_precompute_operator_snapshot import (
    evaluate_precompute_readiness,
)


def _payload(
    *,
    instrument_count: int = 3,
    analyzed: int = 3,
    failed: int = 0,
    as_of: str | None = "2026-09-18",
    integrity: str = "single_as_of",
    cache_status: str = "rebuilt_force",
    freshness: str = "current",
    input_stable: bool = True,
) -> dict:
    return {
        "instrument_count": instrument_count,
        "analyzed_instrument_count": analyzed,
        "failed_instrument_count": failed,
        "as_of_trade_date": as_of,
        "observation_integrity": integrity,
        "product_cache": {
            "status": cache_status,
            "freshness": freshness,
            "input_identity_stable_during_build": input_stable,
        },
    }


def test_precompute_ready_when_current_persisted_single_as_of() -> None:
    result = evaluate_precompute_readiness(
        _payload(),
        expected_trade_date="2026-09-18",
    )
    assert result["product_ready"] is True
    assert result["status"] == "ready"
    assert result["readiness_blockers"] == []


def test_instrument_failures_are_visible_but_nonblocking() -> None:
    result = evaluate_precompute_readiness(
        _payload(analyzed=2, failed=1),
        expected_trade_date="2026-09-18",
    )
    assert result["product_ready"] is True
    assert result["status"] == "ready_with_instrument_failures"
    assert result["failed_instrument_count"] == 1
    assert result["instrument_failures_are_isolated"] is True


def test_precompute_rejects_mixed_as_of() -> None:
    result = evaluate_precompute_readiness(
        _payload(as_of=None, integrity="mixed_as_of"),
        expected_trade_date="2026-09-18",
    )
    assert result["product_ready"] is False
    assert "queue_not_single_as_of" in result["readiness_blockers"]


def test_precompute_rejects_live_not_cached_result() -> None:
    result = evaluate_precompute_readiness(
        _payload(
            cache_status="live_not_cached_input_changed",
            input_stable=False,
        ),
        expected_trade_date="2026-09-18",
    )
    assert result["product_ready"] is False
    assert "product_cache_not_persisted" in result["readiness_blockers"]
    assert "input_identity_not_stable" in result["readiness_blockers"]


def test_precompute_rejects_stale_trade_date() -> None:
    result = evaluate_precompute_readiness(
        _payload(as_of="2026-09-17", freshness="stale"),
        expected_trade_date="2026-09-18",
    )
    assert result["product_ready"] is False
    assert "queue_trade_date_not_expected" in result["readiness_blockers"]
    assert "product_cache_not_current" in result["readiness_blockers"]
