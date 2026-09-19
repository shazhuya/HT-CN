from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_context_sync_exposes_stage_progress_markers() -> None:
    text = (ROOT / "scripts" / "m3_sync_all_contexts.py").read_text(
        encoding="utf-8"
    )
    for marker in ("[1/4]", "[2/4]", "[3/4]", "[4/4]"):
        assert marker in text
    assert "flush=True" in text


def test_precompute_report_surfaces_instrument_errors() -> None:
    text = (
        ROOT / "scripts" / "m5_precompute_operator_snapshot.py"
    ).read_text(encoding="utf-8")
    assert '"instrument_errors"' in text
