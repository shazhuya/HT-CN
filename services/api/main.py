from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from htcn.app.daily_review_digest import (
    CHANGE_TYPE_ORDER,
    WORKFLOW_REVIEW_ORDER,
    build_latest_daily_review_digest,
    filter_daily_review_digest,
)
from htcn.app.harmonic_service import DatasetNotFoundError
from htcn.app.operator_delta import build_operator_delta
from htcn.app.operator_history import query_operator_history
from htcn.app.operator_input_identity import (
    build_analysis_code_identity,
    build_operator_cache_input_identity,
)
from htcn.app.operator_queue import (
    build_operator_queue,
    discover_local_instruments,
    filter_operator_queue_payload,
)
from htcn.app.operator_snapshot import (
    build_or_load_operator_snapshot,
    latest_local_trade_date,
)
from htcn.app.source_clock_lifecycle_service import M3SourceClockHarmonicService
from htcn.harmonic.rules import CARNEY_RULES
from htcn.research.type_i_live_evidence import build_type_i_t5_events

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "data" / "market"
OPERATOR_CACHE_ROOT = ROOT / "data" / "product" / "m5" / "operator_queue"
OPERATOR_HISTORY_ROOT = ROOT / "data" / "product" / "m5" / "operator_history"
OPERATOR_ANALYSIS_CODE_IDENTITY = build_analysis_code_identity(
    project_root=ROOT,
)


def _operator_input_identity():
    return build_operator_cache_input_identity(
        data_root=DATA_ROOT,
        project_root=ROOT,
        analysis_code_identity=OPERATOR_ANALYSIS_CODE_IDENTITY,
    )


def _operator_build_workers() -> int:
    raw = str(os.getenv("HTCN_OPERATOR_WORKERS", "4")).strip()
    try:
        value = int(raw)
    except ValueError:
        value = 4
    return max(1, min(16, value))


OPERATOR_BUILD_WORKERS = _operator_build_workers()


def _operator_service_factory() -> M3SourceClockHarmonicService:
    return M3SourceClockHarmonicService(DATA_ROOT)


app = FastAPI(title="HT-CN API", version="0.4.0")
service = M3SourceClockHarmonicService(DATA_ROOT)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ht-cn-api", "version": "0.4.0"}


@app.get("/api/instruments")
def instruments(limit: int = Query(default=1000, ge=1, le=10000)) -> dict[str, object]:
    daily_root = DATA_ROOT / "daily"
    factor_root = DATA_ROOT / "adjustment" / "qfq"
    ids = sorted(path.stem for path in daily_root.glob("*.parquet")) if daily_root.exists() else []
    rows = [
        {
            "instrument_id": instrument_id,
            "has_qfq_factor": (factor_root / f"{instrument_id}.parquet").exists(),
        }
        for instrument_id in ids[:limit]
    ]
    return {"count": len(ids), "items": rows}




@app.get("/api/operator/queue")
def operator_queue(
    legacy_limit: int | None = Query(
        default=None,
        alias="limit",
        ge=1,
        le=10000,
        description="Deprecated compatibility parameter; full initialized local universe is always scanned.",
    ),
    bars: int = Query(default=420, ge=80, le=1200),
    include_evidence_insufficient: bool = Query(default=True),
    refresh: bool = Query(default=False),
) -> dict[str, object]:
    # M5 Phase 4: the scan/cache universe is canonical and independent from UI
    # pagination or any legacy presentation limit.
    instrument_ids = discover_local_instruments(
        DATA_ROOT,
        limit=0,
    )
    expected_trade_date = latest_local_trade_date(
        DATA_ROOT / "catalog.duckdb"
    )
    input_identity = _operator_input_identity()
    payload = build_or_load_operator_snapshot(
        service,
        instrument_ids,
        cache_root=OPERATOR_CACHE_ROOT,
        expected_trade_date=expected_trade_date,
        input_identity=input_identity,
        input_identity_factory=_operator_input_identity,
        bars=bars,
        scales=(3, 5, 8, 13),
        force_refresh=refresh,
        max_workers=OPERATOR_BUILD_WORKERS,
        service_factory=_operator_service_factory,
    )
    payload["operator_index"] = {
        "schema_version": 1,
        "universe_scope": "all_initialized_local_instruments",
        "universe_instrument_count": len(instrument_ids),
        "presentation_does_not_define_universe": True,
        "legacy_limit_ignored": legacy_limit,
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
    }
    return filter_operator_queue_payload(
        payload,
        include_evidence_insufficient=include_evidence_insufficient,
    )

