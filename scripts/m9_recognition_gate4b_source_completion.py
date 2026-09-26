from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from htcn.harmonic.source_completion import (
    PRODUCTION_MAX_TOTAL_SKIPS,
    scan_source_completion_events,
)
from htcn.research.snapshot_cache import load_research_snapshot

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "research" / "a-share-research-universe-v1.json"
DEFAULT_DATA_DIR = ROOT / "artifacts" / "ci-research" / "data"
REPORT_PATH = ROOT / "artifacts" / "reports" / "m9-recognition-gate4b-source-completion.json"

SCALES = (3, 5, 8)
LIFETIME_BARS = 180


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    return parser.parse_args()


def _date(frame: pd.DataFrame, index: int) -> str:
    return pd.Timestamp(frame.iloc[index]["trade_date"]).date().isoformat()


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    start = str(manifest["start_date"])
    cutoff = str(manifest["snapshot_cutoff"])
    max_bars = int(manifest["max_bars"])
    minimum_symbols = int(manifest.get("minimum_successful_symbols", 1))

    failures: list[dict[str, str]] = []
    total_bars = 0
    total_projections = 0
    state_counts: Counter[str] = Counter()
    pattern_states: dict[str, Counter[str]] = defaultdict(Counter)
    state_by_skip: dict[int, Counter[str]] = defaultdict(Counter)
    state_by_scale_support: dict[int, Counter[str]] = defaultdict(Counter)
    exact_completion_keys: set[tuple[object, ...]] = set()
    exact_duplicate_count = 0
    collision_groups: dict[tuple[object, ...], list[dict[str, Any]]] = defaultdict(list)
    terminal_market_groups: dict[tuple[object, ...], list[dict[str, Any]]] = defaultdict(list)
    same_abc_terminal_groups: dict[tuple[object, ...], list[dict[str, Any]]] = defaultdict(list)
    all_completions: list[dict[str, Any]] = []
    completion_ages: list[int] = []
    loaded_symbols = 0

    for instrument in manifest["instruments"]:
        instrument_id = str(instrument["instrument_id"])
        snapshot, reason = load_research_snapshot(
            args.data_dir,
            instrument_id=instrument_id,
            requested_start=start,
            requested_end=cutoff,
            max_bars=max_bars,
            price_mode="qfq",
        )
        if snapshot is None:
            failures.append({"instrument_id": instrument_id, "reason": reason})
            continue

        frame = snapshot.frame.reset_index(drop=True)
        loaded_symbols += 1
        total_bars += len(frame)
        scan = scan_source_completion_events(
            frame,
            scales=SCALES,
            lifetime_bars=LIFETIME_BARS,
        )
        total_projections += len(scan.projections)

        for item in scan.states:
            state_counts[item.state] += 1
            pattern_states[item.projection.pattern_id][item.state] += 1
            state_by_skip[int(item.projection.min_skipped_pivots)][item.state] += 1
            state_by_scale_support[len(item.projection.scales)][item.state] += 1

        for event in scan.completions:
            key = (
                instrument_id,
                event.pattern_id,
                event.direction.value,
                event.source_nodes,
                event.terminal_bar,
            )
            if key in exact_completion_keys:
                exact_duplicate_count += 1
            exact_completion_keys.add(key)

            row = {
                "instrument_id": instrument_id,
                "name": str(instrument.get("name") or instrument_id),
                "bucket": str(instrument.get("bucket") or ""),
                "pattern_id": event.pattern_id,
                "direction": event.direction.value,
                "source_nodes": list(event.source_nodes),
                "source_dates": [_date(frame, idx) for idx in event.source_nodes],
                "known_at": event.known_at,
                "known_date": _date(frame, event.known_at),
                "terminal_bar": event.terminal_bar,
                "terminal_date": _date(frame, event.terminal_bar),
                "terminal_price": event.terminal_price,
                "scale_support": list(event.projection.scales),
                "scale_support_count": len(event.projection.scales),
                "min_skipped_pivots": event.projection.min_skipped_pivots,
                "source_span_bars": event.source_nodes[-1] - event.source_nodes[0],
                "age_to_terminal": event.terminal_bar - event.known_at,
            }
            all_completions.append(row)
            completion_ages.append(int(row["age_to_terminal"]))
            collision_groups[
                (
                    instrument_id,
                    event.pattern_id,
                    event.direction.value,
                    event.terminal_bar,
                )
            ].append(row)
            terminal_market_groups[
                (
                    instrument_id,
                    event.direction.value,
                    event.terminal_bar,
                )
            ].append(row)
            same_abc_terminal_groups[
                (
                    instrument_id,
                    event.pattern_id,
                    event.direction.value,
                    event.source_nodes[1:],
                    event.terminal_bar,
                )
            ].append(row)

    if loaded_symbols < minimum_symbols:
        raise SystemExit(
            f"insufficient real-market snapshots: loaded={loaded_symbols} minimum={minimum_symbols}"
        )

    collision_rows = [
        {
            "instrument_id": key[0],
            "pattern_id": key[1],
            "direction": key[2],
            "terminal_bar": key[3],
            "count": len(rows),
            "events": rows,
        }
        for key, rows in collision_groups.items()
        if len(rows) > 1
    ]
    collision_rows.sort(key=lambda row: (-int(row["count"]), str(row["instrument_id"])))

    market_collision_rows = [
        {
            "instrument_id": key[0],
            "direction": key[1],
            "terminal_bar": key[2],
            "count": len(rows),
            "pattern_ids": sorted({str(row["pattern_id"]) for row in rows}),
            "events": rows,
        }
        for key, rows in terminal_market_groups.items()
        if len(rows) > 1
    ]
    market_collision_rows.sort(
        key=lambda row: (-int(row["count"]), str(row["instrument_id"]))
    )
    abc_collision_rows = [
        {
            "instrument_id": key[0],
            "pattern_id": key[1],
            "direction": key[2],
            "abc_nodes": list(key[3]),
            "terminal_bar": key[4],
            "count": len(rows),
            "x_nodes": sorted({int(row["source_nodes"][0]) for row in rows}),
            "events": rows,
        }
        for key, rows in same_abc_terminal_groups.items()
        if len(rows) > 1
    ]
    abc_collision_rows.sort(
        key=lambda row: (-int(row["count"]), str(row["instrument_id"]))
    )

    sorted_ages = sorted(completion_ages)
    age_median = (
        sorted_ages[len(sorted_ages) // 2]
        if sorted_ages
        else None
    )
    age_p90 = (
        sorted_ages[min(len(sorted_ages) - 1, int(len(sorted_ages) * 0.9))]
        if sorted_ages
        else None
    )

    completed = int(state_counts["completed"])
    invalidated = int(state_counts["invalidated"])
    expired = int(state_counts["expired"])
    active = int(state_counts["active"])

    report = {
        "schema": 1,
        "gate_id": "recognition-gate4b-source-completion-v1",
        "dataset_id": manifest.get("dataset_id"),
        "snapshot_cutoff": cutoff,
        "raw_market_data_modified": False,
        "loaded_symbols": loaded_symbols,
        "snapshot_failures": failures,
        "total_bars": total_bars,
        "detector": {
            "architecture": (
                "confirmed pivot events -> hierarchical XABC -> frozen Source Raw PRZ -> "
                "C-extreme/expiry validity clock -> canonical Source Terminal"
            ),
            "scales": list(SCALES),
            "lifetime_bars": LIFETIME_BARS,
            "max_total_skips": PRODUCTION_MAX_TOTAL_SKIPS,
            "source_conflict_patterns": False,
            "future_backfill": False,
        },
        "overall": {
            "projection_count": total_projections,
            "completed_count": completed,
            "invalidated_count": invalidated,
            "expired_count": expired,
            "active_count": active,
            "closed_or_active_accounting_matches": (
                completed + invalidated + expired + active == total_projections
            ),
            "completion_rate_of_projections": (
                completed / total_projections if total_projections else 0.0
            ),
            "completion_density_per_1000_bars": (
                completed / total_bars * 1000.0 if total_bars else 0.0
            ),
            "exact_duplicate_completion_count": exact_duplicate_count,
            "same_pattern_terminal_collision_group_count": len(collision_rows),
            "same_pattern_terminal_collision_event_count": sum(
                int(row["count"]) for row in collision_rows
            ),
            "market_terminal_collision_group_count": len(market_collision_rows),
            "market_terminal_collision_event_count": sum(
                int(row["count"]) for row in market_collision_rows
            ),
            "deduped_market_terminal_event_count": len(terminal_market_groups),
            "deduped_market_terminal_density_per_1000_bars": (
                len(terminal_market_groups) / total_bars * 1000.0
                if total_bars
                else 0.0
            ),
            "same_abc_different_x_collision_group_count": len(abc_collision_rows),
            "completion_age_median_bars": age_median,
            "completion_age_p90_bars": age_p90,
            "completion_age_max_bars": max(completion_ages) if completion_ages else None,
        },
        "state_by_min_skipped_pivots": {
            str(skip): {
                "completed": int(counts["completed"]),
                "invalidated": int(counts["invalidated"]),
                "expired": int(counts["expired"]),
                "active": int(counts["active"]),
            }
            for skip, counts in sorted(state_by_skip.items())
        },
        "state_by_scale_support_count": {
            str(support): {
                "completed": int(counts["completed"]),
                "invalidated": int(counts["invalidated"]),
                "expired": int(counts["expired"]),
                "active": int(counts["active"]),
            }
            for support, counts in sorted(state_by_scale_support.items())
        },
        "by_pattern": {
            pattern: {
                "completed": int(counts["completed"]),
                "invalidated": int(counts["invalidated"]),
                "expired": int(counts["expired"]),
                "active": int(counts["active"]),
            }
            for pattern, counts in sorted(pattern_states.items())
        },
        "collision_groups_top50": collision_rows[:50],
        "market_terminal_collision_groups_top50": market_collision_rows[:50],
        "same_abc_different_x_groups_top50": abc_collision_rows[:50],
        "completion_examples_first100": all_completions[:100],
        "interpretation_boundary": (
            "This Gate 4B report measures event density, retirement and duplicate pressure on "
            "unmodified real A-share history. It is not a win-rate or alpha study and does not "
            "by itself label semantic false positives. Semantic precision still requires "
            "high-information adjudication and blind holdout before production promotion."
        ),
    }

    if not report["overall"]["closed_or_active_accounting_matches"]:
        raise SystemExit("projection state accounting mismatch")
    if exact_duplicate_count:
        raise SystemExit(f"exact duplicate completion events detected: {exact_duplicate_count}")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
