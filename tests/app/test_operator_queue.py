from __future__ import annotations

import threading

from htcn.app.operator_queue import (
    WORKFLOW_BUCKET_ORDER,
    build_operator_queue,
    discover_local_instruments,
    filter_operator_queue_payload,
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
            {"index": 1, "trade_date": "2026-09-10"},
            {"index": 2, "trade_date": "2026-09-11"},
            {"index": 3, "trade_date": "2026-09-14"},
            {"index": 4, "trade_date": "2026-09-15"},
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


def _discovery_pattern() -> dict:
    return {
        "pattern_id": "gartley",
        "schema": "XABCD",
        "direction": "bullish",
        "scale": 10,
        "state": "forming",
        "channel": "discovery",
        "discovery_only": True,
        "is_primary_identity": True,
        "points": [
            {"index": 1, "trade_date": "2026-09-10"},
            {"index": 2, "trade_date": "2026-09-11"},
            {"index": 3, "trade_date": "2026-09-14"},
            {"index": 4, "trade_date": "2026-09-15"},
        ],
        "prz": {
            "source_prz_low": 95.0,
            "source_prz_high": 100.0,
            "source_prz": {
                "available": True,
                "price_low": 95.0,
                "price_high": 100.0,
            },
        },
        "discovery": {
            "prz_status": "projected",
            "path_kind": "minor_swing_skip",
            "authoritative_identity": False,
            "fabricates_d": False,
            "owns_lifecycle": False,
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




def test_discover_local_instruments_can_limit_exchange_scope(tmp_path) -> None:
    daily_root = tmp_path / "daily"
    daily_root.mkdir()
    for name in (
        "BSE.920001.parquet",
        "SSE.600000.parquet",
        "SZSE.000001.parquet",
    ):
        (daily_root / name).touch()

    assert discover_local_instruments(tmp_path) == [
        "BSE.920001",
        "SSE.600000",
        "SZSE.000001",
    ]
    assert discover_local_instruments(
        tmp_path,
        exchanges=("SSE", "SZSE"),
    ) == [
        "SSE.600000",
        "SZSE.000001",
    ]


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


def test_operator_queue_includes_bounded_discovery_without_fabricating_lifecycle() -> None:
    analysis = _analysis()
    analysis["discovery"] = [_discovery_pattern()]
    service = FakeService({"SSE.1": analysis})

    payload = build_operator_queue(service, ["SSE.1"])

    assert payload["candidate_count"] == 1
    item = payload["items"][0]
    assert item["pattern_state"] == "discovery"
    assert item["discovery_only"] is True
    assert item["lifecycle_state"] == "discovery_candidate"
    assert item["action_state"] == "evidence_insufficient"
    assert item["predictive_score_used"] is False
    assert item["next_key_price"] is None
    assert "geometry_score" not in item


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



def test_operator_queue_exposes_single_as_of_trade_date() -> None:
    service = FakeService({
        "SSE.1": _analysis(
            _pattern(
                pattern_id="bat",
                action_state="waiting",
                lifecycle_state="approaching_source_prz",
            )
        ),
    })

    payload = build_operator_queue(service, ["SSE.1"])

    assert payload["schema_version"] == 2
    assert payload["as_of_trade_date"] == "2026-09-18"
    assert payload["observed_trade_dates"] == ["2026-09-18"]
    assert payload["observation_integrity"] == "single_as_of"


def test_operator_queue_display_key_uses_trade_dates_not_rolling_indexes() -> None:
    first = _pattern(
        pattern_id="bat",
        action_state="waiting",
        lifecycle_state="approaching_source_prz",
    )
    shifted = {
        **first,
        "points": [
            {**point, "index": int(point["index"]) - 1}
            for point in first["points"]
        ],
    }
    service = FakeService({
        "SSE.1": _analysis(first),
        "SSE.2": _analysis(shifted),
    })

    payload = build_operator_queue(service, ["SSE.1", "SSE.2"])
    first_key = payload["items"][0]["display_key"]
    second_key = payload["items"][1]["display_key"]

    assert first_key.split(":", 1)[1] == second_key.split(":", 1)[1]
    assert "2026-09-10" in first_key


def test_operator_queue_reports_mixed_as_of_dates() -> None:
    service = FakeService({
        "SSE.1": _analysis(
            _pattern(
                pattern_id="bat",
                action_state="waiting",
                lifecycle_state="approaching_source_prz",
            )
        ),
        "SSE.2": {
            **_analysis(
                _pattern(
                    pattern_id="crab",
                    action_state="waiting",
                    lifecycle_state="approaching_source_prz",
                )
            ),
            "last_trade_date": "2026-09-17",
        },
    })

    payload = build_operator_queue(service, ["SSE.1", "SSE.2"])

    assert payload["as_of_trade_date"] is None
    assert payload["observed_trade_dates"] == [
        "2026-09-17",
        "2026-09-18",
    ]
    assert payload["observation_integrity"] == "mixed_as_of"



def test_operator_queue_presentation_filter_preserves_full_snapshot_input() -> None:
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
    full = build_operator_queue(service, ["SSE.1"])
    filtered = filter_operator_queue_payload(
        full,
        include_evidence_insufficient=False,
    )

    assert full["candidate_count"] == 2
    assert filtered["candidate_count"] == 1
    assert filtered["items"][0]["pattern_id"] == "bat"
    assert {
        item["action_state"]
        for item in full["items"]
    } == {"waiting", "evidence_insufficient"}



def test_parallel_operator_queue_matches_serial_semantics() -> None:
    payloads = {
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
        "SZSE.3": _analysis(
            _pattern(
                pattern_id="gartley",
                action_state="reaction_observation",
                lifecycle_state="t_plus_1",
            )
        ),
    }
    instruments = ["SSE.1", "SSE.2", "SZSE.3"]

    serial = build_operator_queue(
        FakeService(payloads),
        instruments,
        max_workers=1,
    )
    parallel = build_operator_queue(
        FakeService(payloads),
        instruments,
        max_workers=3,
        service_factory=lambda: FakeService(payloads),
    )

    assert parallel["items"] == serial["items"]
    assert parallel["errors"] == serial["errors"]
    assert parallel["action_state_counts"] == serial["action_state_counts"]
    assert parallel["lifecycle_state_counts"] == serial["lifecycle_state_counts"]
    assert parallel["as_of_trade_date"] == serial["as_of_trade_date"]
    assert serial["build_execution"]["mode"] == "sequential"
    assert parallel["build_execution"]["mode"] == "parallel_thread_pool"
    assert parallel["build_execution"]["changes_queue_semantics"] is False


def test_parallel_request_without_factory_falls_back_to_sequential() -> None:
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
                action_state="waiting",
                lifecycle_state="approaching_source_prz",
            )
        ),
    })

    payload = build_operator_queue(
        service,
        ["SSE.1", "SSE.2"],
        max_workers=4,
    )

    execution = payload["build_execution"]
    assert execution["mode"] == "sequential"
    assert execution["effective_max_workers"] == 1
    assert execution["parallel_fallback_reason"] == (
        "service_factory_required_for_parallel_isolation"
    )