@app.get("/api/operator/review-digest")
def operator_review_digest(
    workflow_bucket: str | None = Query(default=None),
    change_type: str | None = Query(default=None),
    instrument_id: str | None = Query(default=None),
) -> dict[str, object]:
    if (
        workflow_bucket is not None
        and workflow_bucket not in WORKFLOW_REVIEW_ORDER
    ):
        raise HTTPException(
            status_code=400,
            detail=f"unknown review workflow bucket: {workflow_bucket}",
        )
    if change_type is not None and change_type not in CHANGE_TYPE_ORDER:
        raise HTTPException(
            status_code=400,
            detail=f"unknown review change type: {change_type}",
        )
    try:
        digest = build_latest_daily_review_digest(
            history_root=str(OPERATOR_HISTORY_ROOT),
        )
        return filter_daily_review_digest(
            digest,
            workflow_bucket=workflow_bucket,
            change_type=change_type,
            instrument_id=instrument_id,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"daily review digest unavailable: {exc}",
        ) from exc


@app.get("/api/operator/history")
def operator_history(
    instrument_id: str | None = Query(default=None),
    display_key: str | None = Query(default=None),
    start_trade_date: str | None = Query(default=None),
    end_trade_date: str | None = Query(default=None),
    all_revisions: bool = Query(default=False),
    summary_only: bool = Query(default=True),
    limit: int = Query(default=60, ge=1, le=3650),
) -> dict[str, object]:
    try:
        return query_operator_history(
            history_root=OPERATOR_HISTORY_ROOT,
            instrument_id=instrument_id,
            display_key=display_key,
            start_trade_date=start_trade_date,
            end_trade_date=end_trade_date,
            latest_revision_per_day=not all_revisions,
            summary_only=summary_only,
            limit=limit,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"operator history integrity error: {exc}",
        ) from exc


@app.post("/api/operator/delta")
def operator_delta(
    payload: dict[str, Any] = Body(...),
) -> dict[str, object]:
    previous = payload.get("previous")
    current = payload.get("current")
    if not isinstance(previous, dict) or not isinstance(current, dict):
        raise HTTPException(
            status_code=400,
            detail="operator delta requires previous and current queue snapshots",
        )
    try:
        return build_operator_delta(previous, current)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/harmonic/rules")
def harmonic_rules() -> dict[str, object]:
    return {
        "items": [
            {
                "pattern_id": rule.pattern_id,
                "schema": rule.schema,
                "executable_identity": rule.executable_identity,
                "source_conflict": rule.source_conflict,
                "source_note": rule.source_note,
                "implementation_note": rule.implementation_note,
            }
            for rule in CARNEY_RULES.values()
        ]
    }


@app.get("/api/harmonic/{instrument_id}")
def harmonic_analysis(
    instrument_id: str,
    bars: int = Query(default=420, ge=80, le=3000),
    scales: str = Query(default="3,5,8,13"),
) -> dict[str, object]:
    try:
        parsed_scales = tuple(sorted({int(value.strip()) for value in scales.split(",") if value.strip()}))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="scales must be comma-separated integers") from exc
    try:
        analysis = service.analyze(instrument_id, bars=bars, scales=parsed_scales)
        # M2.23 stays outside the static completed-pattern identity payload. Rebuild the exact
        # selected continuous OHLC window from the service response, replay source-visible forming
        # projections, then attach a separate Terminal-Bar/T+5 evidence stream.
        analysis_frame = pd.DataFrame(analysis.get("bars") or [])
        analysis["type_i_t5_events"] = build_type_i_t5_events(
            analysis_frame,
            instrument_id=instrument_id,
            scales=parsed_scales,
            max_events=12,
        )
        return analysis
    except DatasetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"local dataset not found: {instrument_id}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
