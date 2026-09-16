from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from htcn.app.harmonic_service import DatasetNotFoundError, LocalHarmonicService

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "market"
REPORT_DIR = ROOT / "artifacts" / "reports"
REPORT_PATH = REPORT_DIR / "m2-reaction-audit.json"


def _qfq_symbols() -> list[str]:
    root = DATA_ROOT / "adjustment" / "qfq"
    if not root.exists():
        return []
    return sorted(path.stem for path in root.glob("*.parquet"))


def main() -> int:
    print("[HT-CN M2 OUTCOME] Building automatic reaction/retest/confirmation audit...")
    service = LocalHarmonicService(DATA_ROOT)
    symbols = _qfq_symbols()
    if not symbols:
        print("[HT-CN M2 OUTCOME] WARN: no local QFQ factor datasets; report skipped.")
        return 0

    records: list[dict] = []
    scanned_symbols = 0
    for symbol in symbols:
        try:
            result = service.analyze(
                symbol,
                bars=3000,
                scales=(3, 5, 8, 13, 21),
                max_completed=250,
                max_forming=30,
            )
        except DatasetNotFoundError:
            continue
        if not result["price_mode"].startswith("qfq"):
            continue
        scanned_symbols += 1
        bars_returned = int(result["bars_returned"])
        for pattern in result["completed"]:
            if pattern.get("is_primary_identity") is False:
                continue
            audit = pattern.get("reaction_audit") or {}
            targets = pattern.get("reaction_targets") or {}
            completion_index = int(pattern["points"][-1]["index"])
            records.append(
                {
                    "instrument_id": symbol,
                    "pattern_id": pattern["pattern_id"],
                    "schema": pattern.get("schema", "XABCD"),
                    "direction": pattern["direction"],
                    "scale": pattern["scale"],
                    "geometry_score": pattern["geometry_score"],
                    "completion_trade_date": pattern["points"][-1].get("trade_date"),
                    "completion_price": pattern["points"][-1]["price"],
                    "bars_after_completion": max(0, bars_returned - 1 - completion_index),
                    "prz_low": pattern["prz"]["price_low"],
                    "prz_high": pattern["prz"]["price_high"],
                    "reaction_targets": targets or None,
                    **audit,
                }
            )

    lifecycle_records = [row for row in records if "bars_observed" in row]
    shark_records = [row for row in records if row.get("schema") == "0XABC"]

    t1 = sum(row.get("bars_to_382") is not None for row in lifecycle_records)
    t2 = sum(row.get("bars_to_618") is not None for row in lifecycle_records)
    type_ii = sum(bool(row.get("type_ii_candidate")) for row in lifecycle_records)
    full_retests = sum(row.get("full_prz_retest_bar") is not None for row in lifecycle_records)
    price_reexits = sum(row.get("reversal_exit_after_retest_bar") is not None for row in lifecycle_records)
    rsi_confirmed = sum(bool(row.get("rsi_confirmation")) for row in lifecycle_records)
    third_tests = sum(row.get("third_prz_test_bar") is not None for row in lifecycle_records)
    mature = [row for row in lifecycle_records if int(row.get("bars_observed", 0)) >= 5]
    early_clean_5 = sum(row.get("no_prz_retest_first_5_bars") is True for row in mature)

    shark_50 = sum(
        (row.get("reaction_targets") or {}).get("bars_to_50") is not None
        for row in shark_records
    )
    shark_618 = sum(
        (row.get("reaction_targets") or {}).get("bars_to_618") is not None
        for row in shark_records
    )
    shark_reciprocal = sum(
        (row.get("reaction_targets") or {}).get("bars_to_reciprocal_abcd") is not None
        for row in shark_records
    )

    by_pattern = Counter(str(row["pattern_id"]) for row in records)
    by_schema = Counter(str(row.get("schema", "unknown")) for row in records)
    by_evidence = Counter(
        str(row.get("type_ii_evidence_state", "not_applicable"))
        for row in lifecycle_records
    )

    payload = {
        "schema_version": 3,
        "scope": {
            "symbols_with_qfq_scanned": scanned_symbols,
            "completed_primary_structures": len(records),
            "lifecycle_audited_structures": len(lifecycle_records),
            "shark_reaction_structures": len(shark_records),
            "note": "Historical descriptive audit only; no win-rate or trading recommendation is inferred.",
        },
        "summary": {
            "t1_382_reached": t1,
            "t2_618_reached": t2,
            "secondary_prz_retest_candidates": type_ii,
            "full_prz_retests": full_retests,
            "price_reversal_exits_after_retest": price_reexits,
            "rsi_confirmed_secondary_sequences": rsi_confirmed,
            "third_prz_tests_after_secondary_exit": third_tests,
            "mature_at_least_5_bars": len(mature),
            "no_prz_retest_first_5_bars": early_clean_5,
            "shark_50_target_reached": shark_50,
            "shark_618_target_reached": shark_618,
            "shark_reciprocal_abcd_reached": shark_reciprocal,
            "by_pattern": dict(sorted(by_pattern.items())),
            "by_schema": dict(sorted(by_schema.items())),
            "by_type_ii_evidence": dict(sorted(by_evidence.items())),
        },
        "records": records,
        "methodology": {
            "type_i_targets": "For XABCD, standalone AB=CD and 5-0: 38.2% and 61.8% retracements from completion D toward A using |A-D|.",
            "shark_targets": "Shark is audited separately as a reaction structure using the 50%/61.8% BC retracements and Reciprocal AB=CD target associated with the developing 5-0 PRZ.",
            "type_ii_candidate": "Price exits the original PRZ in the reversal direction and later re-enters the same PRZ.",
            "type_ii_confirmation_evidence": "HT-CN records full-PRZ retest, reversal-direction exit after the secondary test, Wilder RSI(14) extreme/reversal evidence at 30/70, and any third PRZ test. The evidence state is an audit label, not an automatic Carney-valid reversal declaration.",
            "hsi_policy": "HSI is proprietary in Volume Three; HT-CN does not invent or reverse-engineer an unsupported formula.",
            "source": "Scott M. Carney, Harmonic Trading Volumes One/Two/Three; schema-specific source contracts are frozen in specs/.",
        },
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"[HT-CN M2 OUTCOME] symbols={scanned_symbols}, completed_primary={len(records)}, "
        f"lifecycle={len(lifecycle_records)}, T1={t1}, T2={t2}, typeII={type_ii}, "
        f"shark50={shark_50}/{len(shark_records)}"
    )
    print(f"[HT-CN M2 OUTCOME] By schema: {dict(sorted(by_schema.items()))}")
    print(f"[HT-CN M2 OUTCOME] Evidence states: {dict(sorted(by_evidence.items()))}")
    print(f"[HT-CN M2 OUTCOME] Report: {REPORT_PATH.relative_to(ROOT)}")
    print("[HT-CN M2 OUTCOME] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
