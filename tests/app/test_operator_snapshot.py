from __future__ import annotations

import json

from htcn.app.operator_snapshot import (
    OPERATOR_SNAPSHOT_CONTRACT_VERSION,
    build_or_load_operator_snapshot,
    operator_universe_hash,
)


def _pattern() -> dict:
    return {
        "pattern_id": "bat",
        "schema": "XABCD",
        "direction": "bullish",
        "scale": 5,
        "state": "forming",
        "is_primary_identity": True,
        "points": [
            {"index": 1, "trade_date": "2026-09-10"},
            {"index": 2, "trade_date": "2026-09-11"},
            {"index": 3, "trade_date": "2026-09-14"},
            {"index": 4, "trade_date": "2026-09-15"},
        ],
        "source_lifecycle": {
            "state": "approaching_source_prz",
            "state_reason": "source-backed",
            "source_prz_low": 95.0,
            "source_prz_high": 100.0,
            "bars_since_terminal": None,
        },
        "decision_narrative": {
            "action_state": "waiting",
            "current_position": "current",
            "first_watch": "first",
            "next_watch": "next",
            "upgrade_blocker": "blocker",
            "next_key_price": 100.0,
            "next_key_price_role": "source_prz_entry_edge",
            "execution_context_gate": "tradable",
            "context_cautions": [],
        },
    }


class CountingService:
    def __init__(self, as_of: str = "2026-09-18") -> None:
        self.calls = 0
        self.as_of = as_of

    def analyze(self, instrument_id: str, *, bars: int, scales: tuple[int, ...]):
        self.calls += 1
        return {
            "last_trade_date": self.as_of,
            "price_mode": "qfq",
            "warning": None,
            "completed": [],
            "forming": [_pattern()],
        }


def test_operator_snapshot_cache_hit_avoids_reanalysis(tmp_path) -> None:
    service = CountingService()

    first = build_or_load_operator_snapshot(
        service,
        ["SSE.1", "SSE.2"],
        cache_root=tmp_path,
        expected_trade_date="2026-09-18",
    )
    calls_after_first = service.calls
    second = build_or_load_operator_snapshot(
        service,
        ["SSE.1", "SSE.2"],
        cache_root=tmp_path,
        expected_trade_date="2026-09-18",
    )

    assert calls_after_first == 2
    assert service.calls == 2
    assert first["product_cache"]["status"] == "rebuilt"
    assert second["product_cache"]["status"] == "hit"
    assert second["candidate_count"] == first["candidate_count"]


def test_operator_snapshot_force_refresh_reanalyzes(tmp_path) -> None:
    service = CountingService()
    build_or_load_operator_snapshot(
        service,
        ["SSE.1"],
        cache_root=tmp_path,
        expected_trade_date="2026-09-18",
    )
    assert service.calls == 1

    refreshed = build_or_load_operator_snapshot(
        service,
        ["SSE.1"],
        cache_root=tmp_path,
        expected_trade_date="2026-09-18",
        force_refresh=True,
    )

    assert service.calls == 2
    assert refreshed["product_cache"]["status"] == "rebuilt_force"


def test_operator_snapshot_universe_change_invalidates_cache(tmp_path) -> None:
    service = CountingService()
    build_or_load_operator_snapshot(
        service,
        ["SSE.1"],
        cache_root=tmp_path,
        expected_trade_date="2026-09-18",
    )
    assert service.calls == 1

    build_or_load_operator_snapshot(
        service,
        ["SSE.1", "SSE.2"],
        cache_root=tmp_path,
        expected_trade_date="2026-09-18",
    )

    assert service.calls == 3


def test_operator_snapshot_trade_date_gets_separate_cache(tmp_path) -> None:
    service = CountingService(as_of="2026-09-17")
    build_or_load_operator_snapshot(
        service,
        ["SSE.1"],
        cache_root=tmp_path,
        expected_trade_date="2026-09-17",
    )
    service.as_of = "2026-09-18"
    current = build_or_load_operator_snapshot(
        service,
        ["SSE.1"],
        cache_root=tmp_path,
        expected_trade_date="2026-09-18",
    )

    assert service.calls == 2
    assert current["as_of_trade_date"] == "2026-09-18"
    assert len(list(tmp_path.glob("*.json"))) == 2


def test_operator_snapshot_is_product_cache_not_evidence(tmp_path) -> None:
    service = CountingService()
    payload = build_or_load_operator_snapshot(
        service,
        ["SSE.1"],
        cache_root=tmp_path,
        expected_trade_date="2026-09-18",
    )

    cache = payload["product_cache"]
    assert cache["contract_version"] == OPERATOR_SNAPSHOT_CONTRACT_VERSION
    assert cache["authoritative_evidence"] is False
    assert cache["writes_m4_evidence"] is False


def test_operator_universe_hash_is_order_independent() -> None:
    assert operator_universe_hash(["SSE.2", "SSE.1"]) == (
        operator_universe_hash(["SSE.1", "SSE.2"])
    )


def test_operator_snapshot_file_contains_contract_and_universe_hash(tmp_path) -> None:
    service = CountingService()
    build_or_load_operator_snapshot(
        service,
        ["SSE.1"],
        cache_root=tmp_path,
        expected_trade_date="2026-09-18",
    )

    path = next(tmp_path.glob("*.json"))
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["contract_version"] == OPERATOR_SNAPSHOT_CONTRACT_VERSION
    assert stored["universe_hash"] == operator_universe_hash(["SSE.1"])
    assert stored["authoritative_evidence"] is False



def test_operator_snapshot_does_not_cache_stale_queue_as_current_date(
    tmp_path,
) -> None:
    service = CountingService(as_of="2026-09-17")

    payload = build_or_load_operator_snapshot(
        service,
        ["SSE.1"],
        cache_root=tmp_path,
        expected_trade_date="2026-09-18",
    )

    assert payload["product_cache"]["status"] == "live_not_cached"
    assert payload["product_cache"]["freshness"] == "stale"
    assert list(tmp_path.glob("*.json")) == []
