from __future__ import annotations

import argparse
import json
from pathlib import Path

from htcn.app.operator_input_identity import (
    build_analysis_code_identity,
    build_operator_cache_input_identity,
)
from htcn.app.operator_snapshot import (
    build_or_load_operator_snapshot,
    latest_local_trade_date,
)
from htcn.app.source_clock_lifecycle_service import M3SourceClockHarmonicService
from htcn.app.universe_coverage import build_universe_coverage, load_catalog_universes


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "market"
CACHE_ROOT = ROOT / "data" / "product" / "m5" / "operator_queue"
REPORT_PATH = ROOT / "artifacts" / "reports" / "m5-operator-snapshot.json"

PERSISTED_CACHE_STATUSES = {
    "hit",
    "hit_after_race",
    "hit_after_process_wait",
    "rebuilt",
    "rebuilt_force",
    "coalesced_wait",
}


def evaluate_precompute_readiness(
    payload: dict,
    *,
    expected_trade_date: str | None,
) -> dict:
    instrument_count = int(payload.get("instrument_count") or 0)
    analyzed = int(payload.get("analyzed_instrument_count") or 0)
    failed = int(payload.get("failed_instrument_count") or 0)
    cache = dict(payload.get("product_cache") or {})
    reasons: list[str] = []

    if instrument_count <= 0:
        reasons.append("empty_initialized_universe")
    if analyzed <= 0:
        reasons.append("no_successful_instrument_analysis")
    if analyzed + failed != instrument_count:
        reasons.append("instrument_attempt_coverage_mismatch")
    if payload.get("observation_integrity") != "single_as_of":
        reasons.append("queue_not_single_as_of")
    if expected_trade_date is None:
        reasons.append("expected_trade_date_unresolved")
    elif str(payload.get("as_of_trade_date") or "") != str(expected_trade_date):
        reasons.append("queue_trade_date_not_expected")
    if cache.get("freshness") != "current":
        reasons.append("product_cache_not_current")
    if str(cache.get("status") or "") not in PERSISTED_CACHE_STATUSES:
        reasons.append("product_cache_not_persisted")
    if cache.get("input_identity_stable_during_build") is not True:
        reasons.append("input_identity_not_stable")

    ready = not reasons
    status = (
        "ready_with_instrument_failures"
        if ready and failed > 0
        else "ready"
        if ready
        else "not_ready"
    )
    return {
        "status": status,
        "product_ready": ready,
        "instrument_count": instrument_count,
        "analyzed_instrument_count": analyzed,
        "failed_instrument_count": failed,
        "instrument_attempt_coverage_complete": (
            analyzed + failed == instrument_count
        ),
        "instrument_failures_are_isolated": True,
        "readiness_blockers": reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Precompute the product-only M5 daily operator queue cache."
    )
    parser.add_argument("--bars", type=int, default=420)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    catalog_universes = load_catalog_universes(DATA_ROOT)
    instrument_ids = list(catalog_universes["initialized_ids"])
    universe_coverage = build_universe_coverage(
        listed_ids=catalog_universes["listed_ids"],
        initialized_ids=instrument_ids,
        qfq_evaluated=False,
        operator_ids=instrument_ids,
        excluded_local_ids=catalog_universes["excluded_local_ids"],
        initialization_errors=catalog_universes["initialization_errors"],
    )
    expected = latest_local_trade_date(DATA_ROOT / "catalog.duckdb")
    service = M3SourceClockHarmonicService(DATA_ROOT)
    analysis_code_identity = build_analysis_code_identity(
        project_root=ROOT,
    )

    def current_input_identity():
        return build_operator_cache_input_identity(
            data_root=DATA_ROOT,
            project_root=ROOT,
            analysis_code_identity=analysis_code_identity,
        )

    input_identity = current_input_identity()

    def progress(
        completed: int,
        total: int,
        instrument_id: str,
        ok: bool,
    ) -> None:
        if (
            completed == 1
            or completed == total
            or completed % 25 == 0
            or not ok
        ):
            status = "OK" if ok else "FAILED"
            print(
                f"[HT-CN M5] {completed}/{total} "
                f"{status} {instrument_id}",
                flush=True,
            )

    workers = max(1, min(16, int(args.workers)))
    payload = build_or_load_operator_snapshot(
        service,
        instrument_ids,
        cache_root=CACHE_ROOT,
        expected_trade_date=expected,
        input_identity=input_identity,
        input_identity_factory=current_input_identity,
        bars=int(args.bars),
        scales=(3, 5, 8, 13),
        force_refresh=bool(args.force),
        max_workers=workers,
        service_factory=lambda: M3SourceClockHarmonicService(DATA_ROOT),
        progress_callback=progress,
    )

    readiness = evaluate_precompute_readiness(
        payload,
        expected_trade_date=expected,
    )
    report = {
        "schema_version": 2,
        **readiness,
        "instrument_count": payload.get("instrument_count"),
        "analyzed_instrument_count": payload.get(
            "analyzed_instrument_count"
        ),
        "failed_instrument_count": payload.get(
            "failed_instrument_count"
        ),
        "instrument_errors": list(payload.get("errors") or []),
        "candidate_count": payload.get("candidate_count"),
        "as_of_trade_date": payload.get("as_of_trade_date"),
        "observation_integrity": payload.get(
            "observation_integrity"
        ),
        "product_cache": payload.get("product_cache"),
        "input_identity": input_identity.as_payload(),
        "build_execution": payload.get("build_execution"),
        "universe_coverage": universe_coverage,
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "is_trade_instruction": False,
        "alpha_inference_allowed": False,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        ),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["product_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
