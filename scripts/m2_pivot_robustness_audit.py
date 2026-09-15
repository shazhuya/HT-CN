from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from htcn.app.harmonic_service import DatasetNotFoundError, LocalHarmonicService

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "market"
REPORT_DIR = ROOT / "artifacts" / "reports"
REPORT_PATH = REPORT_DIR / "m2-pivot-robustness.json"
SCALES = (3, 5, 8, 13, 21)


def _symbols() -> list[str]:
    root = DATA_ROOT / "adjustment" / "qfq"
    if not root.exists():
        return []
    return sorted(path.stem for path in root.glob("*.parquet"))


def _support_summary(pattern: dict) -> dict:
    support = pattern.get("pivot_support") or []
    counts = [int(row.get("support_count", 1)) for row in support]
    by_label = {str(row.get("label")): row for row in support}
    terminal_label = "D" if pattern.get("state") == "completed" else "C"
    terminal = by_label.get(terminal_label) or {}
    return {
        "min_support": min(counts) if counts else 0,
        "mean_support": (sum(counts) / len(counts)) if counts else 0.0,
        "max_support": max(counts) if counts else 0,
        "terminal_label": terminal_label,
        "terminal_support": int(terminal.get("support_count", 0)),
        "terminal_scales": terminal.get("scales", []),
        "all_nodes_multi_scale": bool(counts and min(counts) >= 2),
    }


def main() -> int:
    print("[HT-CN M2 PIVOT] Auditing cross-scale pivot robustness...")
    service = LocalHarmonicService(DATA_ROOT)
    records: list[dict] = []
    scanned = 0

    for symbol in _symbols():
        try:
            result = service.analyze(
                symbol,
                bars=3000,
                scales=SCALES,
                max_completed=250,
                max_forming=50,
            )
        except DatasetNotFoundError:
            continue
        if not result["price_mode"].startswith("qfq"):
            continue
        scanned += 1
        for pattern in [*result["completed"], *result["forming"]]:
            if pattern.get("is_primary_identity") is False:
                continue
            records.append(
                {
                    "instrument_id": symbol,
                    "pattern_id": pattern["pattern_id"],
                    "state": pattern["state"],
                    "direction": pattern["direction"],
                    "scale": pattern["scale"],
                    "geometry_score": pattern["geometry_score"],
                    "node_indices": [point["index"] for point in pattern["points"]],
                    "pivot_support": pattern.get("pivot_support", []),
                    **_support_summary(pattern),
                }
            )

    min_support_hist = Counter(str(row["min_support"]) for row in records)
    terminal_support_hist = Counter(str(row["terminal_support"]) for row in records)
    all_multi = sum(bool(row["all_nodes_multi_scale"]) for row in records)
    terminal_multi = sum(int(row["terminal_support"]) >= 2 for row in records)

    payload = {
        "schema_version": 1,
        "scope": {
            "symbols_scanned": scanned,
            "scales": list(SCALES),
            "primary_structures": len(records),
        },
        "summary": {
            "all_nodes_supported_by_2plus_scales": all_multi,
            "terminal_node_supported_by_2plus_scales": terminal_multi,
            "min_support_histogram": dict(sorted(min_support_hist.items(), key=lambda item: int(item[0]))),
            "terminal_support_histogram": dict(sorted(terminal_support_hist.items(), key=lambda item: int(item[0]))),
        },
        "records": records,
        "methodology": {
            "definition": "Exact same bar index and pivot kind independently detected by multiple configured scales.",
            "identity_policy": "Pivot support is a calibration/quality diagnostic only. It never relaxes or changes Carney geometry identity.",
            "tolerance_policy": "No near-bar or near-price tolerance is used in this first calibration pass; exact-node agreement avoids inventing an arbitrary robustness band.",
        },
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"[HT-CN M2 PIVOT] symbols={scanned}, structures={len(records)}, "
        f"all_nodes_2+={all_multi}, terminal_2+={terminal_multi}"
    )
    print(f"[HT-CN M2 PIVOT] Report: {REPORT_PATH.relative_to(ROOT)}")
    print("[HT-CN M2 PIVOT] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
