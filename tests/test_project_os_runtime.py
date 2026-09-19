from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_project_state_module():
    path = ROOT / "scripts" / "project_state.py"
    spec = importlib.util.spec_from_file_location("htcn_project_state", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_project_os_runtime_validation_is_green() -> None:
    module = load_project_state_module()
    ok, errors, warnings, state = module.validate()
    assert ok, errors
    assert not errors
    assert state["current"]["phase"] == "M6.2"
    assert state["current"]["status"] in {
        "implementing",
        "validation_green",
        "ready_to_merge",
        "merged",
        "postmerge_pending",
        "awaiting_private_run",
        "real_run_in_progress",
    }
    assert state["current"]["active_change"] == "CR-0066"
    assert state["current"]["latest_attempt_id"] == "A-20260919-0066-014"
    assert state["next_major_task"]["phase"] == "M6.2"
    assert any("legacy PROJECT_CONTEXT" in item for item in warnings)


def test_resume_pack_is_compact_state_index_not_legacy_dump() -> None:
    module = load_project_state_module()
    ok, errors, _, state = module.validate()
    assert ok, errors
    pack = module.build_resume_pack(state)
    assert "HT-CN Resume Pack v2" in pack
    assert "active_change: `CR-0066`" in pack
    assert "M6.2" in pack
    assert "FIVE_ZERO" in pack
    assert "## FILE: `SESSION_LOG.md`" not in pack
    assert "## FILE: `PROJECT_CONTEXT.md`" not in pack
    assert "# Core Context Files" not in pack
    assert len(pack) < 30000


def test_attempt_recorder_refuses_non_active_change_by_contract() -> None:
    text = (ROOT / "scripts" / "record_attempt.py").read_text(encoding="utf-8")
    assert "refuse attempt for non-active change" in text
    assert 'state["ledgers"]["attempts"]' in text
