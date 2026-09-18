from __future__ import annotations

import json
from pathlib import Path
import zipfile

import pytest

from htcn.app.daily_handoff import (
    build_daily_handoff_bundle,
    verify_daily_handoff_bundle,
)
from htcn.app.operator_snapshot import OPERATOR_SNAPSHOT_CONTRACT_VERSION


FP_A = "a" * 64
FP_B = "b" * 64


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _identity(fingerprint: str = FP_A) -> dict:
    return {
        "contract_version": 1,
        "fingerprint": fingerprint,
        "data": {
            "contract_version": 1,
            "fingerprint": "c" * 64,
            "component_count": 1,
            "manifest_mode": "relative_path_size_mtime_ns",
        },
        "analysis_code": {
            "contract_version": 1,
            "fingerprint": "d" * 64,
            "component_count": 1,
            "manifest_mode": "relative_path_content_sha256",
        },
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "methodology_identity": False,
    }


def _prepare_product_ready(
    root: Path,
    *,
    trade_date: str = "2026-09-18",
    fingerprint: str = FP_A,
) -> tuple[dict, Path]:
    identity = _identity(fingerprint)
    cache = root / "data" / "product" / "m5" / "operator_queue"
    snapshot = cache / f"{trade_date}__b420__s3-5-8-13.json"
    _write_json(
        snapshot,
        {
            "schema_version": 1,
            "contract_version": OPERATOR_SNAPSHOT_CONTRACT_VERSION,
            "generated_at_utc": f"{trade_date}T08:00:00+00:00",
            "expected_trade_date": trade_date,
            "bars": 420,
            "scales": [3, 5, 8, 13],
            "universe_hash": "u",
            "instrument_count": 1,
            "input_identity": identity,
            "queue": {
                "as_of_trade_date": trade_date,
                "observation_integrity": "single_as_of",
                "items": [],
            },
            "authoritative_evidence": False,
            "writes_m4_evidence": False,
        },
    )
    report = root / "artifacts" / "reports" / "m5-operator-snapshot.json"
    _write_json(
        report,
        {
            "schema_version": 2,
            "status": "ready",
            "product_ready": True,
            "instrument_count": 1,
            "analyzed_instrument_count": 1,
            "failed_instrument_count": 0,
            "as_of_trade_date": trade_date,
            "observation_integrity": "single_as_of",
            "product_cache": {
                "schema_version": 1,
                "contract_version": OPERATOR_SNAPSHOT_CONTRACT_VERSION,
                "status": "hit",
                "expected_local_trade_date": trade_date,
                "queue_as_of_trade_date": trade_date,
                "freshness": "current",
                "cache_path": str(snapshot.resolve()),
                "input_identity_contract_version": 1,
                "input_identity_fingerprint": fingerprint,
                "input_identity_stable_during_build": True,
            },
            "input_identity": identity,
            "authoritative_evidence": False,
            "writes_m4_evidence": False,
            "is_trade_instruction": False,
            "alpha_inference_allowed": False,
        },
    )
    pipeline = {
        "schema_version": 2,
        "generated_at_utc": "2026-09-18T09:00:00+00:00",
        "overall_status": "product_ready_research_degraded",
        "exit_code": 0,
        "market_data_ready": True,
        "m5_product_ready": True,
        "m5_initial_product_ready": True,
        "m5_final_cache_revalidated_after_research_lane": True,
        "m5_context_refresh_ready": True,
        "m4_research_ready": False,
        "steps": {},
        "artifacts": {
            "pipeline_report": "artifacts/reports/m5-daily-close-pipeline.json",
            "m5_operator_snapshot_report": (
                "artifacts/reports/m5-operator-snapshot.json"
            ),
            "m4_evidence_bundle": "artifacts/reports/m4-evidence-bundle.zip",
        },
    }
    _write_json(
        root / "artifacts" / "reports" / "m5-daily-close-pipeline.json",
        pipeline,
    )
    return pipeline, snapshot


def test_handoff_binds_exact_final_snapshot_not_latest_file(tmp_path: Path) -> None:
    pipeline, current = _prepare_product_ready(tmp_path)

    newer_unrelated = (
        tmp_path
        / "data"
        / "product"
        / "m5"
        / "operator_queue"
        / "2026-09-19__b420__s3-5-8-13.json"
    )
    _write_json(
        newer_unrelated,
        {
            "schema_version": 1,
            "contract_version": OPERATOR_SNAPSHOT_CONTRACT_VERSION,
            "expected_trade_date": "2026-09-19",
            "bars": 420,
            "scales": [3, 5, 8, 13],
            "input_identity": _identity(FP_B),
            "queue": {
                "as_of_trade_date": "2026-09-19",
                "observation_integrity": "single_as_of",
            },
            "authoritative_evidence": False,
            "writes_m4_evidence": False,
        },
    )

    output = tmp_path / "artifacts" / "reports" / "htcn-daily-handoff-v2.zip"
    payload = build_daily_handoff_bundle(
        root=tmp_path,
        pipeline_summary=pipeline,
        output=output,
    )

    assert payload["verification"]["status"] == "valid"
    assert payload["product_binding"]["trade_date"] == "2026-09-18"
    assert payload["product_binding"]["cache_path"] == str(current.resolve())

    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
    assert (
        "m5/operator_snapshots/2026-09-18__b420__s3-5-8-13.json"
        in names
    )
    assert (
        "m5/operator_snapshots/2026-09-19__b420__s3-5-8-13.json"
        not in names
    )


