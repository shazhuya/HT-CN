from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from htcn.app.operator_input_identity import OperatorCacheInputIdentity
from htcn.app.operator_queue import AnalysisService, AnalysisServiceFactory
from htcn.app.operator_snapshot import (
    build_or_load_operator_snapshot,
    operator_universe_hash,
)

SnapshotBuilder = Callable[..., dict[str, Any]]


@dataclass(frozen=True, slots=True)
class AnalysisRuntimeDecision:
    due: bool
    reason: str
    target_trade_date: str | None
    input_identity_fingerprint: str
    last_success_trade_date: str | None
    last_success_input_identity_fingerprint: str | None

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


def _clean_optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def evaluate_harmonic_analysis_schedule(
    *,
    target_trade_date: object,
    input_identity_fingerprint: str,
    last_success_trade_date: object = None,
    last_success_input_identity_fingerprint: object = None,
    force: bool = False,
) -> AnalysisRuntimeDecision:
    target = _clean_optional_text(target_trade_date)
    current_fingerprint = str(input_identity_fingerprint).strip()
    previous_trade_date = _clean_optional_text(last_success_trade_date)
    previous_fingerprint = _clean_optional_text(
        last_success_input_identity_fingerprint
    )

    if not current_fingerprint:
        raise ValueError("analysis runtime input identity fingerprint is required")

    if target is None:
        return AnalysisRuntimeDecision(
            due=False,
            reason="target_trade_date_unresolved",
            target_trade_date=None,
            input_identity_fingerprint=current_fingerprint,
            last_success_trade_date=previous_trade_date,
            last_success_input_identity_fingerprint=previous_fingerprint,
        )

    if force:
        reason = "forced"
        due = True
    elif previous_trade_date != target:
        reason = "new_canonical_trade_session"
        due = True
    elif previous_fingerprint != current_fingerprint:
        reason = "canonical_input_changed"
        due = True
    else:
        reason = "already_current"
        due = False

    return AnalysisRuntimeDecision(
        due=due,
        reason=reason,
        target_trade_date=target,
        input_identity_fingerprint=current_fingerprint,
        last_success_trade_date=previous_trade_date,
        last_success_input_identity_fingerprint=previous_fingerprint,
    )


def _validate_product_boundaries(queue: dict[str, Any]) -> None:
    contract = queue.get("contract")
    if not isinstance(contract, dict):
        raise ValueError("analysis runtime queue contract missing")
    for field in (
        "predictive_score_used",
        "historical_outcome_used",
        "alpha_inference_allowed",
        "is_trade_instruction",
        "mutates_harmonic_identity",
        "mutates_source_raw_prz",
        "owns_lifecycle",
    ):
        if contract.get(field) is not False:
            raise ValueError(f"analysis runtime queue boundary violation: {field}")

    cache = queue.get("product_cache")
    if not isinstance(cache, dict):
        raise ValueError("analysis runtime product-cache metadata missing")
    if cache.get("authoritative_evidence") is not False:
        raise ValueError("analysis runtime must not become authoritative evidence")
    if cache.get("writes_m4_evidence") is not False:
        raise ValueError("analysis runtime must not write M4 evidence")


def build_analysis_runtime_provenance(
    *,
    expected_trade_date: str,
    input_identity: OperatorCacheInputIdentity,
    instrument_ids: Iterable[str],
    bars: int,
    scales: tuple[int, ...],
) -> dict[str, object]:
    instruments = [str(value) for value in instrument_ids]
    return {
        "contract_version": 1,
        "runtime_role": "product_analysis_orchestration_only",
        "analysis_service": "M3SourceClockHarmonicService",
        "source_of_truth": "existing_source_lifecycle_and_decision_narrative",
        "expected_trade_date": str(expected_trade_date),
        "bars": int(bars),
        "scales": [int(value) for value in scales],
        "universe_hash": operator_universe_hash(instruments),
        "instrument_count": len(instruments),
        "input_identity": input_identity.as_payload(),
        "viewport_inputs_used": False,
        "viewport_can_trigger_analysis": False,
        "runtime_synthesizes_future_nodes": False,
        "runtime_mutates_harmonic_identity": False,
        "runtime_mutates_source_raw_prz": False,
        "runtime_owns_lifecycle": False,
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
    }


