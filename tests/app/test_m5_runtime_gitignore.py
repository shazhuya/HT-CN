from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_runtime_product_and_research_state_are_git_ignored() -> None:
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "data/product/**" in text
    assert "data/research/**" in text


def test_runtime_ignore_does_not_hide_source_tree() -> None:
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "src/**" not in text
    assert "scripts/**" not in text
