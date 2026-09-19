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
    milestones = load("governance/MILESTONES.json")
    assert state["schema"] == 2

    current = state["current"]
    assert current["milestone"] == milestones["active"]
    milestone = next(
        row for row in milestones["milestones"]
        if row["id"] == current["milestone"]
    )
    phase = next(
        row for row in milestone["phases"]
        if row["id"] == current["phase"]
    )
    assert phase["status"] == current["status"]

    attempts = [
        json.loads(line)
        for line in (ROOT / state["ledgers"]["attempts"]).read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    by_id = {row["attempt_id"]: row for row in attempts}
    latest_attempt_id = current["latest_attempt_id"]
    hosted_attempt_id = current["latest_hosted_validation_attempt_id"]
    assert latest_attempt_id in by_id
    assert hosted_attempt_id in by_id

    active_change = current.get("active_change")
    if active_change:
        assert by_id[latest_attempt_id]["change_id"] == active_change
        assert by_id[hosted_attempt_id]["change_id"] == active_change
        assert by_id[hosted_attempt_id]["result"] == "success"
        assert (
            by_id[hosted_attempt_id]["workflow_run"]
            == current["latest_validation"]["workflow_run"]
        )
        assert current.get("active_spec")
    else:
        assert current["status"] in {"closed", "ready", "ready_not_started"}
        assert current.get("active_spec") is None

    assert state["next_major_task"]["phase"] != ""
    assert state["next_major_task"]["status"] != ""
    assert state["recovery_contract"]["chat_is_authoritative"] is False
    assert state["recovery_contract"]["important_fact_may_exist_only_in_chat"] is False
    assert state["recovery_contract"]["bootstrap_must_fail_on_state_drift"] is True


def test_active_change_and_required_specs_resolve() -> None:
    state = load("governance/PROJECT_STATE.json")
    current = state["current"]
    active_change = current.get("active_change")

    if active_change:
        matches = sorted(
            (ROOT / "governance" / "changes").glob(f"{active_change}-*.md")
        )
        assert len(matches) == 1
        assert current.get("active_spec") in state["required_specs"]
        assert (ROOT / current["active_spec"]).exists()
    else:
        assert current["status"] in {"closed", "ready", "ready_not_started"}
        assert current.get("active_spec") is None

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


def test_m6_2_empirical_acceptance_is_persisted_when_closed() -> None:
    state = load("governance/PROJECT_STATE.json")
    if state["current"]["phase"] != "M6.2" or state["current"]["status"] != "closed":
        return

    assert state["private_m1"]["current_market_full_closeout_ready"] is True
    assert state["next_major_task"]["phase"] == "M6.3"
    receipt_path = state["private_m1"]["accepted_evidence_receipt"]
    receipt = load(receipt_path)
    assert receipt["status"] == "accepted"
    assert receipt["source_main_head"] == receipt["end_remote_main_head"]
    assert receipt["m6_verification"]["full_closeout_ready"] is True
    assert receipt["m6_verification"]["error_count"] == 0

    issues = load("governance/OPEN_ISSUES.json")
    issue = next(row for row in issues["issues"] if row["id"] == "ISSUE-0061")
    assert issue["status"] == "closed"


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
