from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_daily_review_digest_entrypoint_compiles() -> None:
    path = ROOT / "scripts" / "m5_build_daily_review_digest.py"
    compile(
        path.read_text(encoding="utf-8"),
        str(path),
        "exec",
    )


def test_daily_review_bat_exposes_non_predictive_boundary() -> None:
    text = (ROOT / "运行HT-CN每日变化复盘.bat").read_text(
        encoding="utf-8"
    )
    assert "m5_build_daily_review_digest.py" in text
    assert "不做收益/胜率/alpha排名" in text
    assert "不写 M4 权威 evidence" in text
    assert "不输出交易指令" in text


def test_daily_close_pipeline_exposes_review_digest_artifact() -> None:
    text = (ROOT / "scripts" / "m5_daily_close_pipeline.py").read_text(
        encoding="utf-8"
    )
    assert "m5_daily_review_digest" in text
    assert "review_digest_ready=" in text
