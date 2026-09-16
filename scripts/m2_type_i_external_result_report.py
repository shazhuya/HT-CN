from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "research" / "m2-type-i-external-replication-prereg-v1.json"
AUTHORIZATION = ROOT / "research" / "m2-type-i-external-replication-open-v1.json"
RESULT = ROOT / "research" / "m2-type-i-external-replication-result-v1.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    authorization = json.loads(AUTHORIZATION.read_text(encoding="utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))

    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    prereg_id = str(prereg.get("preregistration_id"))
    prereg_dataset = prereg.get("replication_dataset") or {}
    prereg_contrast = prereg.get("primary_contrast") or {}
    prereg_test = prereg.get("confirmatory_test") or {}
    evaluation = authorization.get("evaluation") or {}
    dataset = result.get("dataset") or {}
    primary = result.get("primary_contrast") or {}
    multiplicity = result.get("multiplicity") or {}
    identity = result.get("identity") or {}

    require(authorization.get("authorized") is False, "external replication authorization must be closed")
    require(
        authorization.get("one_time_external_replication") is False,
        "one_time_external_replication must be false after evaluation",
    )
    require(authorization.get("evaluated_once") is True, "evaluated_once must be true")
    require(authorization.get("preregistration_id") == prereg_id, "authorization/preregistration id mismatch")
    require(result.get("preregistration_id") == prereg_id, "result/preregistration id mismatch")
    require(
        result.get("status") == "external_type_i_replication_evaluated_once",
        "frozen external result status mismatch",
    )
    require(result.get("replication_consumed") is True, "external replication must be marked consumed")
    require(result.get("original_holdout_reopened") is False, "original 45-symbol Holdout must remain closed")
    require(authorization.get("original_holdout_reopened") is False, "authorization must record original Holdout closed")

    require(
        evaluation.get("frozen_result_path") == str(RESULT.relative_to(ROOT)),
        "authorization points to the wrong frozen external result path",
    )
    require(
        evaluation.get("frozen_result_sha256") == _sha256(RESULT),
        "frozen external result SHA256 does not match authorization",
    )
    require(
        evaluation.get("source_evaluation_report_sha256")
        == (result.get("source") or {}).get("evaluation_report_sha256"),
        "source evaluation report hash mismatch",
    )
    require(
        evaluation.get("artifact_sha256") == (result.get("source") or {}).get("artifact_sha256"),
        "artifact hash mismatch",
    )
    require(
        evaluation.get("snapshot_manifest_sha256")
        == (result.get("source") or {}).get("snapshot_manifest_sha256"),
        "snapshot manifest hash mismatch",
    )

    require(dataset.get("dataset_id") == prereg_dataset.get("dataset_id"), "dataset id mismatch")
    require(dataset.get("snapshot_cutoff") == prereg_dataset.get("snapshot_cutoff"), "snapshot cutoff mismatch")
    require(int(dataset.get("requested_symbols") or 0) == 60, "requested symbol count must remain 60")
    require(int(dataset.get("successful_symbols") or 0) == 60, "frozen run must retain 60 successful symbols")
    require(
        int(dataset.get("successful_symbols") or 0) >= int(prereg_dataset.get("minimum_successful_symbols") or 0),
        "provider coverage gate no longer passes",
    )
    require(dataset.get("coverage_ok") is True, "coverage_ok must be true")
    require(int(dataset.get("original_45_symbol_overlap") or -1) == 0, "replication set must remain disjoint")

    exposure_name = (prereg_contrast.get("exposure") or {}).get("name")
    comparator_name = (prereg_contrast.get("comparator") or {}).get("name")
    require(primary.get("exposure_name") == exposure_name, "exposure group differs from preregistration")
    require(primary.get("comparator_name") == comparator_name, "comparator group differs from preregistration")
    require(
        int(primary.get("minimum_records_per_group") or 0)
        == int(prereg_test.get("minimum_records_per_group") or -1),
        "sample floor differs from preregistration",
    )
    require(primary.get("sample_floor_ok") is True, "sample floor must pass in frozen result")
    require(primary.get("result") == evaluation.get("primary_result"), "authorization/result primary outcome mismatch")
    require(primary.get("result") == "confirmed", "frozen primary result must remain confirmed")
    interval = primary.get("newcombe_95_ci") or {}
    require(float(interval.get("lower") or 0.0) > 0.0, "confirmed result requires positive 95% CI lower bound")

    require(multiplicity.get("primary_tests_run") == 1, "exactly one primary replication test must be recorded")
    require(multiplicity.get("alternate_thresholds_searched") is False, "alternate thresholds must remain unsearched")
    require(multiplicity.get("alternate_endpoints_searched") is False, "alternate endpoints must remain unsearched")
    require(multiplicity.get("subgroup_results_can_replace_primary") is False, "subgroups cannot replace primary test")
    require(identity.get("carney_geometry_changed") is False, "Carney geometry must remain unchanged")
    require(identity.get("prz_changed") is False, "PRZ must remain unchanged")
    require(identity.get("t5_threshold_fitted_on_replication") is False, "T+5 threshold must not be fitted on replication")
    require(identity.get("endpoint_fitted_on_replication") is False, "endpoint must not be fitted on replication")

    if failures:
        for failure in failures:
            print(f"[HT-CN M2 EXT-RESULT] FAIL: {failure}")
        return 2

    exposure = primary.get("exposure") or {}
    comparator = primary.get("comparator") or {}
    concentration = result.get("concentration") or {}
    print(
        "[HT-CN M2 EXT-RESULT] status=verified_closed, "
        f"prereg={prereg_id}, result={primary.get('result')}, coverage={dataset.get('successful_symbols')}/60"
    )
    print(
        "[HT-CN M2 EXT-RESULT] primary "
        f"{primary.get('exposure_name')}: n={exposure.get('records')}, hits={exposure.get('endpoint_hits')}, "
        f"rate={exposure.get('endpoint_rate')}; {primary.get('comparator_name')}: "
        f"n={comparator.get('records')}, hits={comparator.get('endpoint_hits')}, rate={comparator.get('endpoint_rate')}"
    )
    print(
        "[HT-CN M2 EXT-RESULT] effect="
        f"{primary.get('absolute_rate_difference')}, CI95=[{interval.get('lower')}, {interval.get('upper')}], "
        f"eligible_symbols={concentration.get('eligible_symbols')}, largest_symbol_share={concentration.get('largest_symbol_share')}"
    )
    print("[HT-CN M2 EXT-RESULT] REPLICATION CONSUMED/CLOSED; no external outcomes recomputed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
