from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_operator_history_entrypoints_compile() -> None:
    for relative in (
        "scripts/m5_record_operator_history.py",
        "scripts/m5_query_operator_history.py",
    ):
        path = ROOT / relative
        compile(
            path.read_text(encoding="utf-8"),
            str(path),
            "exec",
        )


def test_history_query_bat_keeps_product_observation_boundary() -> None:
    text = (ROOT / "运行HT-CN历史变化查询.bat").read_text(
        encoding="utf-8"
    )
    assert "m5_query_operator_history.py" in text
    assert "M4权威证据" in text
    assert "胜率/alpha排名" in text


def test_daily_close_pipeline_exposes_history_artifacts() -> None:
    text = (ROOT / "scripts" / "m5_daily_close_pipeline.py").read_text(
        encoding="utf-8"
    )
    assert "m5_operator_history_report" in text
    assert "m5_operator_history_root" in text
    assert "history_ready=" in text
