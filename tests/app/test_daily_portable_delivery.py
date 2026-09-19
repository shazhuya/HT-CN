from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest

from htcn.app import daily_portable_delivery as delivery


IDENTITY = "a" * 64
PIPELINE_HASH_PLACEHOLDER = "b" * 64


def _v4_manifest(*, degraded: bool = False) -> dict:
    return {
        "schema_version": 4,
        "status": (
            "detail_transport_degraded"
            if degraded
            else "complete_detail_transport"
        ),
        "trade_date": "2026-09-19",
        "input_identity_fingerprint": IDENTITY,
        "detail_display_key_count": 3 if degraded else 5,
        "error_display_key_count": 2 if degraded else 0,
    }


def _valid_v4_result(path: str | Path, *, degraded: bool = False):
    return SimpleNamespace(
        status="valid",
        bundle_path=str(path),
        schema_version=4,
        file_count=5,
        queue_display_key_count=5,
        detail_display_key_count=3 if degraded else 5,
        error_display_key_count=2 if degraded else 0,
        errors=(),
        warnings=(),
        manifest=_v4_manifest(degraded=degraded),
    )


def _inspection(*, degraded: bool = False) -> dict:
    return {
        "schema_version": 2,
        "contract": {
            "version": 2,
            "semantics": "portable_pattern_visual_review_v2",
            "source_bundle_schema": 4,
            "visual_semantics_version": 2,
            "schema_specific_rendering": True,
            "layered_prz_rendering": True,
            "future_pattern_points_may_be_invented": False,
            "requires_market_database": False,
            "imports_product_state": False,
            "writes_review_journal": False,
            "creates_review_events": False,
            "writes_m4_evidence": False,
            "predictive_score_used": False,
            "historical_outcome_used_for_ranking": False,
            "alpha_inference_allowed": False,
            "is_trade_instruction": False,
        },
        "source": {
            "verification_status": "valid",
            "bundle_schema_version": 4,
        },
        "summary": {
            "status": (
                "detail_transport_degraded"
                if degraded
                else "complete_detail_transport"
            ),
            "trade_date": "2026-09-19",
            "queue_display_key_count": 5,
            "detail_display_key_count": 3 if degraded else 5,
            "error_display_key_count": 2 if degraded else 0,
            "detail_complete": not degraded,
        },
        "transport_manifest": _v4_manifest(degraded=degraded),
        "portable_items": [],
        "details_by_display_key": {},
        "detail_errors": [],
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "imports_product_state": False,
        "creates_review_events": False,
        "is_trade_instruction": False,
        "alpha_inference_allowed": False,
        "predictive_score_used": False,
        "historical_outcome_used_for_ranking": False,
    }


