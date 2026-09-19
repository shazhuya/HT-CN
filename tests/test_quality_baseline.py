from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    path = ROOT / "scripts" / "pytest_with_warning_budget.py"
    spec = importlib.util.spec_from_file_location("htcn_warning_budget", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_warning_parser_reads_pytest_summary_without_summing_duplicate_lines() -> None:
    module = load_module()
    assert module.parse_warning_count(["869 passed, 1163 warnings in 10.0s\n"]) == 1163
    assert module.parse_warning_count(["1 warning\n", "3 warnings\n"]) == 3
    assert module.parse_warning_count(["869 passed in 10.0s\n"]) == 0


def test_warning_baseline_is_bound_to_latest_verified_main() -> None:
    payload = json.loads(
        (ROOT / "governance" / "QUALITY_BASELINE.json").read_text(encoding="utf-8")
    )
    assert payload["pytest"]["warning_budget"] == 1163
    assert payload["pytest"]["baseline_passed"] == 869
    assert payload["pytest"]["baseline_commit"] == (
        "cffe3956f4a053581a512a3df24413f400ab3be5"
    )
