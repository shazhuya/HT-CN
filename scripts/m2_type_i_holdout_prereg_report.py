from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "research" / "m2-type-i-holdout-prereg-v1.json"
AUTHORIZATION = ROOT / "research" / "m2-type-i-holdout-open-v1.json"


EXPECTED_PREREGISTRATION_ID = "m2-type-i-holdout-v1"
EXPECTED_DATASET_ID = "a-share-research-v2-45"
EXPECTED_CUTOFF = "2026-09-15"
EXPECTED_SOURCE_COMMIT = "bc90af32963498d174aa2470852ec40330be7853"
EXPECTED_HOLDOUT_RECORDS = 355
EXPECTED_HYPOTHESIS = "full_prz_exit_by_t5"
EXPECTED_COMPARATOR = "no_full_exit_by_t5"


def main() -> int:
    """Verify historical v1 preregistration without rebuilding it from the current engine.

    M2.26 changes source-fidelity/identity semantics, so current runtime sample membership is a
    different research definition. Reconstructing the consumed v1 preregistration from current
    calibration would be scientifically invalid. This verifier therefore reads only the frozen
    historical registry and its closed authorization record.
    """
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    authorization = json.loads(AUTHORIZATION.read_text(encoding="utf-8"))

    dataset = prereg.get("dataset") or {}
    contrast = prereg.get("primary_contrast") or {}
    exposure = contrast.get("exposure") or {}
    comparator = contrast.get("comparator") or {}
    test = prereg.get("confirmatory_test") or {}
    multiplicity = prereg.get("multiplicity") or {}
    holdout = prereg.get("holdout") or {}

    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    require(
        prereg.get("preregistration_id") == EXPECTED_PREREGISTRATION_ID,
        "historical preregistration id changed",
    )
    require(dataset.get("dataset_id") == EXPECTED_DATASET_ID, "historical dataset id changed")
    require(dataset.get("snapshot_cutoff") == EXPECTED_CUTOFF, "historical cutoff changed")
    require(dataset.get("price_mode") == "qfq", "historical price mode changed")
    require(
        prereg.get("frozen_from_evidence_commit") == EXPECTED_SOURCE_COMMIT,
        "historical source evidence commit changed",
    )
    require(
        prereg.get("selected_hypothesis") == EXPECTED_HYPOTHESIS,
        "historical selected hypothesis changed",
    )
    require(exposure.get("name") == EXPECTED_HYPOTHESIS, "historical exposure definition changed")
    require(comparator.get("name") == EXPECTED_COMPARATOR, "historical comparator definition changed")
    require(
        contrast.get("endpoint") == "First T2 hit from T+6 through T+20.",
        "historical endpoint changed",
    )
    require(
        int(test.get("minimum_records_per_group") or 0) == 20,
        "historical minimum group size changed",
    )
    require(
        float(test.get("z") or 0.0) == 1.959963984540054,
        "historical Newcombe z value changed",
    )
    require(
        multiplicity.get("primary_tests") == 1,
        "historical preregistration must contain exactly one primary test",
    )
    require(
        multiplicity.get("post_hoc_threshold_search_allowed") is False,
        "historical post-hoc threshold search must remain forbidden",
    )
    require(
        multiplicity.get("alternate_endpoint_substitution_allowed") is False,
        "historical endpoint substitution must remain forbidden",
    )
    require(holdout.get("sealed") is True, "historical v1 Holdout must remain sealed")
    require(
        int(holdout.get("records") or 0) == EXPECTED_HOLDOUT_RECORDS,
        "historical v1 preregistered Holdout size must remain 355",
    )
    require(
        holdout.get("outcomes_exposed") is False,
        "historical preregistration must preserve the pre-open outcomes_exposed=false state",
    )
    require(
        authorization.get("preregistration_id") == EXPECTED_PREREGISTRATION_ID,
        "closed authorization no longer points to historical preregistration",
    )
    require(
        authorization.get("frozen_evidence_commit") == EXPECTED_SOURCE_COMMIT,
        "closed authorization evidence commit changed",
    )
    require(authorization.get("authorized") is False, "historical Holdout authorization must be closed")
    require(
        authorization.get("one_time_holdout_open") is False,
        "historical one-time Holdout must remain closed",
    )
    require(authorization.get("evaluated_once") is True, "historical Holdout must remain marked consumed")

    if failures:
        for failure in failures:
            print(f"[HT-CN M2 HOLDOUT PREREG V1] FAIL: {failure}")
        return 2

    print(
        "[HT-CN M2 HOLDOUT PREREG V1] PASS: "
        f"prereg={EXPECTED_PREREGISTRATION_ID}, dataset={EXPECTED_DATASET_ID}, "
        f"holdout={EXPECTED_HOLDOUT_RECORDS}, source_commit={EXPECTED_SOURCE_COMMIT[:12]}..."
    )
    print(
        "[HT-CN M2 HOLDOUT PREREG V1] STATIC HISTORICAL INTEGRITY ONLY; "
        "current runtime was not used to rebuild, reopen or reinterpret v1."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
