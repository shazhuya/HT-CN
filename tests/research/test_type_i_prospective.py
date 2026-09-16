from __future__ import annotations

import json
from pathlib import Path

import pytest

from htcn.research.type_i_prospective import (
    PROSPECTIVE_CUTOFF,
    PROSPECTIVE_PROTOCOL_ID,
    ProspectiveRegistryStore,
    empty_registry,
    registry_summary,
    stable_prospective_event_id,
    update_registry,
)


ROOT = Path(__file__).resolve().parents[2]


def _event(
    *,
    terminal_date: str = "2026-09-16",
    signal_date: str = "2026-09-15",
    available: int,
    state: str,
    endpoint: str,
    group: str | None = None,
    exit_bar: int | None = None,
    t2_bar: int | None = None,
    price_shift: float = 0.0,
) -> dict:
    return {
        "event_id": "ui-index-dependent-id",
        "instrument_id": "SSE.688256",
        "pattern_id": "bat",
        "schema": "XABCD",
        "direction": "bullish",
        "source_scale": 5,
        "signal_scales": [5, 8],
        "forming_signal_bar": 100,
        "forming_signal_trade_date": signal_date,
        "terminal_bar": 103,
        "terminal_trade_date": terminal_date,
        "terminal_price": 100.0 + price_shift,
        "prz": {"price_low": 99.0 + price_shift, "price_high": 101.0 + price_shift},
        "t1_name": "38.2%",
        "t1_price": 110.0 + price_shift,
        "t2_name": "61.8%",
        "t2_price": 116.0 + price_shift,
        "bars_from_terminal_to_t1": None,
        "bars_from_terminal_to_t2": t2_bar,
        "bars_from_terminal_to_full_prz_exit": exit_bar,
        "available_future_bars_after_terminal": available,
        "t5_evidence": {
            "state": state,
            "display_label": state,
            "eligible_for_frozen_contrast": group in {"exposure", "comparator"},
            "historical_group": group,
            "bars_until_t5": max(0, 5 - available) if state == "pending_t5_observation" else 0,
            "endpoint_state": endpoint,
        },
    }


