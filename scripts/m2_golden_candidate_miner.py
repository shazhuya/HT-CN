from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from htcn.app.harmonic_service import DatasetNotFoundError, LocalHarmonicService

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "market"
OUT_DIR = ROOT / "artifacts" / "golden_candidates"
MANIFEST = OUT_DIR / "manifest.json"


def _symbols() -> list[str]:
    root = DATA_ROOT / "adjustment" / "qfq"
    if not root.exists():
        return []
    return sorted(path.stem for path in root.glob("*.parquet"))


def _rank(pattern: dict) -> tuple[int, int, float, int]:
    audit = pattern.get("reaction_audit") or {}
    return (
        1 if audit.get("bars_to_618") is not None else 0,
        1 if audit.get("bars_to_382") is not None else 0,
        float(pattern.get("geometry_score", 0.0)),
        int(audit.get("bars_observed", 0)),
    )


def main() -> int:
    print("[HT-CN M2 GOLDEN] Mining real local A-share golden-case candidates...")
    service = LocalHarmonicService(DATA_ROOT)
    by_pattern: dict[str, list[dict]] = defaultdict(list)
    scanned = 0

    for symbol in _symbols():
        try:
            result = service.analyze(
                symbol,
                bars=3000,
                scales=(3, 5, 8, 13, 21),
                max_completed=250,
                max_forming=20,
            )
        except DatasetNotFoundError:
            continue
        if not result["price_mode"].startswith("qfq"):
            continue
        scanned += 1
        for pattern in result["completed"]:
            if pattern.get("is_primary_identity") is False:
                continue
            audit = pattern.get("reaction_audit") or {}
            # A useful review candidate needs enough post-D history to judge reaction vs retest.
            if int(audit.get("bars_observed", 0)) < 10:
                continue
            by_pattern[str(pattern["pattern_id"])].append(
                {
                    "instrument_id": symbol,
                    "price_mode": result["price_mode"],
                    "pattern": pattern,
                    "window": {
                        "first_trade_date": result["first_trade_date"],
                        "last_trade_date": result["last_trade_date"],
                        "bars_returned": result["bars_returned"],
                    },
                }
            )

    selected: dict[str, list[dict]] = {}
    for pattern_id, rows in sorted(by_pattern.items()):
        ranked = sorted(rows, key=lambda row: _rank(row["pattern"]), reverse=True)
        # Keep a compact review set: strongest reaction examples plus a weak/non-T1 contrast
        # when available. These are candidates for human/source audit, not certified truth.
        picks = ranked[:3]
        weak = next(
            (
                row
                for row in reversed(ranked)
                if (row["pattern"].get("reaction_audit") or {}).get("bars_to_382") is None
            ),
            None,
        )
        if weak is not None and weak not in picks:
            picks.append(weak)
        selected[pattern_id] = picks

    payload = {
        "schema_version": 1,
        "status": "candidate_not_certified",
        "symbols_scanned": scanned,
        "method": (
            "Source-valid completed primary identities from local QFQ history; rank T2, then T1, "
            "then geometry score. A candidate is not promoted to a Golden Case until geometry, "
            "pivot choice, PRZ and post-D path are independently audited."
        ),
        "cases": selected,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(rows) for rows in selected.values())
    print(f"[HT-CN M2 GOLDEN] symbols={scanned}, candidate_cases={total}, families={len(selected)}")
    print(f"[HT-CN M2 GOLDEN] Manifest: {MANIFEST.relative_to(ROOT)}")
    print("[HT-CN M2 GOLDEN] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
