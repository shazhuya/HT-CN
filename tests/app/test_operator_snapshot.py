from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import threading
import time

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



def test_operator_snapshot_cache_hit_does_not_create_parallel_workers(
    tmp_path,
) -> None:
    base_service = CountingService()
    factory_calls = 0

    def factory() -> CountingService:
        nonlocal factory_calls
        factory_calls += 1
        return CountingService()

    first = build_or_load_operator_snapshot(
        base_service,
        ["SSE.1", "SSE.2"],
        cache_root=tmp_path,
        expected_trade_date="2026-09-18",
        max_workers=2,
        service_factory=factory,
    )
    calls_after_build = factory_calls
    assert first["product_cache"]["status"] == "rebuilt"
    assert calls_after_build >= 1
    assert first["build_execution"]["mode"] == "parallel_thread_pool"

    second = build_or_load_operator_snapshot(
        base_service,
        ["SSE.1", "SSE.2"],
        cache_root=tmp_path,
        expected_trade_date="2026-09-18",
        max_workers=2,
        service_factory=factory,
    )

    assert second["product_cache"]["status"] == "hit"
    assert factory_calls == calls_after_build



class BlockingCountingService:
    def __init__(
        self,
        *,
        started: threading.Event,
        release: threading.Event,
        counter: dict[str, int],
        lock: threading.Lock,
        as_of: str = "2026-09-18",
    ) -> None:
        self.started = started
        self.release = release
        self.counter = counter
        self.lock = lock
        self.as_of = as_of

    def analyze(
        self,
        instrument_id: str,
        *,
        bars: int,
        scales: tuple[int, ...],
    ) -> dict:
        with self.lock:
            self.counter["calls"] = self.counter.get("calls", 0) + 1
        self.started.set()
        if not self.release.wait(timeout=3):
            raise RuntimeError("test release timeout")
        return {
            "last_trade_date": self.as_of,
            "price_mode": "qfq",
            "warning": None,
            "completed": [],
            "forming": [_pattern()],
        }


def test_operator_snapshot_single_flight_coalesces_concurrent_cache_miss(
    tmp_path,
) -> None:
    started = threading.Event()
    release = threading.Event()
    lock = threading.Lock()
    counter = {"calls": 0}
    service = BlockingCountingService(
        started=started,
        release=release,
        counter=counter,
        lock=lock,
    )

    def run() -> dict:
        return build_or_load_operator_snapshot(
            service,
            ["SSE.1"],
            cache_root=tmp_path,
            expected_trade_date="2026-09-18",
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(run)
        assert started.wait(timeout=2)
        second_future = executor.submit(run)
        time.sleep(0.05)
        release.set()
        first = first_future.result(timeout=3)
        second = second_future.result(timeout=3)

    assert counter["calls"] == 1
    statuses = {
        first["product_cache"]["status"],
        second["product_cache"]["status"],
    }
    assert statuses == {"rebuilt", "coalesced_wait"}
    coalesced = (
        first
        if first["product_cache"]["status"] == "coalesced_wait"
        else second
    )
    assert coalesced["product_cache"]["coalesced_from_status"] == "rebuilt"
    assert coalesced["product_cache"]["single_flight_scope"] == (
        "process_local_cache_identity"
    )


def test_operator_snapshot_single_flight_coalesces_concurrent_force_refresh(
    tmp_path,
) -> None:
    build_or_load_operator_snapshot(
        CountingService(),
        ["SSE.1"],
        cache_root=tmp_path,
        expected_trade_date="2026-09-18",
    )

    started = threading.Event()
    release = threading.Event()
    lock = threading.Lock()
    counter = {"calls": 0}
    service = BlockingCountingService(
        started=started,
        release=release,
        counter=counter,
        lock=lock,
    )

    def refresh() -> dict:
        return build_or_load_operator_snapshot(
            service,
            ["SSE.1"],
            cache_root=tmp_path,
            expected_trade_date="2026-09-18",
            force_refresh=True,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(refresh)
        assert started.wait(timeout=2)
        second_future = executor.submit(refresh)
        time.sleep(0.05)
        release.set()
        first = first_future.result(timeout=3)
        second = second_future.result(timeout=3)

    assert counter["calls"] == 1
    statuses = {
        first["product_cache"]["status"],
        second["product_cache"]["status"],
    }
    assert statuses == {"rebuilt_force", "coalesced_wait"}
    coalesced = (
        first
        if first["product_cache"]["status"] == "coalesced_wait"
        else second
    )
    assert coalesced["product_cache"]["coalesced_from_status"] == (
        "rebuilt_force"
    )


def test_operator_snapshot_regular_cache_metadata_exposes_single_flight_scope(
    tmp_path,
) -> None:
    service = CountingService()
    build_or_load_operator_snapshot(
        service,
        ["SSE.1"],
        cache_root=tmp_path,
        expected_trade_date="2026-09-18",
    )
    hit = build_or_load_operator_snapshot(
        service,
        ["SSE.1"],
        cache_root=tmp_path,
        expected_trade_date="2026-09-18",
    )

    assert hit["product_cache"]["status"] == "hit"
    assert hit["product_cache"]["single_flight_scope"] == (
        "process_local_cache_identity"
    )
    assert hit["product_cache"]["coalesced_from_status"] is None
