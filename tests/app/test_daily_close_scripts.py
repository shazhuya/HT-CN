from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_daily_close_entrypoints_compile() -> None:
    path = ROOT / "scripts" / "m5_daily_close_pipeline.py"
    compile(
        path.read_text(encoding="utf-8"),
        str(path),
        "exec",
    )


def test_windows_daily_close_exposes_product_research_separation() -> None:
    text = (ROOT / "运行HT-CN每日收盘流水线.bat").read_text(
        encoding="utf-8"
    )
    assert "m5_daily_close_pipeline.py" in text
    assert "M4 QFQ" in text
    assert "不会阻塞M5产品队列" in text

def test_m5_operator_precompute_uses_default_sse_szse_scope() -> None:
    text = (ROOT / "scripts" / "m5_precompute_operator_snapshot.py").read_text(
        encoding="utf-8"
    )
    assert 'exchanges=("SSE", "SZSE")' in text
    assert '"BSE"' not in text