def test_protocol_file_matches_code_constants() -> None:
    protocol = json.loads(
        (ROOT / "research" / "m2-type-i-prospective-protocol-v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert protocol["protocol_id"] == PROSPECTIVE_PROTOCOL_ID
    assert protocol["registered_cutoff"] == PROSPECTIVE_CUTOFF
    assert protocol["inference"]["confirmatory_test_in_registry"] is False
    assert protocol["inference"]["interim_significance_testing"] is False
    assert protocol["identity_separation"]["carney_geometry_mutated"] is False


def test_stable_id_does_not_depend_on_ui_bar_indices_or_prices() -> None:
    first = _event(available=1, state="pending_t5_observation", endpoint="pending_t20")
    second = dict(first)
    second["forming_signal_bar"] = 42
    second["terminal_bar"] = 45
    second["terminal_price"] = 88.0
    second["prz"] = {"price_low": 87.0, "price_high": 89.0}
    assert stable_prospective_event_id(first) == stable_prospective_event_id(second)


def test_pre_cutoff_event_is_not_registered() -> None:
    registry = update_registry(
        empty_registry(),
        [
            _event(
                terminal_date="2026-09-15",
                available=5,
                state="full_prz_exit_by_t5",
                endpoint="pending_t20",
                group="exposure",
                exit_bar=3,
            )
        ],
        observed_through_trade_date="2026-09-22",
    )
    assert registry["events"] == {}


def test_live_event_registers_before_endpoint_and_matures_monotonically() -> None:
    registry = empty_registry()
    pending = _event(
        available=2,
        state="pending_t5_observation",
        endpoint="pending_t20",
    )
    registry = update_registry(
        registry,
        [pending],
        observed_through_trade_date="2026-09-18",
    )
    event_id = stable_prospective_event_id(pending)
    record = registry["events"][event_id]
    assert record["registration"]["prospective_registration_valid"] is True
    assert record["registration"]["registration_mode"] == "prospective_before_endpoint_window"

    exposure = _event(
        available=5,
        state="full_prz_exit_by_t5",
        endpoint="pending_t20",
        group="exposure",
        exit_bar=3,
    )
    registry = update_registry(
        registry,
        [exposure],
        observed_through_trade_date="2026-09-23",
    )
    hit = _event(
        available=11,
        state="full_prz_exit_by_t5",
        endpoint="t2_hit_t6_t20",
        group="exposure",
        exit_bar=3,
        t2_bar=9,
    )
    registry = update_registry(
        registry,
        [hit],
        observed_through_trade_date="2026-10-09",
    )
    observations = registry["events"][event_id]["observations"]
    assert [row["state"] for row in observations] == [
        "pending_t5_observation",
        "full_prz_exit_by_t5",
        "full_prz_exit_by_t5",
    ]
    assert observations[-1]["endpoint_state"] == "t2_hit_t6_t20"
    summary = registry_summary(registry)
    assert summary.prospective_registered_before_endpoint == 1
    assert summary.exposure_group == 1
    assert summary.matured_t20 == 1
    assert "rate" not in summary.as_payload()


def test_first_seen_after_t5_is_permanently_backfilled_not_prospective() -> None:
    backfill = _event(
        available=8,
        state="no_full_prz_exit_by_t5",
        endpoint="pending_t20",
        group="comparator",
    )
    registry = update_registry(
        empty_registry(),
        [backfill],
        observed_through_trade_date="2026-09-28",
    )
    record = registry["events"][stable_prospective_event_id(backfill)]
    assert record["registration"]["prospective_registration_valid"] is False
    assert record["registration"]["registration_mode"] == "backfilled_after_t5"
    summary = registry_summary(registry)
    assert summary.total_events == 1
    assert summary.prospective_registered_before_endpoint == 0
    assert summary.backfilled_excluded == 1


def test_registered_group_cannot_flip_after_t5() -> None:
    exposure = _event(
        available=5,
        state="full_prz_exit_by_t5",
        endpoint="pending_t20",
        group="exposure",
        exit_bar=3,
    )
    registry = update_registry(
        empty_registry(),
        [exposure],
        observed_through_trade_date="2026-09-23",
    )
    comparator = _event(
        available=6,
        state="no_full_prz_exit_by_t5",
        endpoint="pending_t20",
        group="comparator",
    )
    with pytest.raises(ValueError, match="state transition"):
        update_registry(
            registry,
            [comparator],
            observed_through_trade_date="2026-09-24",
        )


def test_same_date_price_rebase_is_idempotent_but_state_revision_fails() -> None:
    event = _event(
        available=4,
        state="pending_t5_observation",
        endpoint="pending_t20",
    )
    registry = update_registry(
        empty_registry(),
        [event],
        observed_through_trade_date="2026-09-21",
    )
    rebased = _event(
        available=4,
        state="pending_t5_observation",
        endpoint="pending_t20",
        price_shift=-20.0,
    )
    again = update_registry(
        registry,
        [rebased],
        observed_through_trade_date="2026-09-21",
    )
    event_id = stable_prospective_event_id(event)
    assert len(again["events"][event_id]["observations"]) == 1

    revised = _event(
        available=4,
        state="full_prz_exit_by_t5",
        endpoint="pending_t20",
        group="exposure",
        exit_bar=3,
    )
    with pytest.raises(ValueError, match="same-date prospective state changed"):
        update_registry(
            registry,
            [revised],
            observed_through_trade_date="2026-09-21",
        )


def test_registry_store_round_trip_is_atomic_json(tmp_path: Path) -> None:
    path = tmp_path / "prospective.json"
    store = ProspectiveRegistryStore(path)
    assert store.read()["events"] == {}
    event = _event(
        available=1,
        state="pending_t5_observation",
        endpoint="pending_t20",
    )
    registry = update_registry(
        store.read(),
        [event],
        observed_through_trade_date="2026-09-17",
    )
    store.write(registry)
    assert store.read() == registry
    assert not path.with_suffix(".json.tmp").exists()
