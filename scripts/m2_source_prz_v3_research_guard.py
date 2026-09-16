from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "artifacts" / "ci-research" / "m2-autonomous-research-report.json"
HISTORICAL_PREREG = ROOT / "research" / "m2-type-i-holdout-prereg-v1.json"
OUTPUT = ROOT / "artifacts" / "ci-research" / "m2-source-prz-v3-boundary.json"
EXPECTED_DEFINITION = "m2-source-prz-v3"


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

    # Historical v1 stays immutable.  It was created under the older research definition and
    # must never be rebuilt with M2.27 Source-PRZ semantics.
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
    require(int(historical_holdout.get("records") or 0) == 355, "historical v1 holdout size changed")

    # Current M2.27 research must identify itself as a new definition and use the actual Raw PRZ.
    require(
        calibration.get("research_definition") == EXPECTED_DEFINITION,
        "current calibration is not tagged with the M2.27 source-PRZ research definition",
    )
    require(
        terminal.get("research_definition") == EXPECTED_DEFINITION,
        "Terminal-Bar calibration is not tagged with the M2.27 source-PRZ definition",
    )
    require(
        terminal.get("prz_basis") == "source_raw_prz_only_fail_closed_otherwise",
        "Terminal-Bar calibration does not enforce source Raw PRZ fail-closed semantics",
    )
    require(
        str(terminal.get("status", "")).endswith("holdout_sealed"),
        "Terminal-Bar v3 research is not in a sealed state",
    )
    require(terminal_holdout.get("sealed") is True, "Terminal-Bar v3 holdout is not sealed")
    require(
        terminal_holdout.get("outcomes_exposed") is False,
        "Terminal-Bar v3 holdout outcomes were exposed",
    )
    require(
        int(terminal.get("mature_terminal_events") or 0) > 0,
        "no mature source-Raw-PRZ Terminal-Bar events were observed",
    )

    status_counts = terminal.get("terminal_bar_status_counts") or {}
    require(
        int(status_counts.get("source_prz_unresolved", 0)) >= 0,
        "invalid unresolved-source-PRZ status count",
    )

    # Type-I v3 may be sample-insufficient at this stage.  That is a valid scientific result;
    # it must never be rescued by reopening Holdout or falling back to legacy ideal-core PRZ.
    require(
        timing.get("research_definition") == EXPECTED_DEFINITION,
        "Type-I timing output is not tagged with the v3 research definition",
    )
    if timing_holdout:
        require(timing_holdout.get("sealed") is True, "Type-I v3 holdout is not sealed")
        require(
            timing_holdout.get("outcomes_exposed") is False,
            "Type-I v3 holdout outcomes were exposed",
        )
    require(timing.get("holdout_opened") is not True, "Type-I v3 holdout was opened")
    require(timing.get("policy_frozen") is not True, "Type-I v3 research unexpectedly froze policy")

    anti_leakage = calibration.get("anti_leakage") or {}
    require(
        anti_leakage.get("holdout_outcomes_opened") is False,
        "v3 anti-leakage metadata reports Holdout opening",
    )
    require(
        anti_leakage.get("source_prz_rebuilt_from_signal_time_geometry") is True,
        "v3 does not report signal-time Source PRZ reconstruction",
    )
    require(
        anti_leakage.get("legacy_ideal_core_used_as_source_prz") is False,
        "v3 reports legacy Ideal Core being used as Source PRZ",
    )

    artifact = {
        "schema_version": 1,
        "status": "source_prz_v3_research_boundary_verified",
        "historical_v1": {
            "preregistration_id": historical.get("preregistration_id"),
            "source_commit": historical.get("frozen_from_evidence_commit"),
            "holdout_records_at_preregistration": int(historical_holdout.get("records") or 0),
            "recomputed_with_v3": False,
            "role": "frozen historical confirmatory evidence under its original research definition",
        },
        "m2_26_v2": {
            "role": "historical calibration-only definition; retained for reproducibility",
            "prz_semantics": "legacy PotentialReversalZone.price_low/high aliases (Ideal Core after semantic repair)",
            "promoted_to_source_raw_prz": False,
            "confirmatory_inference_allowed": False,
        },
        "current_v3": {
            "research_definition": EXPECTED_DEFINITION,
            "dataset_id": runtime.get("dataset_id"),
            "snapshot_cutoff": runtime.get("snapshot_cutoff"),
            "prz_basis": terminal.get("prz_basis"),
            "terminal_status": terminal.get("status"),
            "mature_terminal_events": int(terminal.get("mature_terminal_events") or 0),
            "terminal_holdout_records": int(terminal_holdout.get("records") or 0),
            "type_i_status": timing.get("status"),
            "type_i_holdout_records": int(timing_holdout.get("records") or 0),
            "holdout_outcomes_exposed": False,
            "confirmatory_inference_allowed": False,
            "eligible_to_replace_historical_v1": False,
        },
        "policy": {
            "historical_numbers_mutated": False,
            "cross_version_confirmatory_comparison_allowed": False,
            "legacy_ideal_core_fallback_allowed": False,
            "sample_insufficiency_may_be_reported_without_failing_closed_semantics": True,
            "new_untouched_future_dataset_required_for_v3_confirmation": True,
        },
    }

    if failures:
        for failure in failures:
            print(f"[HT-CN M2 SOURCE-PRZ V3 BOUNDARY] FAIL: {failure}")
        return 2

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "[HT-CN M2 SOURCE-PRZ V3 BOUNDARY] PASS: "
        f"terminal={terminal.get('status')} mature={terminal.get('mature_terminal_events')}; "
        f"type_i={timing.get('status')}; confirmatory_inference_allowed=False"
    )
    print("[HT-CN M2 SOURCE-PRZ V3 BOUNDARY] legacy Ideal Core is not accepted as Source PRZ.")
    print("[HT-CN M2 SOURCE-PRZ V3 BOUNDARY] historical v1 was not recomputed or reopened.")
    print(f"[HT-CN M2 SOURCE-PRZ V3 BOUNDARY] report={OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
