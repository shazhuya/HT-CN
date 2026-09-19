from __future__ import annotations

import json
from pathlib import Path

import pytest

from htcn.app.daily_handoff_v3_runner import run_daily_handoff_bundle_v3


def _write_pipeline(path: Path) -> dict:
    payload = {
        "schema_version": 2,
        "overall_status": "product_ready_research_degraded",
        "m5_product_ready": True,
        "m5_history_ready": True,
        "m5_review_digest_ready": True,
        "m4_research_ready": False,
        "artifacts": {},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def test_v3_transport_failure_does_not_mutate_pipeline_or_readiness(
    tmp_path: Path,
) -> None:
    pipeline_path = tmp_path / "pipeline.json"
    expected = _write_pipeline(pipeline_path)
    before = pipeline_path.read_bytes()

    def fail_builder(**_: object) -> dict:
        raise RuntimeError("v3 transport exploded")

    report_path = tmp_path / "handoff-v3-report.json"
    payload, code = run_daily_handoff_bundle_v3(
        root=tmp_path,
        pipeline_report=pipeline_path,
        output=tmp_path / "handoff-v3.zip",
        report=report_path,
        builder=fail_builder,
    )

    assert code == 2
    assert payload["status"] == "failed"
    assert payload["pipeline_m5_product_ready"] is True
    assert payload["pipeline_m5_history_ready"] is True
    assert payload["pipeline_m5_review_digest_ready"] is True
    assert payload["pipeline_m4_research_ready"] is False
    assert payload["pipeline_report_unchanged"] is True
    assert (
        payload["transport_failure_does_not_rewrite_pipeline_readiness"]
        is True
    )
    assert payload["phase10_handoff_v2_is_not_overwritten"] is True
    assert pipeline_path.read_bytes() == before
    assert json.loads(pipeline_path.read_text(encoding="utf-8")) == expected


def test_v3_transport_success_keeps_pipeline_unchanged(
    tmp_path: Path,
) -> None:
    pipeline_path = tmp_path / "pipeline.json"
    _write_pipeline(pipeline_path)
    before = pipeline_path.read_bytes()

    def good_builder(**_: object) -> dict:
        return {
            "status": "complete_review_transport",
            "bundle_sha256": "a" * 64,
            "verification": {"status": "valid"},
        }

    payload, code = run_daily_handoff_bundle_v3(
        root=tmp_path,
        pipeline_report=pipeline_path,
        output=tmp_path / "handoff-v3.zip",
        report=tmp_path / "handoff-v3-report.json",
        builder=good_builder,
    )

    assert code == 0
    assert payload["status"] == "ready"
    assert payload["pipeline_report_unchanged"] is True
    assert payload["bundle"]["verification"]["status"] == "valid"
    assert pipeline_path.read_bytes() == before


def test_v3_runner_refuses_colliding_artifact_paths(
    tmp_path: Path,
) -> None:
    pipeline_path = tmp_path / "pipeline.json"
    _write_pipeline(pipeline_path)
    before = pipeline_path.read_bytes()

    with pytest.raises(ValueError, match="must not replace pipeline"):
        run_daily_handoff_bundle_v3(
            root=tmp_path,
            pipeline_report=pipeline_path,
            output=tmp_path / "handoff-v3.zip",
            report=pipeline_path,
        )

    with pytest.raises(ValueError, match="must not replace pipeline"):
        run_daily_handoff_bundle_v3(
            root=tmp_path,
            pipeline_report=pipeline_path,
            output=pipeline_path,
            report=tmp_path / "handoff-v3-report.json",
        )

    assert pipeline_path.read_bytes() == before


def test_v3_runner_keeps_output_and_report_distinct(
    tmp_path: Path,
) -> None:
    pipeline_path = tmp_path / "pipeline.json"
    _write_pipeline(pipeline_path)
    same = tmp_path / "same.zip"

    with pytest.raises(ValueError, match="must be distinct"):
        run_daily_handoff_bundle_v3(
            root=tmp_path,
            pipeline_report=pipeline_path,
            output=same,
            report=same,
        )
