from __future__ import annotations

import json
from pathlib import Path

from htcn.research.type_i_holdout_prereg import build_type_i_holdout_preregistration


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "artifacts" / "ci-research" / "m2-autonomous-research-report.json"
REGISTRY = ROOT / "research" / "m2-type-i-holdout-prereg-v1.json"
OUTPUT = ROOT / "artifacts" / "ci-research" / "m2-type-i-holdout-preregistration.json"


def _frozen_projection(payload: dict) -> dict:
    """Fields that must match the committed repository pre-registration exactly."""
    contrast = payload.get("primary_contrast") or {}
    test = payload.get("confirmatory_test") or {}
    holdout = payload.get("holdout") or {}
    dataset = payload.get("dataset") or {}
    return {
        "preregistration_id": payload.get("preregistration_id"),
        "dataset_id": dataset.get("dataset_id"),
        "snapshot_cutoff": dataset.get("snapshot_cutoff"),
        "price_mode": dataset.get("price_mode"),
        "source_commit": payload.get("source_commit"),
        "selected_hypothesis": payload.get("selected_hypothesis"),
        "exposure": (contrast.get("exposure") or {}).get("name"),
        "comparator": (contrast.get("comparator") or {}).get("name"),
        "endpoint": contrast.get("endpoint"),
        "effect_measure": contrast.get("effect_measure"),
        "method": test.get("method"),
        "confidence_level": test.get("confidence_level"),
        "z": test.get("z"),
        "minimum_records_per_group": test.get("minimum_records_per_group"),
        "success_criterion": test.get("success_criterion"),
        "primary_tests": (payload.get("multiplicity") or {}).get("primary_tests"),
        "holdout_records": holdout.get("records"),
        "holdout_sealed": holdout.get("sealed"),
        "holdout_outcomes_exposed": holdout.get("outcomes_exposed"),
        "holdout_open_authorized": payload.get("holdout_open_authorized"),
        "policy_frozen": payload.get("policy_frozen"),
    }


def main() -> int:
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    frozen = json.loads(REGISTRY.read_text(encoding="utf-8"))
    calibration = payload.get("calibration") or {}
    timing = calibration.get("type_i_exit_timing") or {}
    prereg = build_type_i_holdout_preregistration(
        timing,
        dataset_id=payload.get("dataset_id"),
        snapshot_cutoff=payload.get("snapshot_cutoff"),
        source_commit=frozen.get("frozen_from_evidence_commit"),
        minimum_holdout_group=int((frozen.get("confirmatory_test") or {}).get("minimum_records_per_group", 20)),
    )

    expected = {
        "preregistration_id": frozen.get("preregistration_id"),
        "dataset_id": (frozen.get("dataset") or {}).get("dataset_id"),
        "snapshot_cutoff": (frozen.get("dataset") or {}).get("snapshot_cutoff"),
        "price_mode": (frozen.get("dataset") or {}).get("price_mode"),
        "source_commit": frozen.get("frozen_from_evidence_commit"),
        "selected_hypothesis": frozen.get("selected_hypothesis"),
        "exposure": ((frozen.get("primary_contrast") or {}).get("exposure") or {}).get("name"),
        "comparator": ((frozen.get("primary_contrast") or {}).get("comparator") or {}).get("name"),
        "endpoint": (frozen.get("primary_contrast") or {}).get("endpoint"),
        "effect_measure": (frozen.get("primary_contrast") or {}).get("effect_measure"),
        "method": (frozen.get("confirmatory_test") or {}).get("method"),
        "confidence_level": (frozen.get("confirmatory_test") or {}).get("confidence_level"),
        "z": (frozen.get("confirmatory_test") or {}).get("z"),
        "minimum_records_per_group": (frozen.get("confirmatory_test") or {}).get("minimum_records_per_group"),
        "success_criterion": (frozen.get("confirmatory_test") or {}).get("success_criterion"),
        "primary_tests": (frozen.get("multiplicity") or {}).get("primary_tests"),
        "holdout_records": (frozen.get("holdout") or {}).get("records"),
        "holdout_sealed": (frozen.get("holdout") or {}).get("sealed"),
        "holdout_outcomes_exposed": (frozen.get("holdout") or {}).get("outcomes_exposed"),
        "holdout_open_authorized": frozen.get("holdout_open_authorized"),
        "policy_frozen": frozen.get("policy_frozen"),
    }
    actual = _frozen_projection(prereg)
    if actual != expected:
        print("[HT-CN M2 HOLDOUT PREREG] FAIL: runtime plan does not match committed pre-registration.")
        print(json.dumps({"expected": expected, "actual": actual}, ensure_ascii=False, indent=2))
        return 2

    artifact = {
        **prereg,
        "registry_path": str(REGISTRY.relative_to(ROOT)),
        "registry_match": True,
    }
    OUTPUT.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "[HT-CN M2 HOLDOUT PREREG] "
        f"status={prereg.get('status')}, selected={prereg.get('selected_hypothesis') or 'none'}, "
        f"holdout={(prereg.get('holdout') or {}).get('records', 0)} SEALED"
    )
    contrast = prereg.get("primary_contrast") or {}
    exposure = (contrast.get("exposure") or {}).get("name")
    comparator = (contrast.get("comparator") or {}).get("name")
    print(
        "[HT-CN M2 HOLDOUT PREREG] primary="
        f"{exposure} vs {comparator}; endpoint=T+6..T+20 first T2"
    )
    test = prereg.get("confirmatory_test") or {}
    print(
        "[HT-CN M2 HOLDOUT PREREG] criterion="
        f"{test.get('success_criterion')}; min_group={test.get('minimum_records_per_group')}"
    )
    print(f"[HT-CN M2 HOLDOUT PREREG] registry_match=True path={REGISTRY.relative_to(ROOT)}")
    print("[HT-CN M2 HOLDOUT PREREG] HOLDOUT REMAINS SEALED")
    print(f"[HT-CN M2 HOLDOUT PREREG] report={OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
