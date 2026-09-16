from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "AGENTS.md",
    "PROJECT_CONTEXT.md",
    "DECISIONS.md",
    "SESSION_LOG.md",
    "scripts/context_pack.py",
    "生成HT-CN续接包.bat",
    "检查HT-CN续接状态.bat",
]


def test_continuity_contract_files_exist() -> None:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).exists()]
    assert not missing, f"continuity contract files missing: {missing}"


def test_project_context_has_valid_checkpoint_and_gate() -> None:
    text = (ROOT / "PROJECT_CONTEXT.md").read_text(encoding="utf-8")
    match = re.search(
        r"^context_checkpoint:\s*`([0-9a-fA-F]{40})`\s*$",
        text,
        re.MULTILINE,
    )
    assert match, "PROJECT_CONTEXT.md must contain a full 40-char context_checkpoint"
    assert "Source Fidelity before M3 expansion" in text
    assert "下一步唯一主任务" in text


def test_agent_protocol_requires_delta_review() -> None:
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "context_checkpoint..HEAD" in text
    assert "PROJECT_CONTEXT.md" in text
    assert "DECISIONS.md" in text
    assert "最新 CI" in text


def test_context_pack_declares_core_handoff_contract() -> None:
    text = (ROOT / "scripts/context_pack.py").read_text(encoding="utf-8")
    assert "HTCN_CONTEXT_PACK.md" in text
    assert "specs/m2-source-fidelity-repair.md" in text
    assert "specs/m2-book-golden-ledger.md" in text
    assert "specs/m3-workbench.md" in text
