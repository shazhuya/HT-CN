from __future__ import annotations

import json
from pathlib import Path

from htcn.research.type_i_live_evidence import (
    classify_type_i_t5_audit,
    frozen_type_i_t5_reference,
)

ROOT = Path(__file__).resolve().parents[2]


def _audit(
    *,
    available: int,
    t2: int | None = None,
    exit_bar: int | None = None,
) -> dict:
    return {
        "status": "terminal_price_bar_observed",
        "available_future_bars_after_terminal": available,
        "bars_from_terminal_to_t2": t2,
        "bars_from_terminal_to_full_prz_exit": exit_bar,
    }


def test_t5_state_waits_until_five_bars_are_observed() -> None:
    state = classify_type_i_t5_audit(_audit(available=4, t2=None, exit_bar=3))
    assert state["state"] == "pending_t5_observation"
    assert state["bars_until_t5"] == 1
    assert state["eligible_for_frozen_contrast"] is False


def test_t2_reached_by_t5_is_outside_preregistered_pending_cohort() -> None:
    state = classify_type_i_t5_audit(_audit(available=3, t2=3, exit_bar=2))
    assert state["state"] == "t2_already_reached_by_t5"
    assert state["endpoint_state"] == "t2_hit_by_t5"
    assert state["eligible_for_frozen_contrast"] is False


def test_full_exit_by_t5_maps_to_frozen_exposure_only_after_t5() -> None:
    state = classify_type_i_t5_audit(_audit(available=5, t2=None, exit_bar=5))
    assert state["state"] == "full_prz_exit_by_t5"
    assert state["historical_group"] == "exposure"
    assert state["eligible_for_frozen_contrast"] is True
    assert state["endpoint_state"] == "pending_t20"


def test_no_full_exit_by_t5_maps_to_frozen_comparator() -> None:
    state = classify_type_i_t5_audit(_audit(available=20, t2=None, exit_bar=None))
    assert state["state"] == "no_full_prz_exit_by_t5"
    assert state["historical_group"] == "comparator"
    assert state["eligible_for_frozen_contrast"] is True
    assert state["endpoint_state"] == "no_t2_by_t20"


def test_later_t2_endpoint_is_descriptive_not_a_new_primary_test() -> None:
    state = classify_type_i_t5_audit(_audit(available=12, t2=9, exit_bar=4))
    assert state["state"] == "full_prz_exit_by_t5"
    assert state["endpoint_state"] == "t2_hit_t6_t20"


def test_runtime_reference_matches_frozen_consumed_holdout_result() -> None:
    frozen = json.loads(
        (ROOT / "research" / "m2-type-i-holdout-result-v1.json").read_text(encoding="utf-8")
    )
    primary = frozen["primary_contrast"]
    reference = frozen_type_i_t5_reference()

    assert reference["status"] == primary["result"] == "confirmed"
    assert reference["preregistration_id"] == frozen["preregistration_id"]
    assert reference["dataset_id"] == frozen["dataset"]["dataset_id"]
    assert reference["snapshot_cutoff"] == frozen["dataset"]["snapshot_cutoff"]
    assert reference["exposure"] == {
        "name": primary["exposure_name"],
        **primary["exposure"],
    }
    assert reference["comparator"] == {
        "name": primary["comparator_name"],
        **primary["comparator"],
    }
    assert reference["absolute_rate_difference"] == primary["absolute_rate_difference"]
    assert reference["newcombe_95_ci"] == primary["newcombe_95_ci"]


def test_runtime_reference_matches_frozen_external_replication_result() -> None:
    frozen = json.loads(
        (ROOT / "research" / "m2-type-i-external-replication-result-v1.json").read_text(
            encoding="utf-8"
        )
    )
    primary = frozen["primary_contrast"]
    replication = frozen_type_i_t5_reference()["external_replication"]

    assert replication["status"] == primary["result"] == "confirmed"
    assert replication["preregistration_id"] == frozen["preregistration_id"]
    assert replication["dataset_id"] == frozen["dataset"]["dataset_id"]
    assert replication["snapshot_cutoff"] == frozen["dataset"]["snapshot_cutoff"]
    assert replication["successful_symbols"] == frozen["dataset"]["successful_symbols"] == 60
    assert replication["eligible_pending_t2_at_t5"] == frozen["eligible_pending_t2_at_t5"]
    assert replication["exposure"] == {
        "name": primary["exposure_name"],
        **primary["exposure"],
    }
    assert replication["comparator"] == {
        "name": primary["comparator_name"],
        **primary["comparator"],
    }
    assert replication["absolute_rate_difference"] == primary["absolute_rate_difference"]
    assert replication["newcombe_95_ci"] == primary["newcombe_95_ci"]
    assert replication["concentration"]["eligible_symbols"] == frozen["concentration"]["eligible_symbols"]
    assert replication["concentration"]["largest_symbol_share"] == frozen["concentration"]["largest_symbol_share"]
