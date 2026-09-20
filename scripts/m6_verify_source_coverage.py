from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COVERAGE_PATH = ROOT / "governance" / "SOURCE_COVERAGE.json"
DECISION_INDEX_PATH = ROOT / "governance" / "DECISION_INDEX.json"
SOURCE_STATUS_PATH = ROOT / "research" / "source-fidelity-status-v1.json"

EXPECTED_IDS = {
    "SOURCE_RAW_PRZ",
    "ABCD",
    "GARTLEY",
    "BAT",
    "CRAB",
    "DEEP_CRAB",
    "BUTTERFLY",
    "SHARK",
    "FIVE_ZERO",
    "ALTERNATE_BAT",
    "TERMINAL_PRICE_BAR",
    "PEZ",
    "TYPE_I",
    "TYPE_II",
    "REACTION_VS_REVERSAL",
    "RSI_BAMM",
    "RSI_BAMM_ACCELERATION_TRIGGER",
    "HSI",
}
ALLOWED_CLASSIFICATIONS = {"supported", "partial", "quarantined", "unsupported"}
STATUS_COMPATIBILITY = {
    "supported": {
        "supported",
        "supported_frozen",
        "supported_source_state_machine",
        "supported_source_clock",
    },
    "partial": set(),
    "quarantined": {"quarantined", "fail_closed"},
    "unsupported": {"unsupported"},
}
BINDING_KEYS = ("source_refs", "specs", "code", "tests", "decisions")


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object: {path}")
    return payload


def _rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw = payload.get("items")
    if not isinstance(raw, list) or any(not isinstance(row, dict) for row in raw):
        raise TypeError("SOURCE_COVERAGE.items must be a list of objects")
    return raw


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        return []
    return value


def verify_source_coverage(
    root: Path = ROOT,
    coverage_path: Path | None = None,
) -> dict[str, Any]:
    path = coverage_path or (root / "governance" / "SOURCE_COVERAGE.json")
    payload = _read_json(path)
    errors: list[str] = []

    if payload.get("schema") != 2:
        errors.append("SOURCE_COVERAGE schema must be 2")

    rows = _rows(payload)
    ids = [str(row.get("id") or "") for row in rows]
    if len(ids) != len(set(ids)):
        errors.append("SOURCE_COVERAGE item ids must be unique")
    if set(ids) != EXPECTED_IDS:
        missing = sorted(EXPECTED_IDS - set(ids))
        extra = sorted(set(ids) - EXPECTED_IDS)
        errors.append(f"coverage id set mismatch missing={missing} extra={extra}")

    taxonomy = payload.get("taxonomy")
    if not isinstance(taxonomy, dict):
        errors.append("taxonomy must be an object")
        taxonomy = {}
    partial_items = _string_list(taxonomy.get("current_partial_items"))
    if partial_items:
        errors.append(f"current partial items must remain empty: {partial_items}")

    decision_index = _read_json(root / "governance" / "DECISION_INDEX.json")
    decision_rows = decision_index.get("active")
    if not isinstance(decision_rows, list):
        errors.append("DECISION_INDEX.active must be a list")
        decision_rows = []
    decision_sources = {
        str(row.get("id")): str(row.get("source"))
        for row in decision_rows
        if isinstance(row, dict) and row.get("id") and row.get("source")
    }

    by_id = {str(row.get("id")): row for row in rows}
    for item_id, row in by_id.items():
        classification = str(row.get("classification") or "")
        if classification not in ALLOWED_CLASSIFICATIONS:
            errors.append(f"{item_id}: invalid classification {classification!r}")
            continue
        legacy_status = str(row.get("status") or "")
        if legacy_status not in STATUS_COMPATIBILITY[classification]:
            errors.append(
                f"{item_id}: legacy status {legacy_status!r} conflicts with "
                f"classification {classification!r}"
            )

        for key in BINDING_KEYS:
            if key not in row:
                errors.append(f"{item_id}: missing binding key {key}")

        source_refs = _string_list(row.get("source_refs"))
        specs = _string_list(row.get("specs"))
        code = _string_list(row.get("code"))
        tests = _string_list(row.get("tests"))
        decisions = _string_list(row.get("decisions"))

        if classification in {"supported", "quarantined"}:
            for key, values in (
                ("source_refs", source_refs),
                ("specs", specs),
                ("code", code),
                ("tests", tests),
                ("decisions", decisions),
            ):
                if not values:
                    errors.append(f"{item_id}: {classification} item requires {key}")
        elif classification == "unsupported":
            if code or tests:
                errors.append(f"{item_id}: unsupported item must not claim code/tests")
            if not source_refs or not specs or not decisions:
                errors.append(f"{item_id}: unsupported item still requires Source/spec/Decision evidence")

        for rel in (*source_refs, *specs, *code, *tests):
            if not (root / rel).is_file():
                errors.append(f"{item_id}: bound path missing: {rel}")

        for decision_id in decisions:
            decision_source = decision_sources.get(decision_id)
            if decision_source is None:
                errors.append(f"{item_id}: decision not active/indexed: {decision_id}")
            elif not (root / decision_source).is_file():
                errors.append(
                    f"{item_id}: decision source missing for {decision_id}: {decision_source}"
                )

    critical = {
        "FIVE_ZERO": ("quarantined", "quarantined"),
        "ALTERNATE_BAT": ("quarantined", "fail_closed"),
        "HSI": ("unsupported", "unsupported_proprietary"),
        "RSI_BAMM_ACCELERATION_TRIGGER": ("unsupported", "deferred_not_implemented"),
    }
    for item_id, (classification, production_state) in critical.items():
        row = by_id.get(item_id, {})
        if row.get("classification") != classification:
            errors.append(f"{item_id}: classification must remain {classification}")
        if row.get("production_state") != production_state:
            errors.append(f"{item_id}: production_state must remain {production_state}")

    shark = by_id.get("SHARK", {})
    if shark.get("classification") != "supported" or shark.get("topology") != "0XABC":
        errors.append("SHARK must remain supported with topology 0XABC")
    shark_constraints = _string_list(shark.get("constraints"))
    if not any("never fabricate D" in value for value in shark_constraints):
        errors.append("SHARK must retain never-fabricate-D constraint")

    status = _read_json(root / "research" / "source-fidelity-status-v1.json")
    patterns = status.get("patterns")
    if not isinstance(patterns, dict):
        errors.append("source-fidelity patterns must be an object")
        patterns = {}
    five_zero = patterns.get("five_zero")
    alternate_bat = patterns.get("alternate_bat")
    if not isinstance(five_zero, dict) or five_zero.get("production") != "quarantined":
        errors.append("source-fidelity five_zero must remain production=quarantined")
    if not isinstance(alternate_bat, dict) or alternate_bat.get("production") != "fail_closed":
        errors.append("source-fidelity alternate_bat must remain production=fail_closed")

    rsi_bamm = status.get("rsi_bamm")
    if not isinstance(rsi_bamm, dict) or rsi_bamm.get("acceleration_trigger") != (
        "deferred_optional_enhancement"
    ):
        errors.append("source-fidelity RSI BAMM acceleration trigger must remain deferred")

    return {
        "status": "valid" if not errors else "invalid",
        "schema": payload.get("schema"),
        "freeze_id": payload.get("freeze_id"),
        "item_count": len(rows),
        "partial_item_count": len(partial_items),
        "errors": errors,
    }


def main() -> int:
    result = verify_source_coverage()
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return 0 if result["status"] == "valid" else 2


if __name__ == "__main__":
    raise SystemExit(main())
