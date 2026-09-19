from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "artifacts" / "ci-research" / "m2-autonomous-research-report.json"
HISTORICAL_PREREG = ROOT / "research" / "m2-type-i-holdout-prereg-v1.json"
OUTPUT = ROOT / "artifacts" / "ci-research" / "m2-source-fidelity-v2-boundary.json"


def main() -> int:
    runtime = json.loads(REPORT.read_text(encoding="utf-8"))
    historical = json.loads(HISTORICAL_PREREG.read_text(encoding="utf-8"))

    timing = ((runtime.get("calibration") or {}).get("type_i_exit_timing") or {})
    current_holdout = timing.get("holdout") or {}
    historical_holdout = historical.get("holdout") or {}

    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    historical_records = int(historical_holdout.get("records") or 0)
    current_records = int(current_holdout.get("records") or 0)

    # Historical v1 is immutable and was already consumed by its one-time evaluation.
    # This guard deliberately does NOT rebuild that pre-registration from the current engine.
    require(
        historical.get("preregistration_id") == "m2-type-i-holdout-v1",
        "historical preregistration id changed",
    )
    require(
        historical.get("frozen_from_evidence_commit")
        == "bc90af32963498d174aa2470852ec40330be7853",
        "historical v1 source commit changed",
    )
    require(historical_holdout.get("sealed") is True, "historical v1 holdout must remain sealed")
    require(
        historical_holdout.get("outcomes_exposed") is False,
        "historical preregistration must still describe outcomes as unexposed at freeze time",
    )
    require(historical_records == 355, "historical v1 preregistered holdout size must remain 355")

    # Current source-fidelity runtime is a new research definition. Its Holdout may have a
    # different membership/count, but its outcomes must stay sealed and may not be used to
    # reinterpret or replace the already-consumed historical v1 confirmatory result.
    require(
        timing.get("status") == "type_i_exit_timing_evidence_holdout_sealed",
        "current source-fidelity Type-I timing evidence is not in the sealed state",
    )
    require(current_holdout.get("sealed") is True, "current source-fidelity holdout is not sealed")
    require(
        current_holdout.get("outcomes_exposed") is False,
        "current source-fidelity holdout outcomes were exposed",
    )
    require(timing.get("holdout_opened") is False, "current source-fidelity holdout was opened")
    require(timing.get("policy_frozen") is False, "current source-fidelity research must not freeze policy")
    require(current_records > 0, "current source-fidelity sealed sample is empty")

    anti_leakage = timing.get("anti_leakage") or {}
    require(
        anti_leakage.get("holdout_outcomes_opened") is False,
        "current source-fidelity anti-leakage metadata reports Holdout opening",
    )

    artifact = {
        "schema_version": 1,
        "status": "source_fidelity_v2_research_boundary_verified",
        "historical_v1": {
            "preregistration_id": historical.get("preregistration_id"),
            "source_commit": historical.get("frozen_from_evidence_commit"),
            "holdout_records_at_preregistration": historical_records,
            "one_time_result_recomputed": False,
            "role": "frozen historical confirmatory evidence; integrity verified by the dedicated frozen-result scripts",
        },
        "current_source_fidelity_v2": {
            "dataset_id": runtime.get("dataset_id"),
            "snapshot_cutoff": runtime.get("snapshot_cutoff"),
            "engine_definition": "M2.26 source-fidelity runtime",
            "sealed_holdout_records": current_records,
            "holdout_sealed": True,
            "holdout_outcomes_exposed": False,
            "confirmatory_inference_allowed": False,
            "eligible_to_replace_historical_v1": False,
            "sample_membership_changed_from_v1": current_records != historical_records,
            "role": "new-definition calibration/research evidence only; requires a separately preregistered untouched future dataset before confirmatory inference",
        },
        "policy": {
            "historical_v1_recomputed": False,
            "historical_v1_numbers_mutated": False,
            "cross_version_confirmatory_comparison_allowed": False,
            "optional_stopping_allowed": False,
            "new_untouched_dataset_required_for_v2_confirmation": True,
        },
    }

    if failures:
        for failure in failures:
            print(f"[HT-CN M2 SOURCE-FIDELITY BOUNDARY] FAIL: {failure}")
        return 2

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "[HT-CN M2 SOURCE-FIDELITY BOUNDARY] PASS: "
        f"historical_v1={historical_records} frozen/consumed; "
        f"current_v2={current_records} sealed; confirmatory_inference_allowed=False"
    )
    if current_records != historical_records:
        print(
            "[HT-CN M2 SOURCE-FIDELITY BOUNDARY] sample definition changed: "
            f"v1={historical_records}, v2={current_records}; versions MUST NOT be treated as the same confirmatory study."
        )
    print("[HT-CN M2 SOURCE-FIDELITY BOUNDARY] historical v1 was not recomputed or reopened.")
    print(f"[HT-CN M2 SOURCE-FIDELITY BOUNDARY] report={OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
