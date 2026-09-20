from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "m6_verify_source_coverage.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("m6_verify_source_coverage", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load M6.5 source coverage verifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_source_coverage_freeze_is_valid() -> None:
    module = _load_module()
    result = module.verify_source_coverage(ROOT)
    assert result["status"] == "valid"
    assert result["schema"] == 2
    assert result["item_count"] == 18
    assert result["partial_item_count"] == 0


def test_source_coverage_fails_if_five_zero_is_promoted(tmp_path: Path) -> None:
    module = _load_module()
    payload = json.loads(
        (ROOT / "governance" / "SOURCE_COVERAGE.json").read_text(encoding="utf-8")
    )
    five_zero = next(row for row in payload["items"] if row["id"] == "FIVE_ZERO")
    five_zero["classification"] = "supported"
    five_zero["production_state"] = "enabled"
    path = tmp_path / "SOURCE_COVERAGE.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = module.verify_source_coverage(ROOT, path)
    assert result["status"] == "invalid"
    assert any("FIVE_ZERO" in error for error in result["errors"])


def test_source_coverage_fails_if_partial_is_invented(tmp_path: Path) -> None:
    module = _load_module()
    payload = json.loads(
        (ROOT / "governance" / "SOURCE_COVERAGE.json").read_text(encoding="utf-8")
    )
    payload["taxonomy"]["current_partial_items"] = ["ALTERNATE_BAT"]
    path = tmp_path / "SOURCE_COVERAGE.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = module.verify_source_coverage(ROOT, path)
    assert result["status"] == "invalid"
    assert result["partial_item_count"] == 1
