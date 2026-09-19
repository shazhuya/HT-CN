from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_handoff_v3_script_uses_new_versioned_paths() -> None:
    text = (
        ROOT / "scripts" / "m5_build_daily_handoff_v3.py"
    ).read_text(encoding="utf-8")
    assert "run_daily_handoff_bundle_v3" in text
    assert "htcn-daily-handoff-v3.zip" in text
    assert "m5-daily-handoff-v3.json" in text
    assert "Phase 9/11/12 readiness remains unchanged" in text
    assert "v2 is untouched" in text


def test_handoff_v3_bat_does_not_run_pipeline_or_v2_entrypoint() -> None:
    text = (ROOT / "运行HT-CN每日交接包v3.bat").read_text(
        encoding="utf-8"
    )
    assert "m5_build_daily_handoff_v3.py" in text
    assert "m5_daily_close_pipeline.py" not in text
    assert "m5_build_daily_handoff.py" not in text
    assert "htcn-daily-handoff-v3.zip" in text
    assert "旧的 v2 交接包也不会被覆盖" in text


def test_phase10_v2_entrypoints_remain_frozen_and_separate() -> None:
    script = (ROOT / "scripts" / "m5_build_daily_handoff.py").read_text(
        encoding="utf-8"
    )
    bat = (ROOT / "运行HT-CN每日交接包.bat").read_text(
        encoding="utf-8"
    )
    assert "htcn-daily-handoff-v2.zip" in script
    assert "m5_build_daily_handoff.py" in bat
    assert "m5_build_daily_handoff_v3.py" not in bat
