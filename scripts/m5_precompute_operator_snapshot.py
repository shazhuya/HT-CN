from __future__ import annotations

import argparse
import json
from pathlib import Path

from htcn.app.operator_queue import discover_local_instruments
from htcn.app.operator_snapshot import (
    build_or_load_operator_snapshot,
    latest_local_trade_date,
)
from htcn.app.source_clock_lifecycle_service import (
    M3SourceClockHarmonicService,
)


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "market"
CACHE_ROOT = ROOT / "data" / "product" / "m5" / "operator_queue"
REPORT_PATH = ROOT / "artifacts" / "reports" / "m5-operator-snapshot.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Precompute the product-only M5 daily operator queue cache."
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--bars", type=int, default=420)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    instrument_ids = discover_local_instruments(
        DATA_ROOT,
        limit=max(0, int(args.limit)),
    )
    expected = latest_local_trade_date(DATA_ROOT / "catalog.duckdb")
    service = M3SourceClockHarmonicService(DATA_ROOT)

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
        bars=int(args.bars),
        scales=(3, 5, 8, 13),
        force_refresh=bool(args.force),
        max_workers=workers,
        service_factory=lambda: M3SourceClockHarmonicService(DATA_ROOT),
        progress_callback=progress,
    )

    report = {
        "schema_version": 1,
        "status": "ready",
        "instrument_count": payload.get("instrument_count"),
        "analyzed_instrument_count": payload.get(
            "analyzed_instrument_count"
        ),
        "failed_instrument_count": payload.get(
            "failed_instrument_count"
        ),
        "candidate_count": payload.get("candidate_count"),
        "as_of_trade_date": payload.get("as_of_trade_date"),
        "observation_integrity": payload.get(
            "observation_integrity"
        ),
        "product_cache": payload.get("product_cache"),
        "build_execution": payload.get("build_execution"),
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
