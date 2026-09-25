from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from threading import local
from typing import Any, Protocol

WORKFLOW_BUCKET_ORDER: dict[str, int] = {
    "execution_evaluation": 0,
    "reaction_observation": 1,
    "waiting": 2,
    "evidence_insufficient": 3,
}


class AnalysisService(Protocol):
    def analyze(
        self,
        instrument_id: str,
        *,
        bars: int,
        scales: tuple[int, ...],
    ) -> dict[str, Any]: ...


AnalysisServiceFactory = Callable[[], AnalysisService]
OperatorProgressCallback = Callable[[int, int, str, bool], None]


@dataclass(frozen=True, slots=True)
class OperatorQueueContract:
    version: int = 2
    source_of_truth: str = "source_lifecycle_plus_non_authoritative_discovery"
    ranking_mode: str = "workflow_bucket_only"
    predictive_score_used: bool = False
    historical_outcome_used: bool = False
    alpha_inference_allowed: bool = False
    is_trade_instruction: bool = False
    mutates_harmonic_identity: bool = False
    mutates_source_raw_prz: bool = False
    owns_lifecycle: bool = False

    def as_payload(self) -> dict[str, object]:
        return {
            "version": self.version,
            "source_of_truth": self.source_of_truth,
            "ranking_mode": self.ranking_mode,
            "predictive_score_used": self.predictive_score_used,
            "historical_outcome_used": self.historical_outcome_used,
            "alpha_inference_allowed": self.alpha_inference_allowed,
            "is_trade_instruction": self.is_trade_instruction,
            "mutates_harmonic_identity": self.mutates_harmonic_identity,
            "mutates_source_raw_prz": self.mutates_source_raw_prz,
            "owns_lifecycle": self.owns_lifecycle,
        }


def discover_local_instruments(
    data_root: str | Path,
    *,
    limit: int = 0,
    exchanges: tuple[str, ...] | None = None,
) -> list[str]:
    daily_root = Path(data_root) / "daily"
    if not daily_root.exists():
        return []
    items = sorted(path.stem for path in daily_root.glob("*.parquet"))
    if exchanges is not None:
        prefixes = tuple(
            f"{str(exchange).strip().upper()}."
            for exchange in exchanges
            if str(exchange).strip()
        )
        items = [
            item
            for item in items
            if prefixes and item.upper().startswith(prefixes)
        ]
    return items if limit <= 0 else items[:limit]


def _display_key(instrument_id: str, pattern: dict[str, Any]) -> str:
    """Stable product identity for comparing queue observations.

    Trade dates are preferred because rolling a fixed-size chart window can
    renumber bar indexes even when the underlying harmonic candidate is the
    same. This key is product-only and does not replace M4 candidate identity.
    """
    points = pattern.get("points") or []
    signature_parts: list[str] = []
    for point in points:
        trade_date = str(point.get("trade_date") or "").strip()
        if trade_date:
            signature_parts.append(trade_date)
        elif point.get("index") is not None:
            signature_parts.append(f"i{point.get('index')}")
    point_signature = "-".join(signature_parts)
    return (
        f"{instrument_id}:{pattern.get('pattern_id')}:{pattern.get('schema')}:"
        f"{pattern.get('direction')}:S{pattern.get('scale')}:{point_signature}"
    )


