from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from htcn.harmonic.pine_r34 import scan_pine_r34
from htcn.harmonic.source_completion import scan_source_completion_events
from htcn.research.snapshot_cache import load_research_snapshot

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "research" / "a-share-research-universe-v1.json"
DEFAULT_DATA_DIR = ROOT / "artifacts" / "ci-research" / "data"
REPORT_PATH = ROOT / "artifacts" / "reports" / "m9-recognition-gate4b-pine-differential.json"

SOURCE_CLEARED_STANDARD = {"gartley", "bat", "butterfly", "crab", "deep_crab"}
V2_NATIVE_SCALES = (3, 5, 8)
PINE_MATCHED_SCALES = (5, 10, 20)
LIFETIME_BARS = 180
NEAR_TERMINAL_BARS = 5
PINE_CAPACITY = 5000


@dataclass(frozen=True, slots=True)
class Event:
    detector: str
    instrument_id: str
    pattern_id: str
    direction: str
    source_nodes: tuple[int, ...]
    known_at: int
    terminal_bar: int
    scale_support: tuple[int, ...]
    min_skipped_pivots: int | None = None

    @property
    def structure_key(self) -> tuple[str, str, tuple[int, ...]]:
        return self.pattern_id, self.direction, self.source_nodes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    return parser.parse_args()


def _date(frame: pd.DataFrame, index: int) -> str:
    return pd.Timestamp(frame.iloc[index]["trade_date"]).date().isoformat()


def _v2_events(
    frame: pd.DataFrame,
    instrument_id: str,
    *,
    scales: tuple[int, ...],
    detector_name: str,
) -> list[Event]:
    scan = scan_source_completion_events(
        frame,
        scales=scales,
        lifetime_bars=LIFETIME_BARS,
    )
    return [
        Event(
            detector=detector_name,
            instrument_id=instrument_id,
            pattern_id=item.pattern_id,
            direction=item.direction.value,
            source_nodes=item.source_nodes,
            known_at=item.known_at,
            terminal_bar=item.terminal_bar,
            scale_support=item.projection.scales,
            min_skipped_pivots=item.projection.min_skipped_pivots,
        )
        for item in scan.completions
        if item.pattern_id in SOURCE_CLEARED_STANDARD
    ]


def _pine_events(frame: pd.DataFrame, instrument_id: str) -> list[Event]:
    scan = scan_pine_r34(
        frame,
        capacity=PINE_CAPACITY,
        unqualified_storage_limit=PINE_CAPACITY,
    )
    out: list[Event] = []
    for item in scan.candidates:
        if item.pattern_id not in SOURCE_CLEARED_STANDARD:
            continue
        if item.schema != "XABCD" or not item.qualified:
            continue
        if item.first_test_bar is None:
            continue
        out.append(
            Event(
                detector="pine_r34_first_test",
                instrument_id=instrument_id,
                pattern_id=item.pattern_id,
                direction="bullish" if item.direction == 1 else "bearish",
                source_nodes=tuple(int(node.index) for node in item.source_nodes),
                known_at=int(item.born_bar),
                terminal_bar=int(item.first_test_bar),
                scale_support=(int(item.scale),),
                min_skipped_pivots=None,
            )
        )
    return out


def _nearest(
    source: Event,
    candidates: list[Event],
    *,
    same_family: bool,
) -> tuple[Event, int, int] | None:
    compatible = [
        item
        for item in candidates
        if item.direction == source.direction
        and (not same_family or item.pattern_id == source.pattern_id)
    ]
    if not compatible:
        return None
    best = min(
        compatible,
        key=lambda item: (
            abs(item.terminal_bar - source.terminal_bar),
            sum(
                abs(a - b)
                for a, b in zip(source.source_nodes, item.source_nodes, strict=True)
            ),
        ),
    )
    terminal_offset = best.terminal_bar - source.terminal_bar
    node_offset = sum(
        abs(a - b)
        for a, b in zip(source.source_nodes, best.source_nodes, strict=True)
    )
    return best, terminal_offset, node_offset