def test_handoff_rejects_report_snapshot_identity_mismatch(tmp_path: Path) -> None:
    pipeline, snapshot = _prepare_product_ready(tmp_path)
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    payload["input_identity"] = _identity(FP_B)
    _write_json(snapshot, payload)

    with pytest.raises(RuntimeError, match="input_identity_mismatch"):
        build_daily_handoff_bundle(
            root=tmp_path,
            pipeline_summary=pipeline,
            output=tmp_path / "handoff.zip",
        )


def test_handoff_rejects_cache_path_outside_operator_root(tmp_path: Path) -> None:
    pipeline, _ = _prepare_product_ready(tmp_path)
    report_path = (
        tmp_path / "artifacts" / "reports" / "m5-operator-snapshot.json"
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    outside = tmp_path / "artifacts" / "reports" / "fake.json"
    outside.write_text("{}", encoding="utf-8")
    report["product_cache"]["cache_path"] = str(outside.resolve())
    _write_json(report_path, report)

    with pytest.raises(RuntimeError, match="outside_root"):
        build_daily_handoff_bundle(
            root=tmp_path,
            pipeline_summary=pipeline,
            output=tmp_path / "handoff.zip",
        )


def test_handoff_requires_pipeline_file_to_match_payload(tmp_path: Path) -> None:
    pipeline, _ = _prepare_product_ready(tmp_path)
    pipeline["overall_status"] = "mutated_in_memory"

    with pytest.raises(RuntimeError, match="pipeline_report_payload_mismatch"):
        build_daily_handoff_bundle(
            root=tmp_path,
            pipeline_summary=pipeline,
            output=tmp_path / "handoff.zip",
        )


def test_product_ready_handoff_does_not_require_m4_bundle(tmp_path: Path) -> None:
    pipeline, _ = _prepare_product_ready(tmp_path)
    output = tmp_path / "handoff.zip"

    payload = build_daily_handoff_bundle(
        root=tmp_path,
        pipeline_summary=pipeline,
        output=output,
    )

    assert payload["status"] == "product_transport_research_degraded"
    assert payload["m5_product_ready"] is True
    assert payload["m4_research_ready"] is False
    assert payload["authoritative_evidence"] is False


def test_research_ready_requires_valid_nested_m4_bundle(tmp_path: Path) -> None:
    pipeline, _ = _prepare_product_ready(tmp_path)
    pipeline["m4_research_ready"] = True
    _write_json(
        tmp_path / "artifacts" / "reports" / "m5-daily-close-pipeline.json",
        pipeline,
    )

    with pytest.raises(RuntimeError, match="evidence_bundle_missing"):
        build_daily_handoff_bundle(
            root=tmp_path,
            pipeline_summary=pipeline,
            output=tmp_path / "handoff.zip",
        )


def test_handoff_verifier_detects_tampered_bound_snapshot(tmp_path: Path) -> None:
    pipeline, _ = _prepare_product_ready(tmp_path)
    output = tmp_path / "handoff.zip"
    build_daily_handoff_bundle(
        root=tmp_path,
        pipeline_summary=pipeline,
        output=output,
    )

    with zipfile.ZipFile(output, "a") as archive:
        archive.writestr(
            "m5/operator_snapshots/2026-09-18__b420__s3-5-8-13.json",
            b"tampered",
        )

    checked = verify_daily_handoff_bundle(output)
    assert checked.status == "invalid"
    assert checked.errors


def test_degraded_transport_can_exist_without_product_snapshot(
    tmp_path: Path,
) -> None:
    reports = tmp_path / "artifacts" / "reports"
    reports.mkdir(parents=True)
    pipeline = {
        "schema_version": 2,
        "generated_at_utc": "2026-09-18T09:00:00+00:00",
        "overall_status": "failed",
        "exit_code": 2,
        "market_data_ready": False,
        "m5_product_ready": False,
        "m4_research_ready": False,
        "steps": {},
        "artifacts": {
            "pipeline_report": "artifacts/reports/m5-daily-close-pipeline.json",
            "m5_operator_snapshot_report": (
                "artifacts/reports/m5-operator-snapshot.json"
            ),
            "m4_evidence_bundle": "artifacts/reports/m4-evidence-bundle.zip",
        },
    }
    _write_json(reports / "m5-daily-close-pipeline.json", pipeline)

    output = tmp_path / "handoff.zip"
    payload = build_daily_handoff_bundle(
        root=tmp_path,
        pipeline_summary=pipeline,
        output=output,
    )
    assert payload["status"] == "degraded_transport"
    assert verify_daily_handoff_bundle(output).status == "valid"
