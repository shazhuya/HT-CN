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

    current = state["current"]
    assert current["phase"]
    assert current["status"] in module.ALLOWED_STATE_STATUS
    assert current["latest_attempt_id"].startswith("A-")
    assert current["latest_hosted_validation_attempt_id"].startswith("A-")
    assert current["latest_validation"]["result"] == "success"
    assert isinstance(current["latest_validation"]["workflow_run"], int)
    if current.get("active_change") is None:
        assert current["status"] in {"closed", "ready", "ready_not_started"}
        assert current.get("active_spec") is None
    assert state["next_major_task"]["phase"]
    assert any("legacy PROJECT_CONTEXT" in item for item in warnings)


def test_resume_pack_is_compact_state_index_not_legacy_dump() -> None:
    module = load_project_state_module()
    ok, errors, _, state = module.validate()
    assert ok, errors
    pack = module.build_resume_pack(state)
    assert "HT-CN Resume Pack v2" in pack
    active_change = state["current"].get("active_change") or "(none)"
    assert f"active_change: `{active_change}`" in pack
    assert state["current"]["phase"] in pack
    assert state["next_major_task"]["phase"] in pack
    assert "FIVE_ZERO" in pack
    assert "## FILE: `SESSION_LOG.md`" not in pack
    assert "## FILE: `PROJECT_CONTEXT.md`" not in pack
    assert "# Core Context Files" not in pack
    assert "## Active Change Index" in pack
    if state["current"].get("active_change"):
        assert "full body: read the canonical file above" in pack
    else:
        assert "## Active Change Index\n\n(none)" in pack
    assert len(pack) < 30000


def test_attempt_recorder_refuses_non_active_change_by_contract() -> None:
    text = (ROOT / "scripts" / "record_attempt.py").read_text(encoding="utf-8")
    assert "refuse attempt for non-active change" in text
    assert 'state["ledgers"]["attempts"]' in text


def test_bounded_text_index_keeps_resume_pack_compact() -> None:
    module = load_project_state_module()
    raw = "\n".join(f"file-{idx}" for idx in range(250))
    bounded = module._bounded_text_index(raw, limit=120, label="changed files")
    assert "file-0" in bounded
    assert "file-119" in bounded
    assert "file-120" not in bounded
    assert "130 additional changed files omitted" in bounded


def test_source_coverage_index_is_compact_and_preserves_critical_states() -> None:
    module = load_project_state_module()
    source = module.read_json(module.SOURCE_PATH)
    index = module._source_coverage_index(source)
    assert "FIVE_ZERO: classification=quarantined" in index
    assert "ALTERNATE_BAT: classification=quarantined" in index
    assert "HSI: classification=unsupported" in index
    assert "full bindings: read the canonical ledger" in index
    assert len(index) < 5000


def test_open_issue_index_omits_closed_history_but_keeps_live_gates() -> None:
    module = load_project_state_module()
    issues = module.read_json(module.ISSUES_PATH)
    index = module._open_issue_index(issues)
    assert "ISSUE-0061" not in index
    assert "ISSUE-0066" in index
    assert "ISSUE-0067" in index
    assert "closed/history details: read the canonical ledger" in index
    assert len(index) < 6000


def test_decision_index_is_compact_but_preserves_active_sources() -> None:
    module = load_project_state_module()
    decisions = module.read_json(module.DECISIONS_PATH)
    index = module._decision_index(decisions)
    assert "D-065" in index
    assert "D-076" in index
    assert "canonical ledger: `governance/DECISION_INDEX.json`" in index
    assert len(index) < 6000
