from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "artifacts" / "ci-research" / "m2-autonomous-research-report.json"
HISTORICAL_PREREG = ROOT / "research" / "m2-type-i-holdout-prereg-v1.json"
OUTPUT = ROOT / "artifacts" / "ci-research" / "m2-source-prz-v6-boundary.json"
EXPECTED_DEFINITION = "m2-source-prz-v6"


def _pattern_count(by_pattern: dict[str, Any], pattern_id: str) -> int:
    value = by_pattern.get(pattern_id)
    if isinstance(value, dict):
        for key in ("records", "count", "n"):
            if key in value:
                return int(value.get(key) or 0)
        return 0
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


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

    require(historical.get("preregistration_id") == "m2-type-i-holdout-v1", "historical preregistration id changed")
    require(
        historical.get("frozen_from_evidence_commit") == "bc90af32963498d174aa2470852ec40330be7853",
        "historical v1 source commit changed",
    )
    require(historical_holdout.get("sealed") is True, "historical v1 holdout must remain sealed")
    require(int(historical_holdout.get("records") or 0) == 355, "historical v1 holdout size changed")

    require(calibration.get("research_definition") == EXPECTED_DEFINITION, "current calibration is not tagged v6")
    require(terminal.get("research_definition") == EXPECTED_DEFINITION, "Terminal-Bar calibration is not tagged v6")
    require(
        terminal.get("prz_basis") == "source_raw_prz_only_fail_closed_otherwise",
        "Terminal-Bar calibration does not enforce Source Raw PRZ semantics",
    )
    require(str(terminal.get("status", "")).endswith("holdout_sealed"), "Terminal-Bar v6 is not sealed")
    require(terminal_holdout.get("sealed") is True, "Terminal-Bar v6 holdout is not sealed")
    require(terminal_holdout.get("outcomes_exposed") is False, "Terminal-Bar v6 holdout outcomes exposed")
    require(int(terminal.get("mature_terminal_events") or 0) > 0, "no mature Source Raw PRZ terminal events")

    require(timing.get("research_definition") == EXPECTED_DEFINITION, "Type-I timing is not tagged v6")
    if timing_holdout:
        require(timing_holdout.get("sealed") is True, "Type-I v6 holdout is not sealed")
        require(timing_holdout.get("outcomes_exposed") is False, "Type-I v6 holdout outcomes exposed")
    require(timing.get("holdout_opened") is not True, "Type-I v6 holdout was opened")
    require(timing.get("policy_frozen") is not True, "Type-I v6 unexpectedly froze policy")

    anti_leakage = calibration.get("anti_leakage") or {}
    require(anti_leakage.get("holdout_outcomes_opened") is False, "v6 reports Holdout opening")
    require(
        anti_leakage.get("source_prz_rebuilt_from_signal_time_geometry") is True,
        "v6 does not report signal-time Source PRZ reconstruction",
    )
    require(
        anti_leakage.get("legacy_ideal_core_used_as_source_prz") is False,
        "v6 reports legacy Ideal Core as Source PRZ",
    )

    train_by_pattern = (terminal.get("train") or {}).get("by_pattern") or {}
    validation_by_pattern = (terminal.get("validation") or {}).get("by_pattern") or {}
    holdout_by_pattern = terminal_holdout.get("by_pattern") or {}
    shark_events = {
        "train": _pattern_count(train_by_pattern, "shark"),
        "validation": _pattern_count(validation_by_pattern, "shark"),
        "holdout": _pattern_count(holdout_by_pattern, "shark"),
    }

    artifact = {
        "schema_version": 1,
        "status": "source_prz_v6_research_boundary_verified",
        "historical_v1": {
            "preregistration_id": historical.get("preregistration_id"),
            "source_commit": historical.get("frozen_from_evidence_commit"),
            "holdout_records_at_preregistration": int(historical_holdout.get("records") or 0),
            "recomputed_with_v6": False,
            "role": "frozen historical confirmatory evidence under original definition",
        },
        "historical_v3": {
            "definition": "m2-source-prz-v3",
            "role": "M2.27 standard-XABCD Source Raw PRZ definition",
            "recomputed_or_relabelled": False,
        },
        "historical_v4": {
            "definition": "m2-source-prz-v4",
            "role": "M2.28 standalone AB=CD Source Raw PRZ definition",
            "recomputed_or_relabelled": False,
        },
        "historical_v5": {
            "definition": "m2-source-prz-v5",
            "role": "M2.29 reconciled 5-0 Volume Two structural Raw PRZ definition",
            "recomputed_or_relabelled": False,
        },
        "current_v6": {
            "research_definition": EXPECTED_DEFINITION,
            "scope": "v5 source schemas plus Shark Volume Three Source Raw PRZ and source-aligned reaction management",
            "dataset_id": runtime.get("dataset_id"),
            "snapshot_cutoff": runtime.get("snapshot_cutoff"),
            "prz_basis": terminal.get("prz_basis"),
            "terminal_status": terminal.get("status"),
            "mature_terminal_events": int(terminal.get("mature_terminal_events") or 0),
            "terminal_holdout_records": int(terminal_holdout.get("records") or 0),
            "train_by_pattern": train_by_pattern,
            "validation_by_pattern": validation_by_pattern,
            "holdout_by_pattern": holdout_by_pattern,
            "shark_terminal_events": shark_events,
            "type_i_status": timing.get("status"),
            "type_i_holdout_records": int(timing_holdout.get("records") or 0),
            "confirmatory_inference_allowed": False,
            "eligible_to_replace_historical_v1": False,
        },
        "shark_policy": {
            "source_raw_prz_members": [
                "0B 0.886-1.13 completion corridor",
                "AB impulse 1.618-2.24 completion corridor",
            ],
            "source_raw_prz_selection": "geometric overlap/alignment of the two published source corridors",
            "zero_b_typical_focus": 1.0,
            "zero_b_stop_reference": 1.13,
            "initial_management_target": "first encountered of 50% BC and Reciprocal AB=CD",
            "wider_5_0_management_level": "61.8% BC",
            "reaction_targets_are_shark_identity_members": False,
            "sample_insufficiency_blocks_source_contract": False,
        },
        "five_zero_policy": {
            "structural_raw_prz_members": ["50% BC retracement", "Reciprocal AB=CD"],
            "volume3_61_8_raw_prz_membership": False,
            "volume3_61_8_identity_membership": False,
            "volume3_label_conflict_preserved": True,
            "production_engine_quarantine_remains": True,
        },
        "policy": {
            "historical_numbers_mutated": False,
            "cross_version_confirmatory_comparison_allowed": False,
            "legacy_ideal_core_fallback_allowed": False,
            "sample_insufficiency_is_valid_result": True,
            "new_untouched_future_dataset_required_for_v6_confirmation": True,
        },
    }

    if failures:
        for failure in failures:
            print(f"[HT-CN M2 SOURCE-PRZ V6 BOUNDARY] FAIL: {failure}")
        return 2

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "[HT-CN M2 SOURCE-PRZ V6 BOUNDARY] PASS: "
        f"terminal={terminal.get('status')} mature={terminal.get('mature_terminal_events')}; "
        f"shark={shark_events}; type_i={timing.get('status')}; confirmatory_inference_allowed=False"
    )
    print("[HT-CN M2 SOURCE-PRZ V6 BOUNDARY] Shark Raw PRZ = overlap of 0B 0.886-1.13 and AB impulse 1.618-2.24 corridors.")
    print("[HT-CN M2 SOURCE-PRZ V6 BOUNDARY] Shark reaction targets remain management-only and outside identity/Raw PRZ.")
    print("[HT-CN M2 SOURCE-PRZ V6 BOUNDARY] historical v1/v3/v4/v5 were not recomputed or relabelled.")
    print(f"[HT-CN M2 SOURCE-PRZ V6 BOUNDARY] report={OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
