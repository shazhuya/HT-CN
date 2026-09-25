import json
from pathlib import Path

from htcn.harmonic import pine_r34

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "research" / "pine-r34-recognition-contract-v1.json"


def test_pine_r34_machine_contract_matches_runtime_defaults():
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    params = contract["parameters"]

    assert contract["source_sha256"] == pine_r34.PINE_R34_SOURCE_SHA256
    assert tuple(params["scales"]) == pine_r34.PINE_R34_SCALES
    assert params["atr_length"] == 14
    assert params["min_leg_atr"] == 0.35
    assert params["max_source_span_bars"] == 500
    assert params["cluster_width_reference_leg"] == 0.12
    assert params["structure_life_bars"] == 180
    assert params["abcd_tolerance_pct"] == 3.0
    assert params["abcd_convergence_pct"] == 3.0
    assert params["test_gap_bars"] == 3
    assert params["test_session_bars"] == 12
    assert params["test_reset_atr"] == 0.75
    assert params["candidate_capacity"] == 180
    assert (
        params["unqualified_storage_limit"]
        == pine_r34.PINE_R34_UNQUALIFIED_STORAGE_LIMIT
    )
    assert params["near_atr"] == pine_r34.PINE_R34_NEAR_ATR
    assert params["journey_atr"] == pine_r34.PINE_R34_JOURNEY_ATR
    assert params["near_pct"] == pine_r34.PINE_R34_NEAR_PCT
    assert params["journey_pct"] == pine_r34.PINE_R34_JOURNEY_PCT
    assert params["visible_width_atr"] == pine_r34.PINE_R34_VISIBLE_WIDTH_ATR
    assert params["developing_age_bars"] == pine_r34.PINE_R34_DEVELOPING_AGE
    assert params["candidate_table_limit"] == pine_r34.PINE_R34_CANDIDATE_TABLE_LIMIT


def test_pine_r34_machine_contract_matches_rule_topology():
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    for row in contract["rules"]:
        rule = int(row["rule"])
        assert pine_r34._PATTERN_NAMES[rule] == row["id"]
        assert pine_r34._PATTERN_SCHEMA[rule] == row["schema"]
        assert list(pine_r34._SOURCE_LABELS[rule]) == row["source_nodes"]
        assert pine_r34._SOURCE_COUNT[rule] == len(row["source_nodes"])


def test_pine_r34_contract_preserves_non_authoritative_boundaries():
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    boundaries = contract["boundaries"]

    assert boundaries["behavioral_parity_is_not_source_identity"] is True
    assert boundaries["five_zero_remains_quarantined"] is True
    assert boundaries["alternate_bat_remains_fail_closed_for_canonical_identity"] is True
    assert boundaries["discovery_does_not_own_source_lifecycle"] is True
    assert boundaries["no_historical_prz_test_backfill"] is True
    assert boundaries["no_automatic_trading"] is True
