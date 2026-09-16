from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "artifacts" / "ci-research" / "m2-autonomous-research-report.json"
HISTORICAL_PREREG = ROOT / "research" / "m2-type-i-holdout-prereg-v1.json"
OUTPUT = ROOT / "artifacts" / "ci-research" / "m2-source-prz-v4-boundary.json"
EXPECTED_DEFINITION = "m2-source-prz-v4"


def main() -> int:
    runtime = json.loads(REPORT.read_text(encoding="utf-8"))
    historical = json.loads(HISTORICAL_PREREG.read_text(encoding="utf-8"))
    calibration = runtime.get("calibration") or {}
    terminal = calibration.get("terminal_bar_calibration") or {}
    timing = calibration.get("type_i_exit_timing") or {}
    terminal_holdout = terminal.get("holdout") or {}
    timing_holdout = timing.get("holdout") or {}
    historical_holdout = historical.get("holdout") or {}
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    # Historical confirmatory evidence is immutable across source-definition upgrades.
    require(historical.get("preregistration_id") == "m2-type-i-holdout-v1", "historical preregistration id changed")
    require(
        historical.get("frozen_from_evidence_commit") == "bc90af32963498d174aa2470852ec40330be7853",
        "historical v1 source commit changed",
    )
    require(historical_holdout.get("sealed") is True, "historical v1 holdout must remain sealed")
    require(int(historical_holdout.get("records") or 0) == 355, "historical v1 holdout size changed")

    # M2.28 v4 is a new descriptive definition: standard XABCD + standalone AB=CD Source Raw PRZ.
    require(calibration.get("research_definition") == EXPECTED_DEFINITION, "current calibration is not tagged v4")
    require(terminal.get("research_definition") == EXPECTED_DEFINITION, "Terminal-Bar calibration is not tagged v4")
    require(
        terminal.get("prz_basis") == "source_raw_prz_only_fail_closed_otherwise",
        "Terminal-Bar calibration does not enforce Source Raw PRZ semantics",
    )
    require(str(terminal.get("status", "")).endswith("holdout_sealed"), "Terminal-Bar v4 is not sealed")
    require(terminal_holdout.get("sealed") is True, "Terminal-Bar v4 holdout is not sealed")
    require(terminal_holdout.get("outcomes_exposed") is False, "Terminal-Bar v4 holdout outcomes exposed")
    require(int(terminal.get("mature_terminal_events") or 0) > 0, "no mature Source Raw PRZ terminal events")

    require(timing.get("research_definition") == EXPECTED_DEFINITION, "Type-I timing is not tagged v4")
    if timing_holdout:
        require(timing_holdout.get("sealed") is True, "Type-I v4 holdout is not sealed")
        require(timing_holdout.get("outcomes_exposed") is False, "Type-I v4 holdout outcomes exposed")
    require(timing.get("holdout_opened") is not True, "Type-I v4 holdout was opened")
    require(timing.get("policy_frozen") is not True, "Type-I v4 unexpectedly froze policy")

    anti_leakage = calibration.get("anti_leakage") or {}
    require(anti_leakage.get("holdout_outcomes_opened") is False, "v4 reports Holdout opening")
    require(
        anti_leakage.get("source_prz_rebuilt_from_signal_time_geometry") is True,
        "v4 does not report signal-time Source PRZ reconstruction",
    )
    require(
        anti_leakage.get("legacy_ideal_core_used_as_source_prz") is False,
        "v4 reports legacy Ideal Core as Source PRZ",
    )

    artifact = {
        "schema_version": 1,
        "status": "source_prz_v4_research_boundary_verified",
        "historical_v1": {
            "preregistration_id": historical.get("preregistration_id"),
            "source_commit": historical.get("frozen_from_evidence_commit"),
            "holdout_records_at_preregistration": int(historical_holdout.get("records") or 0),
            "recomputed_with_v4": False,
            "role": "frozen historical confirmatory evidence under original definition",
        },
        "historical_v3": {
            "definition": "m2-source-prz-v3",
            "role": "M2.27 standard-XABCD-only Source Raw PRZ calibration definition",
            "recomputed_or_relabelled": False,
            "confirmatory_inference_allowed": False,
        },
        "current_v4": {
            "research_definition": EXPECTED_DEFINITION,
            "scope": "standard XABCD plus standalone AB=CD Source Raw PRZ",
            "dataset_id": runtime.get("dataset_id"),
            "snapshot_cutoff": runtime.get("snapshot_cutoff"),
            "prz_basis": terminal.get("prz_basis"),
            "terminal_status": terminal.get("status"),
            "mature_terminal_events": int(terminal.get("mature_terminal_events") or 0),
            "terminal_holdout_records": int(terminal_holdout.get("records") or 0),
            "type_i_status": timing.get("status"),
            "type_i_holdout_records": int(timing_holdout.get("records") or 0),
            "confirmatory_inference_allowed": False,
            "eligible_to_replace_historical_v1": False,
        },
        "policy": {
            "historical_numbers_mutated": False,
            "cross_version_confirmatory_comparison_allowed": False,
            "legacy_ideal_core_fallback_allowed": False,
            "abcd_source_prz_requires_signal_time_abc": True,
            "bc_layering_is_raw_prz_or_identity": False,
            "sample_insufficiency_is_valid_result": True,
            "new_untouched_future_dataset_required_for_v4_confirmation": True,
        },
    }

    if failures:
        for failure in failures:
            print(f"[HT-CN M2 SOURCE-PRZ V4 BOUNDARY] FAIL: {failure}")
        return 2

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "[HT-CN M2 SOURCE-PRZ V4 BOUNDARY] PASS: "
        f"terminal={terminal.get('status')} mature={terminal.get('mature_terminal_events')}; "
        f"type_i={timing.get('status')}; confirmatory_inference_allowed=False"
    )
    print("[HT-CN M2 SOURCE-PRZ V4 BOUNDARY] standalone AB=CD uses signal-time A/B/C Source Raw PRZ.")
    print("[HT-CN M2 SOURCE-PRZ V4 BOUNDARY] BC layering remains execution-only; legacy Ideal Core rejected.")
    print("[HT-CN M2 SOURCE-PRZ V4 BOUNDARY] historical v1/v3 were not recomputed or reopened.")
    print(f"[HT-CN M2 SOURCE-PRZ V4 BOUNDARY] report={OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
