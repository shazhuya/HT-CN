from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github" / "workflows" / "ci.yml"


def test_ci_uses_workflow_level_supersession_concurrency() -> None:
    text = CI.read_text(encoding="utf-8")
    expected = (
        "concurrency:\n"
        "  group: htcn-ci-${{ github.event.pull_request.number || github.ref }}\n"
        "  cancel-in-progress: true\n"
    )
    assert expected in text
    jobs_start = text.index("jobs:")
    assert "\n    concurrency:" not in text[jobs_start:]


def test_ci_enforces_m6_5_source_coverage() -> None:
    text = CI.read_text(encoding="utf-8")
    assert "Verify M6.5 source coverage freeze" in text
    assert "python scripts/m6_verify_source_coverage.py" in text