def _primary_patterns(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    authoritative = [
        *(analysis.get("completed") or []),
        *(analysis.get("forming") or []),
    ]
    discovery = sorted(
        (analysis.get("discovery") or []),
        key=lambda pattern: (
            -int(((pattern.get("points") or [{}])[-1]).get("index") or -1),
            str(pattern.get("pattern_id") or ""),
        ),
    )[:3]
    patterns = [*authoritative, *discovery]
    return [
        dict(pattern)
        for pattern in patterns
        if pattern.get("is_primary_identity") is not False
    ]


def _queue_item(
    *,
    instrument_id: str,
    analysis: dict[str, Any],
    pattern: dict[str, Any],
) -> dict[str, Any] | None:
    if pattern.get("discovery_only") is True:
        discovery = pattern.get("discovery") or {}
        prz = pattern.get("prz") or {}
        source_prz = prz.get("source_prz") or {}
        status = str(discovery.get("prz_status") or "projected")
        path_kind = str(discovery.get("path_kind") or "consecutive")
        source_low = source_prz.get("price_low", prz.get("source_prz_low"))
        source_high = source_prz.get("price_high", prz.get("source_prz_high"))
        return {
            "display_key": _display_key(instrument_id, pattern),
            "instrument_id": instrument_id,
            "last_trade_date": analysis.get("last_trade_date"),
            "price_mode": analysis.get("price_mode"),
            "warning": analysis.get("warning"),
            "pattern_id": pattern.get("pattern_id"),
            "schema": pattern.get("schema"),
            "direction": pattern.get("direction"),
            "scale": pattern.get("scale"),
            "pattern_state": "discovery",
            "discovery_only": True,
            "action_state": "evidence_insufficient",
            "workflow_bucket_order": WORKFLOW_BUCKET_ORDER["evidence_insufficient"],
            "lifecycle_state": "discovery_candidate",
            "state_reason": (
                "XABC discovery candidate; Source lifecycle has not started."
            ),
            "current_position": (
                "发现候选已在 C 确认后测试 Source PRZ。"
                if status == "tested"
                else "发现候选已投影 Source PRZ，尚未在可观察时钟内测试。"
            ),
            "first_watch": "先观察投影 Source PRZ；不得虚构 D 或 Source Terminal。",
            "next_watch": "只有权威 identity / Source Clock 成立后才进入正式生命周期。",
            "upgrade_blocker": "Discovery 不是 canonical identity，不能用排名或评分升级。",
            "next_key_price": None,
            "next_key_price_role": None,
            "execution_context_gate": "discovery_only",
            "context_cautions": [
                "minor_swing_skip" if path_kind == "minor_swing_skip" else "consecutive_path"
            ],
            "source_prz_low": source_low,
            "source_prz_high": source_high,
            "bars_since_terminal": None,
            "is_trade_instruction": False,
            "predictive_score_used": False,
            "alpha_inference_allowed": False,
        }

    lifecycle = pattern.get("source_lifecycle")
    narrative = pattern.get("decision_narrative")
    if not isinstance(lifecycle, dict) or not isinstance(narrative, dict):
        return None

    action_state = str(
        narrative.get("action_state") or "evidence_insufficient"
    )
    lifecycle_state = str(
        lifecycle.get("state") or "source_clock_unavailable"
    )
    if action_state not in WORKFLOW_BUCKET_ORDER:
        action_state = "evidence_insufficient"

    return {
        "display_key": _display_key(instrument_id, pattern),
        "instrument_id": instrument_id,
        "last_trade_date": analysis.get("last_trade_date"),
        "price_mode": analysis.get("price_mode"),
        "warning": analysis.get("warning"),
        "pattern_id": pattern.get("pattern_id"),
        "schema": pattern.get("schema"),
        "direction": pattern.get("direction"),
        "scale": pattern.get("scale"),
        "pattern_state": pattern.get("state"),
        "action_state": action_state,
        "workflow_bucket_order": WORKFLOW_BUCKET_ORDER[action_state],
        "lifecycle_state": lifecycle_state,
        "state_reason": lifecycle.get("state_reason"),
        "current_position": narrative.get("current_position"),
        "first_watch": narrative.get("first_watch"),
        "next_watch": narrative.get("next_watch"),
        "upgrade_blocker": narrative.get("upgrade_blocker"),
        "next_key_price": narrative.get("next_key_price"),
        "next_key_price_role": narrative.get("next_key_price_role"),
        "execution_context_gate": narrative.get("execution_context_gate"),
        "context_cautions": list(narrative.get("context_cautions") or []),
        "source_prz_low": lifecycle.get("source_prz_low"),
        "source_prz_high": lifecycle.get("source_prz_high"),
        "bars_since_terminal": lifecycle.get("bars_since_terminal"),
        "is_trade_instruction": False,
        "predictive_score_used": False,
        "alpha_inference_allowed": False,
    }


def build_operator_queue(
    service: AnalysisService,
    instrument_ids: Iterable[str],
    *,
    bars: int = 420,
    scales: tuple[int, ...] = (3, 5, 8, 13),
    include_evidence_insufficient: bool = True,
    max_workers: int = 1,
    service_factory: AnalysisServiceFactory | None = None,
    progress_callback: OperatorProgressCallback | None = None,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    analyzed = 0
    observed_trade_dates: set[str] = set()

    instrument_list = [str(value) for value in instrument_ids]
    requested_workers = max(1, int(max_workers))
    parallel_requested = requested_workers > 1 and len(instrument_list) > 1
    parallel_enabled = parallel_requested and service_factory is not None
    effective_workers = (
        min(requested_workers, len(instrument_list))
        if parallel_enabled
        else 1
    )
    fallback_reason = (
        "service_factory_required_for_parallel_isolation"
        if parallel_requested and service_factory is None
        else None
    )
    thread_state = local()

    def worker_service() -> AnalysisService:
        if not parallel_enabled or service_factory is None:
            return service
        instance = getattr(thread_state, "service", None)
        if instance is None:
            instance = service_factory()
            thread_state.service = instance
        return instance

    def analyze_one(
        instrument_id: str,
    ) -> tuple[str, dict[str, Any] | None, str | None]:
        try:
            analysis = worker_service().analyze(
                instrument_id,
                bars=bars,
                scales=scales,
            )
            return instrument_id, analysis, None
        except Exception as exc:
            return (
                instrument_id,
                None,
                f"{type(exc).__name__}: {exc}",
            )

    def emit_progress(
        completed: int,
        instrument_id: str,
        ok: bool,
    ) -> None:
        if progress_callback is None:
            return
        try:
            progress_callback(
                completed,
                len(instrument_list),
                instrument_id,
                ok,
            )
        except Exception:
            # Product progress reporting must never alter queue semantics.
            return

    if parallel_enabled:
        with ThreadPoolExecutor(
            max_workers=effective_workers,
            thread_name_prefix="htcn-operator",
        ) as executor:
            futures = {
                executor.submit(analyze_one, instrument_id): instrument_id
                for instrument_id in instrument_list
            }
            results = (
                future.result()
                for future in as_completed(futures)
            )
            for completed, result in enumerate(results, start=1):
                instrument_id, analysis, error = result
                if analysis is None:
                    errors.append({
                        "instrument_id": instrument_id,
                        "error": error or "unknown analysis error",
                    })
                    emit_progress(completed, instrument_id, False)
                    continue
                analyzed += 1
                last_trade_date = str(
                    analysis.get("last_trade_date") or ""
                ).strip()
                if last_trade_date:
                    observed_trade_dates.add(last_trade_date)
                for pattern in _primary_patterns(analysis):
                    item = _queue_item(
                        instrument_id=instrument_id,
                        analysis=analysis,
                        pattern=pattern,
                    )
                    if item is None:
                        continue
                    if (
                        not include_evidence_insufficient
                        and item["action_state"] == "evidence_insufficient"
                    ):
                        continue
                    items.append(item)
                emit_progress(completed, instrument_id, True)
    else:
        for completed, instrument_id in enumerate(
            instrument_list,
            start=1,
        ):
            _, analysis, error = analyze_one(instrument_id)
            if analysis is None:
                errors.append({
                    "instrument_id": instrument_id,
                    "error": error or "unknown analysis error",
                })
                emit_progress(completed, instrument_id, False)
                continue
            analyzed += 1
            last_trade_date = str(
                analysis.get("last_trade_date") or ""
            ).strip()
            if last_trade_date:
                observed_trade_dates.add(last_trade_date)
            for pattern in _primary_patterns(analysis):
                item = _queue_item(
                    instrument_id=instrument_id,
                    analysis=analysis,
                    pattern=pattern,
                )
                if item is None:
                    continue
                if (
                    not include_evidence_insufficient
                    and item["action_state"] == "evidence_insufficient"
                ):
                    continue
                items.append(item)
            emit_progress(completed, instrument_id, True)

    items.sort(
        key=lambda item: (
            int(item["workflow_bucket_order"]),
            str(item["instrument_id"]),
            str(item["display_key"]),
        )
    )

    action_counts = Counter(str(item["action_state"]) for item in items)
    lifecycle_counts = Counter(str(item["lifecycle_state"]) for item in items)
    instrument_with_candidates = len({
        str(item["instrument_id"]) for item in items
    })

    sorted_trade_dates = sorted(observed_trade_dates)
    as_of_trade_date = (
        sorted_trade_dates[0]
        if len(sorted_trade_dates) == 1
        else None
    )
    observation_integrity = (
        "single_as_of"
        if len(sorted_trade_dates) == 1
        else ("empty" if not sorted_trade_dates else "mixed_as_of")
    )

    return {
        "schema_version": 2,
        "contract": OperatorQueueContract().as_payload(),
        "build_execution": {
            "mode": (
                "parallel_thread_pool"
                if parallel_enabled
                else "sequential"
            ),
            "requested_max_workers": requested_workers,
            "effective_max_workers": effective_workers,
            "service_isolation": (
                "thread_local_service_factory"
                if parallel_enabled
                else "single_service"
            ),
            "parallel_fallback_reason": fallback_reason,
            "changes_queue_semantics": False,
            "authoritative_evidence": False,
            "writes_m4_evidence": False,
        },
        "as_of_trade_date": as_of_trade_date,
        "observed_trade_dates": sorted_trade_dates,
        "observation_integrity": observation_integrity,
        "instrument_count": len(instrument_list),
        "analyzed_instrument_count": analyzed,
        "failed_instrument_count": len(errors),
        "candidate_count": len(items),
        "candidate_instrument_count": instrument_with_candidates,
        "action_state_counts": dict(sorted(action_counts.items())),
        "lifecycle_state_counts": dict(sorted(lifecycle_counts.items())),
        "items": items,
        "errors": errors,
    }


def filter_operator_queue_payload(
    payload: dict[str, Any],
    *,
    include_evidence_insufficient: bool,
) -> dict[str, Any]:
    """Return a presentation-only filtered copy without changing snapshot identity."""
    if include_evidence_insufficient:
        return dict(payload)

    out = dict(payload)
    items = [
        dict(item)
        for item in (payload.get("items") or [])
        if str(item.get("action_state") or "") != "evidence_insufficient"
    ]
    out["items"] = items
    out["candidate_count"] = len(items)
    out["candidate_instrument_count"] = len({
        str(item.get("instrument_id") or "")
        for item in items
        if item.get("instrument_id")
    })
    out["action_state_counts"] = dict(sorted(Counter(
        str(item.get("action_state") or "")
        for item in items
    ).items()))
    out["lifecycle_state_counts"] = dict(sorted(Counter(
        str(item.get("lifecycle_state") or "")
        for item in items
    ).items()))
    return out