def _row(
    event: Event,
    frame: pd.DataFrame,
    *,
    name: str,
    bucket: str,
) -> dict[str, Any]:
    return {
        "detector": event.detector,
        "instrument_id": event.instrument_id,
        "name": name,
        "bucket": bucket,
        "pattern_id": event.pattern_id,
        "direction": event.direction,
        "source_nodes": list(event.source_nodes),
        "source_dates": [_date(frame, index) for index in event.source_nodes],
        "known_at": event.known_at,
        "known_date": _date(frame, event.known_at),
        "terminal_bar": event.terminal_bar,
        "terminal_date": _date(frame, event.terminal_bar),
        "scale_support": list(event.scale_support),
        "scale_support_count": len(event.scale_support),
        "min_skipped_pivots": event.min_skipped_pivots,
        "age_to_terminal": event.terminal_bar - event.known_at,
    }


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    start = str(manifest["start_date"])
    cutoff = str(manifest["snapshot_cutoff"])
    max_bars = int(manifest["max_bars"])
    minimum_symbols = int(manifest.get("minimum_successful_symbols", 1))

    failures: list[dict[str, str]] = []
    symbol_reports: list[dict[str, Any]] = []
    high_information: list[dict[str, Any]] = []
    totals = {
        "v2": 0,
        "v2_pine_scales": 0,
        "pine": 0,
        "exact_structure_common": 0,
        "pine_scale_exact_structure_common": 0,
        "pine_scale_exact_structure_terminal_within_5": 0,
        "pine_scale_same_family_terminal_within_5": 0,
        "pine_scale_any_family_terminal_within_5": 0,
        "exact_structure_terminal_within_5": 0,
        "v2_same_family_terminal_within_5": 0,
        "pine_same_family_terminal_within_5": 0,
        "v2_any_family_terminal_within_5": 0,
        "pine_any_family_terminal_within_5": 0,
    }

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
        name = str(instrument.get("name") or instrument_id)
        bucket = str(instrument.get("bucket") or "")
        v2 = _v2_events(
            frame,
            instrument_id,
            scales=V2_NATIVE_SCALES,
            detector_name="hierarchical_v2_native",
        )
        v2_pine_scales = _v2_events(
            frame,
            instrument_id,
            scales=PINE_MATCHED_SCALES,
            detector_name="hierarchical_v2_pine_scales",
        )
        pine = _pine_events(frame, instrument_id)
        totals["v2"] += len(v2)
        totals["pine"] += len(pine)

        v2_exact = {item.structure_key: item for item in v2}
        pine_exact = {item.structure_key: item for item in pine}
        common_keys = set(v2_exact) & set(pine_exact)
        exact_near = sum(
            abs(v2_exact[key].terminal_bar - pine_exact[key].terminal_bar)
            <= NEAR_TERMINAL_BARS
            for key in common_keys
        )

        v2_pine_exact = {item.structure_key: item for item in v2_pine_scales}
        pine_scale_common_keys = set(v2_pine_exact) & set(pine_exact)
        pine_scale_exact_near = sum(
            abs(v2_pine_exact[key].terminal_bar - pine_exact[key].terminal_bar)
            <= NEAR_TERMINAL_BARS
            for key in pine_scale_common_keys
        )
        totals["exact_structure_common"] += len(common_keys)
        totals["exact_structure_terminal_within_5"] += exact_near

        totals["v2_pine_scales"] += len(v2_pine_scales)
        totals["pine_scale_exact_structure_common"] += len(pine_scale_common_keys)
        totals["pine_scale_exact_structure_terminal_within_5"] += pine_scale_exact_near
        totals["pine_scale_same_family_terminal_within_5"] += sum(
            1
            for item in v2_pine_scales
            if (
                (nearest := _nearest(item, pine, same_family=True)) is not None
                and abs(nearest[1]) <= NEAR_TERMINAL_BARS
            )
        )
        totals["pine_scale_any_family_terminal_within_5"] += sum(
            1
            for item in v2_pine_scales
            if (
                (nearest := _nearest(item, pine, same_family=False)) is not None
                and abs(nearest[1]) <= NEAR_TERMINAL_BARS
            )
        )

        v2_same_near = 0
        v2_any_near = 0
        for item in v2:
            same = _nearest(item, pine, same_family=True)
            any_family = _nearest(item, pine, same_family=False)
            if same is not None and abs(same[1]) <= NEAR_TERMINAL_BARS:
                v2_same_near += 1
            if any_family is not None and abs(any_family[1]) <= NEAR_TERMINAL_BARS:
                v2_any_near += 1
            if same is None or abs(same[1]) > NEAR_TERMINAL_BARS:
                row = _row(item, frame, name=name, bucket=bucket)
                row["disagreement"] = "v2_without_near_pine_same_family"
                row["nearest_pine_same_family"] = (
                    None
                    if same is None
                    else {
                        "pattern_id": same[0].pattern_id,
                        "source_nodes": list(same[0].source_nodes),
                        "terminal_bar": same[0].terminal_bar,
                        "terminal_date": _date(frame, same[0].terminal_bar),
                        "terminal_offset": same[1],
                        "sum_abs_source_node_offset": same[2],
                    }
                )
                row["audit_priority"] = (
                    (12 if item.min_skipped_pivots is not None and item.min_skipped_pivots >= 8 else 0)
                    + (6 if len(item.scale_support) == 1 else 0)
                    + min(10, max(0, item.terminal_bar - item.known_at) // 20)
                )
                high_information.append(row)

        pine_same_near = 0
        pine_any_near = 0
        for item in pine:
            same = _nearest(item, v2, same_family=True)
            any_family = _nearest(item, v2, same_family=False)
            if same is not None and abs(same[1]) <= NEAR_TERMINAL_BARS:
                pine_same_near += 1
            if any_family is not None and abs(any_family[1]) <= NEAR_TERMINAL_BARS:
                pine_any_near += 1
            if same is None or abs(same[1]) > NEAR_TERMINAL_BARS:
                row = _row(item, frame, name=name, bucket=bucket)
                row["disagreement"] = "pine_without_near_v2_same_family"
                row["nearest_v2_same_family"] = (
                    None
                    if same is None
                    else {
                        "pattern_id": same[0].pattern_id,
                        "source_nodes": list(same[0].source_nodes),
                        "terminal_bar": same[0].terminal_bar,
                        "terminal_date": _date(frame, same[0].terminal_bar),
                        "terminal_offset": same[1],
                        "sum_abs_source_node_offset": same[2],
                    }
                )
                row["audit_priority"] = 20 + min(
                    10,
                    max(0, item.terminal_bar - item.known_at) // 20,
                )
                high_information.append(row)

        totals["v2_same_family_terminal_within_5"] += v2_same_near
        totals["pine_same_family_terminal_within_5"] += pine_same_near
        totals["v2_any_family_terminal_within_5"] += v2_any_near
        totals["pine_any_family_terminal_within_5"] += pine_any_near

        symbol_reports.append(
            {
                "instrument_id": instrument_id,
                "name": name,
                "bucket": bucket,
                "bars": len(frame),
                "v2_completions": len(v2),
                "v2_pine_scale_completions": len(v2_pine_scales),
                "pine_completions": len(pine),
                "exact_structure_common": len(common_keys),
                "pine_scale_exact_structure_common": len(pine_scale_common_keys),
                "exact_structure_terminal_within_5": exact_near,
                "v2_same_family_terminal_within_5": v2_same_near,
                "pine_same_family_terminal_within_5": pine_same_near,
            }
        )

    loaded_symbols = len(symbol_reports)
    if loaded_symbols < minimum_symbols:
        raise SystemExit(
            f"insufficient differential snapshots: loaded={loaded_symbols} minimum={minimum_symbols}"
        )

    v2_total = totals["v2"]
    pine_total = totals["pine"]
    report = {
        "schema": 1,
        "gate_id": "recognition-gate4b-pine-r34-differential-v1",
        "dataset_id": manifest.get("dataset_id"),
        "snapshot_cutoff": cutoff,
        "raw_market_data_modified": False,
        "loaded_symbols": loaded_symbols,
        "snapshot_failures": failures,
        "comparison": {
            "v2": (
                "event-sourced Hierarchical XABC -> frozen Source Raw PRZ -> "
                "validity clock -> PRZ-contact Source Terminal"
            ),
            "v2_native_scales": list(V2_NATIVE_SCALES),
            "v2_pine_matched_scales": list(PINE_MATCHED_SCALES),
            "pine": (
                "standalone Pine R3.4 behavioral-parity channel; source-cleared standard "
                "XABCD only; completed when Pine first_test_bar is observed"
            ),
            "near_terminal_bars": NEAR_TERMINAL_BARS,
            "pine_is_ground_truth": False,
        },
        "totals": {
            **totals,
            "exact_structure_common_rate_over_v2": (
                totals["exact_structure_common"] / v2_total if v2_total else 0.0
            ),
            "exact_structure_common_rate_over_pine": (
                totals["exact_structure_common"] / pine_total if pine_total else 0.0
            ),
            "v2_same_family_near_pine_rate": (
                totals["v2_same_family_terminal_within_5"] / v2_total
                if v2_total
                else 0.0
            ),
            "pine_same_family_near_v2_rate": (
                totals["pine_same_family_terminal_within_5"] / pine_total
                if pine_total
                else 0.0
            ),
            "v2_any_family_near_pine_rate": (
                totals["v2_any_family_terminal_within_5"] / v2_total
                if v2_total
                else 0.0
            ),
            "pine_any_family_near_v2_rate": (
                totals["pine_any_family_terminal_within_5"] / pine_total
                if pine_total
                else 0.0
            ),

            "pine_scale_exact_structure_common_rate_over_v2": (
                totals["pine_scale_exact_structure_common"] / totals["v2_pine_scales"]
                if totals["v2_pine_scales"]
                else 0.0
            ),
            "pine_scale_exact_structure_common_rate_over_pine": (
                totals["pine_scale_exact_structure_common"] / pine_total
                if pine_total
                else 0.0
            ),
            "pine_scale_same_family_near_pine_rate": (
                totals["pine_scale_same_family_terminal_within_5"]
                / totals["v2_pine_scales"]
                if totals["v2_pine_scales"]
                else 0.0
            ),
            "pine_scale_any_family_near_pine_rate": (
                totals["pine_scale_any_family_terminal_within_5"]
                / totals["v2_pine_scales"]
                if totals["v2_pine_scales"]
                else 0.0
            ),
        },
        "symbols": symbol_reports,
        "high_information_disagreements": sorted(
            high_information,
            key=lambda row: (
                -int(row["audit_priority"]),
                row["instrument_id"],
                row["terminal_bar"],
                row["pattern_id"],
            ),
        )[:160],
        "interpretation_boundary": (
            "Pine R3.4 is a disagreement miner, not ground truth. Native V2 uses different "
            "pivot scales, so this report also runs a diagnostic V2 copy on Pine's 5/10/20 "
            "scales to separate scale mismatch from algorithm mismatch. Neither comparison "
            "authorizes tuning Detector V2 to Pine."
        ),
    }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