def execute_harmonic_analysis_cycle(
    service: AnalysisService,
    instrument_ids: Iterable[str],
    *,
    cache_root: str | Path,
    expected_trade_date: str,
    input_identity: OperatorCacheInputIdentity,
    input_identity_factory: Callable[[], OperatorCacheInputIdentity] | None = None,
    bars: int = 420,
    scales: tuple[int, ...] = (3, 5, 8, 13),
    force_refresh: bool = False,
    max_workers: int = 1,
    service_factory: AnalysisServiceFactory | None = None,
    snapshot_builder: SnapshotBuilder = build_or_load_operator_snapshot,
) -> dict[str, object]:
    instruments = [str(value) for value in instrument_ids]
    if not instruments:
        raise ValueError("analysis runtime requires at least one initialized instrument")

    queue = snapshot_builder(
        service,
        instruments,
        cache_root=cache_root,
        expected_trade_date=str(expected_trade_date),
        input_identity=input_identity,
        input_identity_factory=input_identity_factory,
        bars=int(bars),
        scales=tuple(int(value) for value in scales),
        force_refresh=bool(force_refresh),
        max_workers=max(1, int(max_workers)),
        service_factory=service_factory,
    )
    _validate_product_boundaries(queue)

    product_cache = dict(queue.get("product_cache") or {})
    freshness = str(product_cache.get("freshness") or "")
    stable_during_build = product_cache.get("input_identity_stable_during_build")
    observation_integrity = str(queue.get("observation_integrity") or "")
    queue_as_of = _clean_optional_text(queue.get("as_of_trade_date"))
    expected = str(expected_trade_date)

    if freshness != "current":
        raise ValueError(
            f"analysis runtime snapshot is not current: freshness={freshness or 'missing'}"
        )
    if stable_during_build is not True:
        raise ValueError("analysis runtime input identity changed during build")
    if observation_integrity != "single_as_of":
        raise ValueError(
            "analysis runtime requires single_as_of observation integrity"
        )
    if queue_as_of != expected:
        raise ValueError(
            f"analysis runtime trade-date mismatch: expected={expected} observed={queue_as_of}"
        )

    failed = int(queue.get("failed_instrument_count") or 0)
    analyzed = int(queue.get("analyzed_instrument_count") or 0)
    candidate_count = int(queue.get("candidate_count") or 0)
    healthy = failed == 0 and analyzed == len(instruments)
    overall_status = "healthy" if healthy else "degraded"

    diagnostics_zh = [
        (
            "谐波分析运行时已覆盖全部初始化标的，当前交易日分析缓存可用。"
            if healthy
            else "谐波分析运行时已完成本轮扫描，但存在标的分析失败；不会推进成功水位，将自动重试。"
        )
    ]
    if failed:
        diagnostics_zh.append(f"失败标的数量：{failed}。")

    return {
        "schema_version": 1,
        "overall_status": overall_status,
        "healthy": healthy,
        "retry_required": not healthy,
        "target_trade_date": expected,
        "instrument_count": len(instruments),
        "analyzed_instrument_count": analyzed,
        "failed_instrument_count": failed,
        "candidate_count": candidate_count,
        "queue_cache": product_cache,
        "provenance": build_analysis_runtime_provenance(
            expected_trade_date=expected,
            input_identity=input_identity,
            instrument_ids=instruments,
            bars=bars,
            scales=scales,
        ),
        "diagnostics_zh": diagnostics_zh,
    }


def empty_harmonic_analysis_runtime_status() -> dict[str, object]:
    return {
        "schema_version": 1,
        "service": "m9_harmonic_analysis_runtime",
        "status": "not_started",
        "healthy": False,
        "target_trade_date": None,
        "last_success_trade_date": None,
        "last_success_input_identity_fingerprint": None,
        "last_cycle_started_at_utc": None,
        "last_cycle_finished_at_utc": None,
        "next_check_at_utc": None,
        "schedule": None,
        "cycle": None,
        "diagnostics_zh": ["自动谐波分析运行时尚未产生运行状态。"],
    }


def read_harmonic_analysis_runtime_status(path: str | Path) -> dict[str, object]:
    status_path = Path(path)
    if not status_path.exists():
        return empty_harmonic_analysis_runtime_status()
    try:
        payload = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fallback = empty_harmonic_analysis_runtime_status()
        fallback["status"] = "status_unreadable"
        fallback["diagnostics_zh"] = [
            f"自动谐波分析运行时状态文件不可读：{type(exc).__name__}"
        ]
        return fallback
    if not isinstance(payload, dict):
        fallback = empty_harmonic_analysis_runtime_status()
        fallback["status"] = "status_invalid"
        fallback["diagnostics_zh"] = ["自动谐波分析运行时状态文件格式无效。"]
        return fallback
    return payload


def write_harmonic_analysis_runtime_status(
    path: str | Path,
    payload: dict[str, Any],
) -> Path:
    status_path = Path(path)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = status_path.with_suffix(status_path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(status_path)
    return status_path
