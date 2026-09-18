from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_daily_handoff_python_entrypoints_compile() -> None:
    for relative in (
        "scripts/m5_daily_close_pipeline.py",
        "scripts/m5_export_daily_handoff.py",
    ):
        path = ROOT / relative
        compile(
            path.read_text(encoding="utf-8"),
            str(path),
            "exec",
        )


def test_windows_daily_close_surfaces_single_upload_bundle() -> None:
    text = (ROOT / "运行HT-CN每日收盘流水线.bat").read_text(
        encoding="utf-8"
    )
    assert "htcn-daily-handoff.zip" in text
    assert "m5_daily_close_pipeline.py" in text
