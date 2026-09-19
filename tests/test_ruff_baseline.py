from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    path = ROOT / "scripts" / "ruff_with_budget.py"
    spec = importlib.util.spec_from_file_location("htcn_ruff_budget", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ruff_budget_and_parser() -> None:
    module = load_module()
    assert module.violation_budget() == 483
    assert module.parse_violations('[{"code":"F401"}]') == [{"code": "F401"}]
