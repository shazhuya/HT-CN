from __future__ import annotations

from htcn.app.operator_queue import (
    WORKFLOW_BUCKET_ORDER,
    build_operator_queue,
)


def _pattern(
    *,
    pattern_id: str,
    action_state: str,
    lifecycle_state: str,
    primary: bool = True,
    next_key_price: float | None = 100.0,
) -> dict:
    return {
        "pattern_id": pattern_id,
        "schema": "XABCD",
        "direction": "bullish",
        "scale": 5,
        "state": "forming",
        "is_primary_identity": primary,
        "points": [
            {"index": 1},
            {"index": 2},
            {"index": 3},
            {"index": 4},
        ],
        "source_lifecycle": {
            "state": lifecycle_state,
            "state_reason": "source-backed",
            "source_prz_low": 95.0,
            "source_prz_high": 100.0,
            "bars_since_terminal": None,
        },
        "decision_narrative": {
            "action_state": action_state,
            "current_position": "current",
            "first_watch": "first",
            "next_watch": "next",
            "upgrade_blocker": "blocker",
            "next_key_price": next_key_price,
            "next_key_price_role": "source_prz_entry_edge",
            "execution_context_gate": "tradable",
            "context_cautions": [],
        },
    }


class FakeService:
    def __init__(self, payloads: dict[str, dict]) -> None:
        self.payloads = payloads

    def analyze(self, instrument_id: str, *, bars: int, scales: tuple[int, ...]):
        value = self.payloads[instrument_id]
        if isinstance(value, Exception):
            raise value
        return value


def _analysis(*patterns: dict) -> dict:
    return {
        "last_trade_date": "2026-09-18",
        "price_mode": "qfq",
        "warning": None,
        "completed": [],
        "forming": list(patterns),
    }


def test_operator_queue_uses_workflow_bucket_not_predictive_score() -> None:
    service = FakeService({
        "SSE.1": _analysis(
            _pattern(
                pattern_id="bat",
                action_state="waiting",
                lifecycle_state="approaching_source_prz",
            )
        ),
        "SSE.2": _analysis(
            _pattern(
                pattern_id="crab",
                action_state="execution_evaluation",
                lifecycle_state="type_i_confirmed",
            )
        ),
    })

    payload = build_operator_queue(service, ["SSE.1", "SSE.2"])

    assert [item["instrument_id"] for item in payload["items"]] == [
        "SSE.2",
        "SSE.1",
    ]
    assert payload["contract"]["ranking_mode"] == "workflow_bucket_only"
    assert payload["contract"]["predictive_score_used"] is False
    assert payload["contract"]["historical_outcome_used"] is False
    assert payload["contract"]["alpha_inference_allowed"] is False
    assert payload["contract"]["is_trade_instruction"] is False
    prohibited = {
        "geometry_score",
        "ranking_score",
        "win_rate",
        "alpha",
        "expected_return",
        "buy_score",
        "sell_score",
    }
    assert all(
        prohibited.isdisjoint(item)
        for item in payload["items"]
    )
    assert all(
        item["predictive_score_used"] is False
        for item in payload["items"]
    )


def test_operator_queue_filters_secondary_identity() -> None:
    service = FakeService({
        "SSE.1": _analysis(
            _pattern(
                pattern_id="bat",
                action_state="waiting",
                lifecycle_state="approaching_source_prz",
                primary=True,
            ),
            _pattern(
                pattern_id="alternate_bat",
                action_state="waiting",
                lifecycle_state="approaching_source_prz",
                primary=False,
            ),
        )
    })

    payload = build_operator_queue(service, ["SSE.1"])

    assert payload["candidate_count"] == 1
    assert payload["items"][0]["pattern_id"] == "bat"


def test_operator_queue_isolates_instrument_error() -> None:
    service = FakeService({
        "SSE.1": RuntimeError("bad local data"),
        "SSE.2": _analysis(
            _pattern(
                pattern_id="crab",
                action_state="reaction_observation",
                lifecycle_state="t_plus_1",
            )
        ),
    })

    payload = build_operator_queue(service, ["SSE.1", "SSE.2"])

    assert payload["analyzed_instrument_count"] == 1
    assert payload["failed_instrument_count"] == 1
    assert payload["candidate_count"] == 1
    assert payload["errors"][0]["instrument_id"] == "SSE.1"


def test_operator_queue_can_hide_evidence_insufficient() -> None:
    service = FakeService({
        "SSE.1": _analysis(
            _pattern(
                pattern_id="five_zero",
                action_state="evidence_insufficient",
                lifecycle_state="source_clock_unavailable",
            ),
            _pattern(
                pattern_id="bat",
                action_state="waiting",
                lifecycle_state="approaching_source_prz",
            ),
        )
    })

    payload = build_operator_queue(
        service,
        ["SSE.1"],
        include_evidence_insufficient=False,
    )

    assert payload["candidate_count"] == 1
    assert payload["items"][0]["pattern_id"] == "bat"


def test_workflow_bucket_order_is_explicit_and_small() -> None:
    assert WORKFLOW_BUCKET_ORDER == {
        "execution_evaluation": 0,
        "reaction_observation": 1,
        "waiting": 2,
        "evidence_insufficient": 3,
    }
