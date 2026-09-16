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


def _pivot_quality(pattern: dict) -> tuple[int, float, int]:
    support = pattern.get("pivot_support") or []
    counts = [int(row.get("support_count", 1)) for row in support]
    if not counts:
        return (0, 0.0, 0)
    by_label = {str(row.get("label")): row for row in support}
    terminal = by_label.get("D") or by_label.get("C") or {}
    return (min(counts), sum(counts) / len(counts), int(terminal.get("support_count", 0)))


def _outcome_rank(pattern: dict) -> tuple[int, int, int, int, int, float, float]:
    audit = pattern.get("reaction_audit") or {}
    targets = pattern.get("reaction_targets") or {}
    min_support, mean_support, terminal_support = _pivot_quality(pattern)

    if targets:
        return (
            1 if targets.get("bars_to_618") is not None else 0,
            1 if targets.get("bars_to_50") is not None else 0,
            1 if targets.get("bars_to_reciprocal_abcd") is not None else 0,
            0,
            min_support,
            mean_support + (terminal_support * 0.01),
            float(pattern.get("geometry_score", 0.0)),
        )

    evidence = str(audit.get("type_ii_evidence_state", "not_candidate"))
    evidence_rank = {
        "price_and_rsi_confirmed": 3,
        "price_confirmed_no_rsi": 2,
        "retest_only": 1,
        "not_candidate": 0,
    }.get(evidence, 0)
    return (
        1 if audit.get("bars_to_618") is not None else 0,
        1 if audit.get("bars_to_382") is not None else 0,
        0,
        evidence_rank,
        min_support,
        mean_support + (terminal_support * 0.01),
        float(pattern.get("geometry_score", 0.0)),
    )


def _geometry_rank(pattern: dict) -> tuple[int, float, int, float]:
    min_support, mean_support, terminal_support = _pivot_quality(pattern)
    return (
        min_support,
        mean_support,
        terminal_support,
        float(pattern.get("geometry_score", 0.0)),
    )


def _case_key(row: dict) -> tuple:
    pattern = row["pattern"]
    return (
        row["instrument_id"],
        pattern["pattern_id"],
        pattern["direction"],
        tuple(point["index"] for point in pattern["points"]),
    )


def _is_weak_outcome(pattern: dict) -> bool:
    targets = pattern.get("reaction_targets") or {}
    if targets:
        return targets.get("bars_to_50") is None
    audit = pattern.get("reaction_audit") or {}
    return audit.get("bars_to_382") is None


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
                max_completed=300,
                max_forming=30,
            )
        except DatasetNotFoundError:
            continue
        if not result["price_mode"].startswith("qfq"):
            continue
        scanned += 1
        bars_returned = int(result["bars_returned"])
        for pattern in result["completed"]:
            if pattern.get("is_primary_identity") is False:
                continue
            completion_index = int(pattern["points"][-1]["index"])
            bars_after_completion = max(0, bars_returned - 1 - completion_index)
            if bars_after_completion < 10:
                continue
            min_support, mean_support, terminal_support = _pivot_quality(pattern)
            by_pattern[str(pattern["pattern_id"])].append(
                {
                    "instrument_id": symbol,
                    "price_mode": result["price_mode"],
                    "schema": pattern.get("schema", "XABCD"),
                    "review_status": "candidate_not_certified",
                    "bars_after_completion": bars_after_completion,
                    "pivot_robustness": {
                        "min_support": min_support,
                        "mean_support": mean_support,
                        "terminal_support": terminal_support,
                    },
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
        picks: list[dict] = []

        # 1) strongest schema-appropriate observed outcomes. For Shark this means its
        #    50%/61.8%/Reciprocal reaction targets; for the other completed schemas it
        #    means the shared Reaction-vs-Reversal lifecycle audit.
        picks.extend(sorted(rows, key=lambda row: _outcome_rank(row["pattern"]), reverse=True)[:2])

        # 2) strongest geometry + cross-scale pivot persistence example. This is the
        #    deliberately non-outcome-biased candidate that guards against circular
        #    "it worked, therefore its geometry was good" selection.
        robust = max(rows, key=lambda row: _geometry_rank(row["pattern"]), default=None)
        if robust is not None:
            picks.append(robust)

        # 3) Type-II price+RSI evidence only applies to schemas carrying the common
        #    lifecycle audit. Shark remains a reaction-only audit here.
        type_ii = next(
            (
                row
                for row in sorted(rows, key=lambda row: _geometry_rank(row["pattern"]), reverse=True)
                if (row["pattern"].get("reaction_audit") or {}).get("type_ii_evidence_state")
                == "price_and_rsi_confirmed"
            ),
            None,
        )
        if type_ii is not None:
            picks.append(type_ii)

        # 4) retain a weak/failed first objective as a negative control.
        weak = next(
            (
                row
                for row in sorted(rows, key=lambda row: _geometry_rank(row["pattern"]), reverse=True)
                if _is_weak_outcome(row["pattern"])
            ),
            None,
        )
        if weak is not None:
            picks.append(weak)

        unique: list[dict] = []
        seen: set[tuple] = set()
        for row in picks:
            key = _case_key(row)
            if key in seen:
                continue
            seen.add(key)
            unique.append(row)
        selected[pattern_id] = unique[:5]

    payload = {
        "schema_version": 3,
        "status": "candidate_not_certified",
        "symbols_scanned": scanned,
        "method": (
            "Source-valid completed primary identities from local QFQ history. Candidate selection "
            "keeps separate schema-appropriate outcome, geometry+pivot-robustness, Type-II evidence "
            "where applicable, and weak negative-control examples. Outcome success never certifies "
            "geometry by itself."
        ),
        "certification_gate": [
            "Recompute ratios independently from frozen raw point prices using the candidate's schema.",
            "Verify semantic points are legitimate confirmed pivots and inspect cross-scale support.",
            "Verify PRZ components/convergence without using post-completion outcome.",
            "Only then attach schema-appropriate outcome labels (lifecycle or Shark reaction targets).",
        ],
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
