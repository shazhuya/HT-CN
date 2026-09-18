from __future__ import annotations

import json

import pytest
from pathlib import Path

from htcn.app.daily_handoff_runner import run_daily_handoff_bundle


def _write_pipeline(path: Path, *, product_ready: bool = True) -> dict:
    payload = {
        "schema_version": 2,
        "overall_status": "product_ready_research_degraded",
        "m5_product_ready": product_ready,
        "m4_research_ready": False,
        "artifacts": {},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def test_transport_failure_does_not_mutate_pipeline_or_readiness(
    tmp_path: Path,
) -> None:
    pipeline_path = tmp_path / "artifacts" / "reports" / "pipeline.json"
    expected = _write_pipeline(pipeline_path, product_ready=True)
    before = pipeline_path.read_bytes()

    def fail_builder(**_: object) -> dict:
        raise RuntimeError("transport exploded")

    report_path = tmp_path / "artifacts" / "reports" / "handoff.json"
    payload, code = run_daily_handoff_bundle(
        root=tmp_path,
        pipeline_report=pipeline_path,
        output=tmp_path / "handoff.zip",
        report=report_path,
        builder=fail_builder,
    )

    assert code == 2
    assert payload["status"] == "failed"
    assert payload["pipeline_m5_product_ready"] is True
    assert payload["pipeline_m4_research_ready"] is False
    assert payload["pipeline_report_unchanged"] is True
    assert payload["transport_failure_does_not_rewrite_pipeline_readiness"] is True
    assert pipeline_path.read_bytes() == before
    assert json.loads(pipeline_path.read_text(encoding="utf-8")) == expected

    persisted = json.loads(report_path.read_text(encoding="utf-8"))
    assert persisted["pipeline_m5_product_ready"] is True
    assert persisted["status"] == "failed"


def test_transport_success_keeps_pipeline_unchanged(tmp_path: Path) -> None:
    pipeline_path = tmp_path / "pipeline.json"
    _write_pipeline(pipeline_path, product_ready=True)
    before = pipeline_path.read_bytes()

    def good_builder(**_: object) -> dict:
        return {
            "status": "product_transport_research_degraded",
            "bundle_sha256": "a" * 64,
            "verification": {"status": "valid"},
        }

    payload, code = run_daily_handoff_bundle(
        root=tmp_path,
        pipeline_report=pipeline_path,
        output=tmp_path / "handoff.zip",
        report=tmp_path / "handoff-report.json",
        builder=good_builder,
    )

    assert code == 0
    assert payload["status"] == "ready"
    assert payload["pipeline_report_unchanged"] is True
    assert payload["bundle"]["verification"]["status"] == "valid"
    assert pipeline_path.read_bytes() == before


def test_missing_pipeline_writes_separate_failure_report(tmp_path: Path) -> None:
    report_path = tmp_path / "handoff-report.json"
    payload, code = run_daily_handoff_bundle(
        root=tmp_path,
        pipeline_report=tmp_path / "missing.json",
        output=tmp_path / "handoff.zip",
        report=report_path,
    )

    assert code == 2
    assert payload["status"] == "failed"
    assert payload["pipeline_m5_product_ready"] is None
    assert payload["pipeline_report_unchanged"] is False
    assert "FileNotFoundError" in str(payload["error"])
    assert report_path.is_file()


def test_runner_refuses_artifact_paths_that_can_overwrite_pipeline(
    tmp_path: Path,
) -> None:
    pipeline_path = tmp_path / "pipeline.json"
    _write_pipeline(pipeline_path, product_ready=True)
    before = pipeline_path.read_bytes()

    with pytest.raises(ValueError, match="must not replace pipeline report"):
        run_daily_handoff_bundle(
            root=tmp_path,
            pipeline_report=pipeline_path,
            output=tmp_path / "handoff.zip",
            report=pipeline_path,
        )

    assert pipeline_path.read_bytes() == before
