from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "AGENTS.md",
    "CHAT_CONTINUATION.md",
    "PROJECT_BLUEPRINT.md",
    "governance/PROJECT_STATE.json",
    "governance/MILESTONES.json",
    "governance/DECISION_INDEX.json",
    "governance/SOURCE_COVERAGE.json",
    "governance/OPEN_ISSUES.json",
    "governance/QUALITY_BASELINE.json",
    "uv.lock",
    "requirements-dev.lock",
    "scripts/project_state.py",
    "scripts/context_pack.py",
    "scripts/build_chat_continuation_bundle.py",
    "scripts/verify_chat_continuation_bundle.py",
    "scripts/pytest_with_warning_budget.py",
    "scripts/ruff_with_budget.py",
    "生成HT-CN续接包.bat",
    "验证HT-CN续接包.bat",
    "检查HT-CN续接状态.bat",
]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_project_os_v2_contract_files_exist() -> None:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).exists()]
    assert not missing, f"Project OS files missing: {missing}"


def test_project_state_is_machine_current_truth() -> None:
    state = load("governance/PROJECT_STATE.json")
    assert state["schema"] == 2
    assert state["current"]["milestone"] == "M6"
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
    assert state["current"]["active_spec"] == "specs/m6-phase-2-real-private-m1-closeout.md"
    attempts = [
        json.loads(line)
        for line in (ROOT / state["ledgers"]["attempts"]).read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    by_id = {row["attempt_id"]: row for row in attempts}
    latest_attempt_id = state["current"]["latest_attempt_id"]
    hosted_attempt_id = state["current"]["latest_hosted_validation_attempt_id"]
    assert latest_attempt_id in by_id
    assert hosted_attempt_id in by_id
    assert by_id[latest_attempt_id]["change_id"] == "CR-0066"
    assert by_id[hosted_attempt_id]["change_id"] == "CR-0066"
    assert by_id[hosted_attempt_id]["result"] == "success"
    assert (
        by_id[hosted_attempt_id]["workflow_run"]
        == state["current"]["latest_validation"]["workflow_run"]
    )
    assert state["next_major_task"]["phase"] == "M6.2"
    assert state["next_major_task"]["status"] in {
        "implementing",
        "validation_green",
        "ready_to_merge",
        "awaiting_private_run",
    }
    assert state["recovery_contract"]["chat_is_authoritative"] is False
    assert state["recovery_contract"]["important_fact_may_exist_only_in_chat"] is False
    assert state["recovery_contract"]["bootstrap_must_fail_on_state_drift"] is True


def test_active_change_and_required_specs_resolve() -> None:
    state = load("governance/PROJECT_STATE.json")
    assert state["current"]["active_change"] == "CR-0066"
    change = ROOT / "governance" / "changes" / "CR-0066-real-private-m1-closeout.md"
    assert change.exists()
    change_text = change.read_text(encoding="utf-8")
    assert any(
        f"status: {value}" in change_text
        for value in (
            "implementing",
            "validation_green",
            "ready_to_merge",
            "merged",
            "postmerge_pending",
        )
    )
    for rel in state["required_specs"]:
        assert (ROOT / rel).exists(), rel


def test_context_pack_is_dynamic_not_hard_coded_to_old_specs() -> None:
    text = (ROOT / "scripts" / "context_pack.py").read_text(encoding="utf-8")
    assert "build_resume_pack" in text
    assert "PROJECT_STATE" not in text or "project_state" in text
    assert "ACTIVE_SPECS" not in text
    assert "specs/m2-source-fidelity-repair.md" not in text


def test_decision_index_prevents_old_decision_revival() -> None:
    payload = load("governance/DECISION_INDEX.json")
    rows = {row["id"]: row for row in payload["active"]}
    assert rows["D-035"]["status"] == "active"
    assert "D-034" in rows["D-035"]["supersedes"]
    assert rows["D-065"]["source"] == "governance/decisions/D-065-project-os-v2.md"
    assert rows["D-066"]["source"] == "governance/decisions/D-066-private-m1-evidence-bundle.md"
    assert rows["D-067"]["source"] == "governance/decisions/D-067-portable-chat-continuity.md"


def test_source_coverage_keeps_known_fail_closed_boundaries() -> None:
    payload = load("governance/SOURCE_COVERAGE.json")
    rows = {row["id"]: row for row in payload["items"]}
    assert rows["SHARK"]["topology"] == "0XABC"
    assert rows["FIVE_ZERO"]["status"] == "quarantined"
    assert rows["ALTERNATE_BAT"]["status"] == "fail_closed"
    assert rows["HSI"]["status"] == "unsupported"


def test_release_record_does_not_claim_private_m1_closeout() -> None:
    state = load("governance/PROJECT_STATE.json")
    release = load(state["ledgers"]["releases"])
    assert release["commit"] == state["last_integrated_release"]["commit"]
    assert release["claims"]["private_m1_current_market_closeout_ready"] is False
    assert release["claims"]["profitability_claim_allowed"] is False


def test_agent_protocol_demotes_chat_and_legacy_context() -> None:
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "聊天不是项目状态" in text
    assert "PROJECT_STATE.json" in text
    assert "No Important Fact Only in Chat" in text
    assert "PROJECT_CONTEXT.md" in text
    assert "不再拥有 current-state authority" in text
    assert "普通 ChatGPT / 其他 AI 的便携续接" in text
    assert "Bootstrap Receipt" in text
    assert "不要求通读全部旧聊天" in text


def test_portable_continuation_contract_is_required_and_private_safe() -> None:
    state = load("governance/PROJECT_STATE.json")
    assert "specs/m6-phase-2-portable-chat-continuity.md" in state["required_specs"]
    contract = (ROOT / "CHAT_CONTINUATION.md").read_text(encoding="utf-8")
    assert "不需要每次重新阅读全部旧聊天" in contract
    assert "Bootstrap Receipt 必答项" in contract
    assert "私有 M1 数据库" in contract
    generator = (ROOT / "生成HT-CN续接包.bat").read_text(encoding="utf-8")
    assert "build_chat_continuation_bundle.py" in generator
    assert "--allow-dirty" not in generator


def test_project_state_engine_is_fail_closed_and_checks_ancestry() -> None:
    text = (ROOT / "scripts" / "project_state.py").read_text(encoding="utf-8")
    assert "git_is_ancestor" in text
    assert "release anchor is not an ancestor" in text
    assert "required spec missing" in text
    assert "active decision source missing" in text
    assert "return 2" in text
    assert text.count("ALLOWED_CHANGE_STATUS = {") == 1
    assert "active spec status does not match current state" in text
    assert "latest_validation commit does not match hosted attempt commit" in text
