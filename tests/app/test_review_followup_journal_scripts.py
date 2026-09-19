from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_review_journal_query_script_compiles() -> None:
    path = ROOT / "scripts" / "m5_query_review_journal.py"
    compile(
        path.read_text(encoding="utf-8"),
        str(path),
        "exec",
    )


def test_review_journal_query_bat_keeps_product_boundary() -> None:
    text = (ROOT / "运行HT-CN复盘跟踪查询.bat").read_text(
        encoding="utf-8"
    )
    assert "m5_query_review_journal.py" in text
    assert "不修改 lifecycle/action" in text
    assert "不写 M4 evidence" in text
    assert "不做胜率/alpha/预测排名" in text
    assert "不输出交易指令" in text
