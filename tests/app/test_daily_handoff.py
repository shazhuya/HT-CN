from __future__ import annotations

import json
from pathlib import Path
import zipfile

import pytest

from htcn.app.daily_handoff import (
    build_daily_handoff_bundle,
    verify_daily_handoff_bundle,
)


def _write_product_snapshot(path: Path, trade_date: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({
            "schema_version": 1,
            "contract_version": 1,
            "generated_at_utc": f"{trade_date}T09:00:00+00:00",
            "expected_trade_date": trade_date,
            "bars": 420,
            "scales": [3, 5, 8, 13],
            "universe_hash": "abc",
            "instrument_count": 1,
            "queue": {"items": []},
            "authoritative_evidence": False,
            "writes_m4_evidence": False,
        }),
        encoding="utf-8",
    )


def test_daily_handoff_product_only_partial_bundle(tmp_path) -> None:
    reports = tmp_path / "artifacts" / "reports"
    reports.mkdir(parents=True)
    (reports / "m5-operator-snapshot.json").write_text(
        '{"status":"ready"}',
        encoding="utf-8",
    )
    cache = tmp_path / "data" / "product" / "m5" / "operator_queue"
    _write_product_snapshot(cache / "2026-09-18__b420__s3-5-8-13.json", "2026-09-18")
    _write_product_snapshot(cache / "2026-09-17__b420__s3-5-8-13.json", "2026-09-17")

    output = tmp_path / "artifacts" / "reports" / "htcn-daily-handoff.zip"
    payload = build_daily_handoff_bundle(
        root=tmp_path,
        pipeline_summary={
            "overall_status": "partial",
            "data_ready": True,
            "m5_product_ready": True,
            "m4_research_ready": False,
        },
        output=output,
    )

    assert payload["status"] == "partial_transport"
    assert payload["m5_snapshot_count"] == 2
    assert payload["verification"]["status"] == "valid"
    checked = verify_daily_handoff_bundle(output)
    assert checked["status"] == "valid"

    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
    assert "pipeline/m5-daily-close-pipeline.json" in names
    assert any(name.startswith("m5/operator_snapshots/") for name in names)
    assert "m4/m4-evidence-bundle.zip" not in names


def test_daily_handoff_requires_current_snapshot_when_product_ready(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="current_snapshot_missing"):
        build_daily_handoff_bundle(
            root=tmp_path,
            pipeline_summary={
                "overall_status": "partial",
                "data_ready": True,
                "m5_product_ready": True,
                "m4_research_ready": False,
            },
            output=tmp_path / "handoff.zip",
        )


def test_daily_handoff_verifier_detects_tampering(tmp_path) -> None:
    reports = tmp_path / "artifacts" / "reports"
    reports.mkdir(parents=True)
    cache = tmp_path / "data" / "product" / "m5" / "operator_queue"
    _write_product_snapshot(cache / "2026-09-18__b420__s3-5-8-13.json", "2026-09-18")
    output = reports / "htcn-daily-handoff.zip"
    build_daily_handoff_bundle(
        root=tmp_path,
        pipeline_summary={
            "overall_status": "partial",
            "data_ready": True,
            "m5_product_ready": True,
            "m4_research_ready": False,
        },
        output=output,
    )

    with zipfile.ZipFile(output, "a") as archive:
        archive.writestr(
            "m5/operator_snapshots/2026-09-18__b420__s3-5-8-13.json",
            b"tampered",
        )

    checked = verify_daily_handoff_bundle(output)
    assert checked["status"] == "invalid"
    assert checked["errors"]
