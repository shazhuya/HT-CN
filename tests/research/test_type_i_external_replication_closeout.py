from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUTHORIZATION = ROOT / "research" / "m2-type-i-external-replication-open-v1.json"
RESULT = ROOT / "research" / "m2-type-i-external-replication-result-v1.json"
PREREG = ROOT / "research" / "m2-type-i-external-replication-prereg-v1.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_external_replication_is_frozen_closed_and_consumed() -> None:
    authorization = json.loads(AUTHORIZATION.read_text(encoding="utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))

    assert authorization["authorized"] is False
    assert authorization["one_time_external_replication"] is False
    assert authorization["evaluated_once"] is True
    assert result["replication_consumed"] is True
    assert result["original_holdout_reopened"] is False
    assert authorization["original_holdout_reopened"] is False
    assert authorization["evaluation"]["frozen_result_sha256"] == _sha256(RESULT)
    assert result["preregistration_id"] == prereg["preregistration_id"]
    assert result["dataset"]["dataset_id"] == prereg["replication_dataset"]["dataset_id"]
    assert result["dataset"]["successful_symbols"] == 60
    assert result["dataset"]["coverage_ok"] is True
    assert result["dataset"]["original_45_symbol_overlap"] == 0


def test_external_replication_primary_result_remains_single_confirmed_test() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    primary = result["primary_contrast"]
    multiplicity = result["multiplicity"]
    identity = result["identity"]

    assert primary["exposure_name"] == "full_prz_exit_by_t5"
    assert primary["comparator_name"] == "no_full_exit_by_t5"
    assert primary["exposure"] == {
        "records": 736,
        "endpoint_hits": 257,
        "endpoint_rate": 0.3491847826086957,
    }
    assert primary["comparator"] == {
        "records": 1182,
        "endpoint_hits": 213,
        "endpoint_rate": 0.1802030456852792,
    }
    assert primary["result"] == "confirmed"
    assert primary["newcombe_95_ci"]["lower"] > 0.0
    assert multiplicity == {
        "primary_tests_run": 1,
        "alternate_thresholds_searched": False,
        "alternate_endpoints_searched": False,
        "subgroup_results_can_replace_primary": False,
    }
    assert identity["carney_geometry_changed"] is False
    assert identity["prz_changed"] is False
    assert identity["t5_threshold_fitted_on_replication"] is False
    assert identity["endpoint_fitted_on_replication"] is False
