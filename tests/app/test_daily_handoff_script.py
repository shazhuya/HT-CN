from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_handoff_script_uses_separate_transport_report() -> None:
    text = (ROOT / "scripts" / "m5_build_daily_handoff.py").read_text(
        encoding="utf-8"
    )
    assert "run_daily_handoff_bundle" in text
    assert "m5-daily-close-pipeline.json" in text
    assert "htcn-daily-handoff-v2.zip" in text
    assert "m5-daily-handoff.json" in text
    assert "Phase 9 product/research readiness remains unchanged" in text


def test_handoff_bat_calls_only_handoff_script() -> None:
    text = (ROOT / "运行HT-CN每日交接包.bat").read_text(
        encoding="utf-8"
    )
    assert "m5_build_daily_handoff.py" in text
    assert "m5_daily_close_pipeline.py" not in text
