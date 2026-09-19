from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from htcn.app.harmonic_service import LocalHarmonicService
from htcn.research.type_i_live_evidence import build_type_i_t5_events
from htcn.research.type_i_prospective import (
    PROSPECTIVE_CUTOFF,
    PROSPECTIVE_PROTOCOL_ID,
    ProspectiveRegistryStore,
    registry_summary,
    update_registry,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "market"
PROTOCOL_PATH = ROOT / "research" / "m2-type-i-prospective-protocol-v1.json"
REGISTRY_PATH = ROOT / "artifacts" / "prospective" / "m2-type-i-prospective-registry.json"
SUMMARY_PATH = ROOT / "artifacts" / "prospective" / "m2-type-i-prospective-summary.json"
SCALES = (3, 5, 8, 13, 21)
FORMING_HORIZON = 60
MAX_BARS = 3000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update the append-only HT-CN Type-I prospective evidence registry"
    )
    parser.add_argument(
        "--instrument",
        action="append",
        default=[],
        help="instrument id such as SSE.688256; repeat for multiple symbols",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="when --instrument is omitted, 0 means all locally initialized symbols with QFQ factors",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=REGISTRY_PATH,
        help="override local registry path",
    )
    return parser.parse_args()


def _load_protocol() -> dict:
    payload = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if payload.get("protocol_id") != PROSPECTIVE_PROTOCOL_ID:
        raise RuntimeError("prospective protocol id differs from code constant")
    if payload.get("registered_cutoff") != PROSPECTIVE_CUTOFF:
        raise RuntimeError("prospective protocol cutoff differs from code constant")
    clock = payload.get("event_clock") or {}
    if tuple(int(value) for value in clock.get("scales") or []) != SCALES:
        raise RuntimeError("prospective scales differ from frozen protocol")
    if int(clock.get("forming_horizon_bars") or 0) != FORMING_HORIZON:
        raise RuntimeError("prospective forming horizon differs from frozen protocol")
    return payload


def _instrument_ids(requested: list[str], limit: int) -> list[str]:
    if requested:
        values = sorted({value.strip().upper() for value in requested if value.strip()})
    else:
        daily_root = DATA_ROOT / "daily"
        factor_root = DATA_ROOT / "adjustment" / "qfq"
        values = sorted(
            path.stem
            for path in daily_root.glob("*.parquet")
            if (factor_root / path.name).exists()
        )
    if limit > 0:
        values = values[:limit]
    return values


def main() -> int:
    args = parse_args()
    _load_protocol()
    service = LocalHarmonicService(DATA_ROOT)
    store = ProspectiveRegistryStore(args.registry)
    registry = store.read()
    instruments = _instrument_ids(list(args.instrument), int(args.limit))
    if not instruments:
        print("[HT-CN M2 PROSPECTIVE] FAIL: no local QFQ instruments selected.")
        return 2

    print(
        "[HT-CN M2 PROSPECTIVE] START "
        f"protocol={PROSPECTIVE_PROTOCOL_ID}, cutoff={PROSPECTIVE_CUTOFF}, "
        f"symbols={len(instruments)}, scales={SCALES}"
    )
    processed = 0
    skipped = 0
    failures = 0

    for index, instrument_id in enumerate(instruments, start=1):
        try:
            raw = service._load_history(instrument_id)
            continuous, price_mode, warning = service._continuous_view(instrument_id, raw)
            if price_mode == "raw":
                skipped += 1
                print(
                    f"[HT-CN M2 PROSPECTIVE] {index}/{len(instruments)} SKIP {instrument_id}: "
                    f"official prospective ledger requires QFQ; {warning or 'raw price view'}"
                )
                continue
            frame = continuous.tail(MAX_BARS).reset_index(drop=True)
            if frame.empty:
                skipped += 1
                continue
            observed_through = pd.Timestamp(frame["trade_date"].iloc[-1]).date().isoformat()
            events = build_type_i_t5_events(
                frame,
                instrument_id=instrument_id,
                scales=SCALES,
                forming_horizon=FORMING_HORIZON,
                max_events=10000,
            )
            prospective = [
                row for row in events if str(row.get("terminal_trade_date")) > PROSPECTIVE_CUTOFF
            ]
            registry = update_registry(
                registry,
                prospective,
                observed_through_trade_date=observed_through,
            )
            # Persist after each symbol so interruption cannot erase already registered events.
            store.write(registry)
            processed += 1
            print(
                f"[HT-CN M2 PROSPECTIVE] {index}/{len(instruments)} OK {instrument_id}: "
                f"view={price_mode}, through={observed_through}, post_cutoff_events={len(prospective)}"
            )
        except KeyboardInterrupt:
            store.write(registry)
            print("\n[HT-CN M2 PROSPECTIVE] INTERRUPTED: registry saved through last completed symbol.")
            return 130
        except Exception as exc:
            failures += 1
            print(
                f"[HT-CN M2 PROSPECTIVE] {index}/{len(instruments)} FAILED {instrument_id}: "
                f"{type(exc).__name__}: {exc}"
            )

    summary = registry_summary(registry)
    try:
        registry_display_path = str(args.registry.relative_to(ROOT))
    except ValueError:
        registry_display_path = str(args.registry)
    summary_payload = {
        **summary.as_payload(),
        "registered_cutoff": PROSPECTIVE_CUTOFF,
        "processed_symbols": processed,
        "skipped_symbols": skipped,
        "failed_symbols": failures,
        "registry_path": registry_display_path,
        "inference": "descriptive_registry_only_no_interim_confirmatory_test",
    }
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(
        json.dumps(summary_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        "[HT-CN M2 PROSPECTIVE] DONE "
        f"registered={summary.total_events}, prospective={summary.prospective_registered_before_endpoint}, "
        f"backfilled={summary.backfilled_excluded}, awaiting_t5={summary.awaiting_t5}, "
        f"excluded_t2_by_t5={summary.excluded_t2_by_t5}, exposure={summary.exposure_group}, "
        f"comparator={summary.comparator_group}, matured_t20={summary.matured_t20}, failures={failures}"
    )
    print(
        "[HT-CN M2 PROSPECTIVE] NO INTERIM SIGNIFICANCE TEST / NO DYNAMIC SUCCESS PROBABILITY."
    )
    print(f"[HT-CN M2 PROSPECTIVE] registry={registry_display_path}")
    print(f"[HT-CN M2 PROSPECTIVE] summary={SUMMARY_PATH.relative_to(ROOT)}")
    return 0 if processed > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
