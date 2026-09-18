from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from htcn.app.harmonic_service import DatasetNotFoundError
from htcn.app.operator_delta import build_operator_delta
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
def instruments(limit: int = Query(default=200, ge=1, le=1000)) -> dict[str, object]:
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
    limit: int = Query(default=200, ge=1, le=1000),
    bars: int = Query(default=420, ge=80, le=1200),
    include_evidence_insufficient: bool = Query(default=True),
    refresh: bool = Query(default=False),
) -> dict[str, object]:
    instrument_ids = discover_local_instruments(
        DATA_ROOT,
        limit=limit,
    )
    expected_trade_date = latest_local_trade_date(
        DATA_ROOT / "catalog.duckdb"
    )
    payload = build_or_load_operator_snapshot(
        service,
        instrument_ids,
        cache_root=OPERATOR_CACHE_ROOT,
        expected_trade_date=expected_trade_date,
        bars=bars,
        scales=(3, 5, 8, 13),
        force_refresh=refresh,
    )
    return filter_operator_queue_payload(
        payload,
        include_evidence_insufficient=include_evidence_insufficient,
    )

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