def test_parallel_operator_queue_uses_thread_local_service_instances() -> None:
    lock = threading.Lock()
    barrier = threading.Barrier(2)
    service_ids: set[int] = set()

    class ProbeService:
        def analyze(
            self,
            instrument_id: str,
            *,
            bars: int,
            scales: tuple[int, ...],
        ) -> dict:
            with lock:
                service_ids.add(id(self))
            barrier.wait(timeout=2)
            return _analysis(
                _pattern(
                    pattern_id="bat",
                    action_state="waiting",
                    lifecycle_state="approaching_source_prz",
                )
            )

    payload = build_operator_queue(
        ProbeService(),
        ["SSE.1", "SSE.2"],
        max_workers=2,
        service_factory=ProbeService,
    )

    assert payload["failed_instrument_count"] == 0
    assert payload["analyzed_instrument_count"] == 2
    assert len(service_ids) == 2
    assert payload["build_execution"]["service_isolation"] == (
        "thread_local_service_factory"
    )


def test_parallel_operator_queue_keeps_error_isolation_and_progress() -> None:
    payloads: dict[str, dict | Exception] = {
        "SSE.1": _analysis(
            _pattern(
                pattern_id="bat",
                action_state="waiting",
                lifecycle_state="approaching_source_prz",
            )
        ),
        "SSE.2": RuntimeError("broken local history"),
        "SSE.3": _analysis(
            _pattern(
                pattern_id="crab",
                action_state="reaction_observation",
                lifecycle_state="t_plus_1",
            )
        ),
    }
    progress: list[tuple[int, int, str, bool]] = []

    payload = build_operator_queue(
        FakeService(payloads),
        ["SSE.1", "SSE.2", "SSE.3"],
        max_workers=3,
        service_factory=lambda: FakeService(payloads),
        progress_callback=lambda done, total, instrument, ok: progress.append(
            (done, total, instrument, ok)
        ),
    )

    assert payload["analyzed_instrument_count"] == 2
    assert payload["failed_instrument_count"] == 1
    assert payload["errors"][0]["instrument_id"] == "SSE.2"
    assert len(progress) == 3
    assert {row[2] for row in progress} == {"SSE.1", "SSE.2", "SSE.3"}
    assert progress[-1][0] == 3
    assert all(row[1] == 3 for row in progress)
