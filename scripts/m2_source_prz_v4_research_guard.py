from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "artifacts" / "ci-research" / "m2-autonomous-research-report.json"
HISTORICAL_PREREG = ROOT / "research" / "m2-type-i-holdout-prereg-v1.json"
OUTPUT = ROOT / "artifacts" / "ci-research" / "m2-source-prz-v4-boundary.json"
EXPECTED_DEFINITION = "m2-source-prz-v4"
V3_RESEARCH_HEAD = "5b1ba9bb9bca639a248a74a1b9a683b09e4a6622"
V3_MERGED_MAIN = "612c0dc01ecbbadfe763bbe9a78c9acd9cee5014"


def _pattern_count(summary: dict, pattern_id: str) -> int:
    return int((summary.get("by_pattern") or {}).get(pattern_id, 0))


def main() -> int:
    runtime = json.loads(REPORT.read_text(encoding="utf-8"))
    historical = json.loads(HISTORICAL_PREREG.read_text(encoding="utf-8"))

    calibration = runtime.get("calibration") or {}
    terminal = calibration.get("terminal_bar_calibration") or {}
    timing = calibration.get("type_i_exit_timing") or {}
    terminal_holdout = terminal.get("holdout") or {}
    timing_holdout = timing.get("holdout") or {}
    historical_holdout = historical.get("holdout") or {}
    train = terminal.get("train") or {}
    validation = terminal.get("validation") or {}

    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    # Historical confirmatory result remains immutable and is never reinterpreted under v4.
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

    # v4 is a new research definition because standalone AB=CD joins source-Raw-PRZ eligibility.
    require(
        calibration.get("research_definition") == EXPECTED_DEFINITION,
        "current calibration is not tagged with the v4 source-PRZ research definition",
    )
    require(
        terminal.get("research_definition") == EXPECTED_DEFINITION,
        "Terminal-Bar calibration is not tagged with the v4 source-PRZ definition",
    )
    require(
        terminal.get("prz_basis") == "source_raw_prz_only_fail_closed_otherwise",
        "Terminal-Bar calibration does not enforce source Raw PRZ fail-closed semantics",
    )
    require(
        str(terminal.get("status", "")).endswith("holdout_sealed"),
        "Terminal-Bar v4 research is not in a sealed state",
    )
    require(terminal_holdout.get("sealed") is True, "Terminal-Bar v4 holdout is not sealed")
    require(
        terminal_holdout.get("outcomes_exposed") is False,
        "Terminal-Bar v4 holdout outcomes were exposed",
    )
    require(
        int(terminal.get("mature_terminal_events") or 0) > 0,
        "no mature source-Raw-PRZ Terminal-Bar events were observed",
    )

    abcd_visible = (
        _pattern_count(train, "abcd")
        + _pattern_count(validation, "abcd")
        + _pattern_count(terminal_holdout, "abcd")
    )
    require(
        abcd_visible > 0,
        "v4 real-A-share research produced no standalone AB=CD Source-T-Bar events",
    )

    # Type-I may remain non-robust/sample-insufficient. Scientific non-readiness is valid;
    # reopening Holdout or rescuing with legacy Ideal Core is not.
    require(
        timing.get("research_definition") == EXPECTED_DEFINITION,
        "Type-I timing output is not tagged with the v4 research definition",
    )
    if timing_holdout:
        require(timing_holdout.get("sealed") is True, "Type-I v4 holdout is not sealed")
        require(
            timing_holdout.get("outcomes_exposed") is False,
            "Type-I v4 holdout outcomes were exposed",
        )
    require(timing.get("holdout_opened") is not True, "Type-I v4 holdout was opened")
    require(timing.get("policy_frozen") is not True, "Type-I v4 research unexpectedly froze policy")

    anti_leakage = calibration.get("anti_leakage") or {}
    require(
        anti_leakage.get("holdout_outcomes_opened") is False,
        "v4 anti-leakage metadata reports Holdout opening",
    )
    require(
        anti_leakage.get("source_prz_rebuilt_from_signal_time_geometry") is True,
        "v4 does not report signal-time Source PRZ reconstruction",
    )
    require(
        anti_leakage.get("legacy_ideal_core_used_as_source_prz") is False,
        "v4 reports legacy Ideal Core being used as Source PRZ",
    )

    artifact = {
        "schema_version": 1,
        "status": "source_prz_v4_research_boundary_verified",
        "historical_v1": {
            "preregistration_id": historical.get("preregistration_id"),
            "source_commit": historical.get("frozen_from_evidence_commit"),
            "holdout_records_at_preregistration": int(historical_holdout.get("records") or 0),
            "recomputed_with_v4": False,
            "role": "frozen historical confirmatory evidence under its original research definition",
        },
        "m2_27_v3": {
            "research_definition": "m2-source-prz-v3",
            "research_head": V3_RESEARCH_HEAD,
            "merged_main_commit": V3_MERGED_MAIN,
            "role": "closed historical source-Raw-PRZ calibration for standard XABCD only",
            "recomputed_as_v3": False,
            "promoted_or_reinterpreted_by_v4": False,
        },
        "current_v4": {
            "research_definition": EXPECTED_DEFINITION,
            "dataset_id": runtime.get("dataset_id"),
            "snapshot_cutoff": runtime.get("snapshot_cutoff"),
            "prz_basis": terminal.get("prz_basis"),
            "terminal_status": terminal.get("status"),
            "mature_terminal_events": int(terminal.get("mature_terminal_events") or 0),
            "visible_abcd_terminal_events": int(abcd_visible),
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
            "abcd_bc_layering_in_source_raw_prz": False,
            "sample_insufficiency_may_be_reported_without_failing_closed_semantics": True,
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
        f"visible_abcd={abcd_visible}; type_i={timing.get('status')}; "
        "confirmatory_inference_allowed=False"
    )
    print("[HT-CN M2 SOURCE-PRZ V4 BOUNDARY] legacy Ideal Core is not accepted as Source PRZ.")
    print("[HT-CN M2 SOURCE-PRZ V4 BOUNDARY] v3 and historical v1 remain closed historical definitions.")
    print(f"[HT-CN M2 SOURCE-PRZ V4 BOUNDARY] report={OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
