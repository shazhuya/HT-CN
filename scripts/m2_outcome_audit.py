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
    print("[HT-CN M2 OUTCOME] Building automatic reaction/retest audit...")
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
                max_completed=200,
                max_forming=20,
            )
        except DatasetNotFoundError:
            continue
        if not result["price_mode"].startswith("qfq"):
            continue
        scanned_symbols += 1
        for pattern in result["completed"]:
            if pattern.get("is_primary_identity") is False:
                continue
            audit = pattern.get("reaction_audit") or {}
            records.append(
                {
                    "instrument_id": symbol,
                    "pattern_id": pattern["pattern_id"],
                    "direction": pattern["direction"],
                    "scale": pattern["scale"],
                    "geometry_score": pattern["geometry_score"],
                    "d_trade_date": pattern["points"][-1].get("trade_date"),
                    "d_price": pattern["points"][-1]["price"],
                    "prz_low": pattern["prz"]["price_low"],
                    "prz_high": pattern["prz"]["price_high"],
                    **audit,
                }
            )

    t1 = sum(row.get("bars_to_382") is not None for row in records)
    t2 = sum(row.get("bars_to_618") is not None for row in records)
    type_ii = sum(bool(row.get("type_ii_candidate")) for row in records)
    mature = [row for row in records if int(row.get("bars_observed", 0)) >= 5]
    early_clean_5 = sum(row.get("no_prz_retest_first_5_bars") is True for row in mature)
    by_pattern = Counter(str(row["pattern_id"]) for row in records)

    payload = {
        "schema_version": 1,
        "scope": {
            "symbols_with_qfq_scanned": scanned_symbols,
            "completed_primary_structures": len(records),
            "note": "Historical descriptive audit only; no win-rate or trading recommendation is inferred.",
        },
        "summary": {
            "t1_382_reached": t1,
            "t2_618_reached": t2,
            "secondary_prz_retest_candidates": type_ii,
            "mature_at_least_5_bars": len(mature),
            "no_prz_retest_first_5_bars": early_clean_5,
            "by_pattern": dict(sorted(by_pattern.items())),
        },
        "records": records,
        "methodology": {
            "type_i_targets": "38.2% and 61.8% retracements from D toward A using |A-D|.",
            "type_ii_candidate": "Price exits the original PRZ in the reversal direction and later re-enters the same PRZ. This is not a validated Type-II reversal; Volume Three requires additional price/indicator confirmation.",
            "source": "Scott M. Carney, Harmonic Trading Volume Three: Reaction vs. Reversal, Type-I/Type-II management sections.",
        },
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"[HT-CN M2 OUTCOME] symbols={scanned_symbols}, completed_primary={len(records)}, "
        f"T1={t1}, T2={t2}, typeII_candidates={type_ii}"
    )
    print(f"[HT-CN M2 OUTCOME] Report: {REPORT_PATH.relative_to(ROOT)}")
    print("[HT-CN M2 OUTCOME] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