def _workspace_html() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>HT-CN v4 便携图形复盘</title></head>
<body>
<h1>HT-CN v4 便携图形复盘</h1>
<div>Visual Semantics v2</div>
<div>Source Raw PRZ</div>
<div>下一关键价导引，不是预测腿</div>
</body></html>
"""


def _write_workspace_outputs(
    *,
    json_output: str | Path,
    html_output: str | Path,
    degraded: bool = False,
) -> None:
    json_path = Path(json_output)
    html_path = Path(html_output)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(
            _inspection(degraded=degraded),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    html_path.write_text(_workspace_html(), encoding="utf-8")


def _patch_v4_verifier(
    monkeypatch: pytest.MonkeyPatch,
    *,
    degraded: bool = False,
) -> None:
    monkeypatch.setattr(
        delivery,
        "verify_daily_handoff_bundle_v4",
        lambda path: _valid_v4_result(path, degraded=degraded),
    )


def test_outer_portable_delivery_bundle_verifies_nested_v4_and_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_v4_verifier(monkeypatch)
    v4 = tmp_path / "v4.zip"
    v4.write_bytes(b"verified-v4")
    inspection = tmp_path / "inspection.json"
    workspace = tmp_path / "workspace.html"
    _write_workspace_outputs(
        json_output=inspection,
        html_output=workspace,
    )
    output = tmp_path / "delivery.zip"

    payload = delivery.build_daily_portable_delivery_bundle(
        v4_bundle=v4,
        inspection_json=inspection,
        workspace_html=workspace,
        pipeline_report_sha256=PIPELINE_HASH_PLACEHOLDER,
        output=output,
    )

    assert payload["status"] == "complete_portable_delivery"
    assert payload["detail_display_key_count"] == 5
    assert payload["error_display_key_count"] == 0
    checked = delivery.verify_daily_portable_delivery_bundle(output)
    assert checked.status == "valid"
    assert checked.trade_date == "2026-09-19"
    assert checked.nested_v4_status == "complete_detail_transport"

    with zipfile.ZipFile(output, "r") as archive:
        assert set(archive.namelist()) == {
            "daily-portable-delivery-manifest.json",
            "base/htcn-daily-handoff-v4.zip",
            "workspace/m5-handoff-v4-inspector.json",
            "workspace/m5-handoff-v4-pattern-workspace.html",
        }


def test_detail_degraded_v4_is_valid_explicit_degraded_delivery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_v4_verifier(monkeypatch, degraded=True)
    v4 = tmp_path / "v4.zip"
    v4.write_bytes(b"verified-v4-degraded")
    inspection = tmp_path / "inspection.json"
    workspace = tmp_path / "workspace.html"
    _write_workspace_outputs(
        json_output=inspection,
        html_output=workspace,
        degraded=True,
    )
    output = tmp_path / "delivery.zip"

    payload = delivery.build_daily_portable_delivery_bundle(
        v4_bundle=v4,
        inspection_json=inspection,
        workspace_html=workspace,
        pipeline_report_sha256=PIPELINE_HASH_PLACEHOLDER,
        output=output,
    )

    assert payload["status"] == "detail_degraded_portable_delivery"
    assert payload["detail_display_key_count"] == 3
    assert payload["error_display_key_count"] == 2
    checked = delivery.verify_daily_portable_delivery_bundle(output)
    assert checked.status == "valid"
    assert checked.error_display_key_count == 2


def test_outer_verifier_detects_semantic_inspector_tamper_even_with_new_hash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_v4_verifier(monkeypatch)
    v4 = tmp_path / "v4.zip"
    v4.write_bytes(b"verified-v4")
    inspection = tmp_path / "inspection.json"
    workspace = tmp_path / "workspace.html"
    _write_workspace_outputs(
        json_output=inspection,
        html_output=workspace,
    )
    original = tmp_path / "delivery.zip"
    delivery.build_daily_portable_delivery_bundle(
        v4_bundle=v4,
        inspection_json=inspection,
        workspace_html=workspace,
        pipeline_report_sha256=PIPELINE_HASH_PLACEHOLDER,
        output=original,
    )

    with zipfile.ZipFile(original, "r") as source:
        blobs = {
            info.filename: source.read(info.filename)
            for info in source.infolist()
        }

    inspector_name = "workspace/m5-handoff-v4-inspector.json"
    payload = json.loads(blobs[inspector_name].decode("utf-8"))
    payload["contract"]["writes_m4_evidence"] = True
    blobs[inspector_name] = (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")

    manifest = json.loads(
        blobs["daily-portable-delivery-manifest.json"].decode("utf-8")
    )
    for record in manifest["files"]:
        if record["arcname"] == inspector_name:
            record["size_bytes"] = len(blobs[inspector_name])
            record["sha256"] = sha256(blobs[inspector_name]).hexdigest()
    blobs["daily-portable-delivery-manifest.json"] = (
        json.dumps(
            manifest,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")

    tampered = tmp_path / "tampered.zip"
    with zipfile.ZipFile(
        tampered,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as target:
        for name, raw in blobs.items():
            target.writestr(name, raw)

    checked = delivery.verify_daily_portable_delivery_bundle(tampered)
    assert checked.status == "invalid"
    assert (
        "inspection_boundary_invalid:writes_m4_evidence"
        in checked.errors
    )


def _pipeline(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "m5_product_ready": True,
                "m5_history_ready": True,
                "m5_review_digest_ready": True,
                "m4_research_ready": False,
            },
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _fake_v3_runner(**kwargs):
    output = Path(kwargs["output"])
    report = Path(kwargs["report"])
    output.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b"fake-v3")
    report.write_text(
        json.dumps({"status": "ready"}) + "\n",
        encoding="utf-8",
    )
    return {"status": "ready", "error": None}, 0


def _fake_v4_builder(*, output, **kwargs):
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fake-v4")
    return {
        **_v4_manifest(),
        "output": str(path),
        "bundle_sha256": sha256(b"fake-v4").hexdigest(),
    }


def _fake_workspace_writer(
    *,
    json_output,
    html_output,
    **kwargs,
):
    _write_workspace_outputs(
        json_output=json_output,
        html_output=html_output,
    )
    return {"status": "ready"}


def _run_paths(root: Path) -> dict[str, Path]:
    reports = root / "artifacts" / "reports"
    return {
        "pipeline_report": reports / "m5-daily-close-pipeline.json",
        "output": reports / "htcn-daily-portable-delivery-v1.zip",
        "run_report": reports / "m5-daily-portable-delivery-run.json",
        "latest_pointer": reports / "m5-daily-portable-delivery-latest.json",
        "latest_v4_alias": reports / "m5-daily-portable-v4.zip",
        "latest_inspector_alias": reports / "m5-daily-portable-inspector.json",
        "latest_workspace_alias": reports / "m5-daily-portable-workspace.html",
        "archive_root": root / "artifacts" / "deliveries" / "m5",
    }


def test_daily_delivery_success_publishes_archive_aliases_and_pointer_last(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_v4_verifier(monkeypatch)
    paths = _run_paths(tmp_path)
    _pipeline(paths["pipeline_report"])

    # Sentinel frozen aliases from older phases must remain untouched.
    frozen_v3 = tmp_path / "artifacts" / "reports" / "htcn-daily-handoff-v3.zip"
    frozen_v4 = tmp_path / "artifacts" / "reports" / "htcn-daily-handoff-v4.zip"
    frozen_v3.write_bytes(b"phase14-frozen")
    frozen_v4.write_bytes(b"phase16-frozen")

    payload, code = delivery.run_daily_portable_delivery(
        root=tmp_path,
        **paths,
        v3_runner=_fake_v3_runner,
        v4_builder=_fake_v4_builder,
        workspace_writer=_fake_workspace_writer,
        identity_factory=lambda repo: IDENTITY,
        provider_factory=lambda repo: object(),
    )

    assert code == 0
    assert payload["status"] == "complete_portable_delivery"
    assert payload["pipeline_report_unchanged"] is True
    assert paths["output"].is_file()
    assert paths["latest_pointer"].is_file()
    assert paths["latest_v4_alias"].read_bytes() == b"fake-v4"
    assert paths["latest_workspace_alias"].is_file()
    assert frozen_v3.read_bytes() == b"phase14-frozen"
    assert frozen_v4.read_bytes() == b"phase16-frozen"

    latest = json.loads(
        paths["latest_pointer"].read_text(encoding="utf-8")
    )
    archive_dir = tmp_path / latest["archive_dir"]
    assert archive_dir.is_dir()
    assert (
        archive_dir / "htcn-daily-portable-delivery-v1.zip"
    ).is_file()
    assert (archive_dir / "htcn-daily-handoff-v4.zip").is_file()
    assert (archive_dir / "m5-portable-delivery-archive.json").is_file()
    assert not any(
        child.name.startswith(".")
        for child in archive_dir.parent.iterdir()
        if child.is_dir()
    )


def test_v4_failure_preserves_previous_successful_pointer_and_aliases(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_v4_verifier(monkeypatch)
    paths = _run_paths(tmp_path)
    _pipeline(paths["pipeline_report"])
    for key in (
        "output",
        "latest_pointer",
        "latest_v4_alias",
        "latest_inspector_alias",
        "latest_workspace_alias",
    ):
        path = paths[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"previous-success")

    def fail_v4(**kwargs):
        raise RuntimeError("synthetic-v4-failure")

    payload, code = delivery.run_daily_portable_delivery(
        root=tmp_path,
        **paths,
        v3_runner=_fake_v3_runner,
        v4_builder=fail_v4,
        workspace_writer=_fake_workspace_writer,
        identity_factory=lambda repo: IDENTITY,
        provider_factory=lambda repo: object(),
    )

    assert code == 2
    assert payload["status"] == "failed"
    assert payload["failed_stage"] == "handoff_v4"
    for key in (
        "output",
        "latest_pointer",
        "latest_v4_alias",
        "latest_inspector_alias",
        "latest_workspace_alias",
    ):
        assert paths[key].read_bytes() == b"previous-success"


def test_pipeline_drift_blocks_promotion_and_preserves_latest_pointer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_v4_verifier(monkeypatch)
    paths = _run_paths(tmp_path)
    _pipeline(paths["pipeline_report"])
    paths["latest_pointer"].parent.mkdir(parents=True, exist_ok=True)
    paths["latest_pointer"].write_bytes(b"previous-pointer")

    def drift_workspace(*, json_output, html_output, **kwargs):
        _write_workspace_outputs(
            json_output=json_output,
            html_output=html_output,
        )
        with paths["pipeline_report"].open("a", encoding="utf-8") as handle:
            handle.write(" ")
        return {"status": "ready"}

    payload, code = delivery.run_daily_portable_delivery(
        root=tmp_path,
        **paths,
        v3_runner=_fake_v3_runner,
        v4_builder=_fake_v4_builder,
        workspace_writer=drift_workspace,
        identity_factory=lambda repo: IDENTITY,
        provider_factory=lambda repo: object(),
    )

    assert code == 2
    assert payload["failed_stage"] == "pipeline_stability"
    assert payload["pipeline_report_unchanged"] is False
    assert paths["latest_pointer"].read_bytes() == b"previous-pointer"
    assert not paths["output"].exists()


def test_v3_failure_short_circuits_before_v4(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_v4_verifier(monkeypatch)
    paths = _run_paths(tmp_path)
    _pipeline(paths["pipeline_report"])
    called = {"v4": False}

    def fail_v3(**kwargs):
        return {"status": "failed", "error": "synthetic-v3"}, 2

    def should_not_run_v4(**kwargs):
        called["v4"] = True
        raise AssertionError("v4 must not run")

    payload, code = delivery.run_daily_portable_delivery(
        root=tmp_path,
        **paths,
        v3_runner=fail_v3,
        v4_builder=should_not_run_v4,
        workspace_writer=_fake_workspace_writer,
        identity_factory=lambda repo: IDENTITY,
        provider_factory=lambda repo: object(),
    )

    assert code == 2
    assert payload["failed_stage"] == "handoff_v3"
    assert called["v4"] is False
    assert not paths["output"].exists()



def test_product_not_ready_fails_before_v3(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_v4_verifier(monkeypatch)
    paths = _run_paths(tmp_path)
    paths["pipeline_report"].parent.mkdir(parents=True, exist_ok=True)
    paths["pipeline_report"].write_text(
        json.dumps({"schema_version": 2, "m5_product_ready": False}) + "\n",
        encoding="utf-8",
    )
    called = {"v3": False}

    def should_not_run_v3(**kwargs):
        called["v3"] = True
        raise AssertionError("v3 must not run")

    payload, code = delivery.run_daily_portable_delivery(
        root=tmp_path,
        **paths,
        v3_runner=should_not_run_v3,
        v4_builder=_fake_v4_builder,
        workspace_writer=_fake_workspace_writer,
        identity_factory=lambda repo: IDENTITY,
        provider_factory=lambda repo: object(),
    )

    assert code == 2
    assert payload["failed_stage"] == "pipeline_preflight"
    assert "pipeline_m5_product_not_ready" in str(payload["error"])
    assert called["v3"] is False
    assert not paths["output"].exists()


def test_workspace_failure_preserves_previous_successful_delivery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_v4_verifier(monkeypatch)
    paths = _run_paths(tmp_path)
    _pipeline(paths["pipeline_report"])
    for key in (
        "output",
        "latest_pointer",
        "latest_workspace_alias",
    ):
        path = paths[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"previous-success")

    def fail_workspace(**kwargs):
        raise RuntimeError("synthetic-workspace-failure")

    payload, code = delivery.run_daily_portable_delivery(
        root=tmp_path,
        **paths,
        v3_runner=_fake_v3_runner,
        v4_builder=_fake_v4_builder,
        workspace_writer=fail_workspace,
        identity_factory=lambda repo: IDENTITY,
        provider_factory=lambda repo: object(),
    )

    assert code == 2
    assert payload["failed_stage"] == "workspace"
    assert paths["output"].read_bytes() == b"previous-success"
    assert paths["latest_pointer"].read_bytes() == b"previous-success"
    assert (
        paths["latest_workspace_alias"].read_bytes()
        == b"previous-success"
    )
