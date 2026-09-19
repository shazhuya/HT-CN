from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from htcn.app.daily_handoff_v3 import build_daily_handoff_bundle_v3

HANDOFF_V3_RUN_REPORT_SCHEMA_VERSION = 1
BuildBundleV3 = Callable[..., dict[str, Any]]


def _sha256_path(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("pipeline report must be a JSON object")
    return value


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    encoded = (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    )
    tmp.write_text(encoded, encoding="utf-8")
    tmp.replace(path)


def run_daily_handoff_bundle_v3(
    *,
    root: str | Path,
    pipeline_report: str | Path,
    output: str | Path,
    report: str | Path,
    builder: BuildBundleV3 = build_daily_handoff_bundle_v3,
) -> tuple[dict[str, Any], int]:
    repo = Path(root).resolve()

    pipeline_path = Path(pipeline_report)
    if not pipeline_path.is_absolute():
        pipeline_path = repo / pipeline_path
    pipeline_path = pipeline_path.resolve()

    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = repo / output_path
    output_path = output_path.resolve()

    report_path = Path(report)
    if not report_path.is_absolute():
        report_path = repo / report_path
    report_path = report_path.resolve()

    if report_path == pipeline_path:
        raise ValueError(
            "handoff v3 report path must not replace pipeline report"
        )
    if output_path == pipeline_path:
        raise ValueError(
            "handoff v3 output path must not replace pipeline report"
        )
    if output_path == report_path:
        raise ValueError(
            "handoff v3 output and report paths must be distinct"
        )

    generated_at = datetime.now(UTC).isoformat()
    pipeline_payload: dict[str, Any] | None = None
    before_hash: str | None = None
    after_hash: str | None = None
    error: str | None = None
    bundle: dict[str, Any] | None = None

    try:
        before_hash = _sha256_path(pipeline_path)
        pipeline_payload = _read_json_object(pipeline_path)
        bundle = builder(
            root=repo,
            pipeline_summary=pipeline_payload,
            output=output_path,
        )
        exit_code = 0
        status = "ready"
    except Exception as exc:
        exit_code = 2
        status = "failed"
        error = f"{type(exc).__name__}:{exc}"
    finally:
        if pipeline_path.is_file():
            after_hash = _sha256_path(pipeline_path)

    pipeline_unchanged = (
        before_hash is not None
        and after_hash is not None
        and before_hash == after_hash
    )
    payload: dict[str, Any] = {
        "schema_version": HANDOFF_V3_RUN_REPORT_SCHEMA_VERSION,
        "generated_at_utc": generated_at,
        "status": status,
        "exit_code": exit_code,
        "pipeline_report": str(pipeline_path),
        "pipeline_report_sha256_before": before_hash,
        "pipeline_report_sha256_after": after_hash,
        "pipeline_report_unchanged": pipeline_unchanged,
        "pipeline_m5_product_ready": (
            None
            if pipeline_payload is None
            else pipeline_payload.get("m5_product_ready")
        ),
        "pipeline_m5_history_ready": (
            None
            if pipeline_payload is None
            else pipeline_payload.get("m5_history_ready")
        ),
        "pipeline_m5_review_digest_ready": (
            None
            if pipeline_payload is None
            else pipeline_payload.get("m5_review_digest_ready")
        ),
        "pipeline_m4_research_ready": (
            None
            if pipeline_payload is None
            else pipeline_payload.get("m4_research_ready")
        ),
        "transport_failure_does_not_rewrite_pipeline_readiness": True,
        "phase10_handoff_v2_is_not_overwritten": True,
        "transport_only": True,
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "is_trade_instruction": False,
        "alpha_inference_allowed": False,
        "predictive_score_used": False,
        "historical_outcome_used_for_ranking": False,
        "output": str(output_path),
        "error": error,
        "bundle": bundle,
    }
    _write_json_atomic(report_path, payload)
    return payload, exit_code
