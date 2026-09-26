from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any

import pandas as pd

from htcn.harmonic.candidates import iter_completed_xabcd_windows
from htcn.harmonic.discovery import iter_hierarchical_xabcd_windows
from htcn.harmonic.pivots import detect_multi_scale_pivots
from htcn.harmonic.scanner import classify_completed_xabcd
from htcn.research.snapshot_cache import load_research_snapshot

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "research" / "a-share-research-universe-v1.json"
DEFAULT_DATA_DIR = ROOT / "artifacts" / "ci-research" / "data"
REPORT_PATH = ROOT / "artifacts" / "reports" / "m9-recognition-real-market-disagreement.json"

SCALES = (3, 5, 8)
WINDOW_BARS = 480
HISTORY_BARS = 1600
STEP_BARS = 160
D_RECENCY_BARS = 160
LEFT_EDGE_GUARD = 20
V2_RECENT_PIVOTS = 20
V2_MAX_LEG_STEP = 7
V2_MAX_TOTAL_SKIPS = 12


@dataclass(frozen=True, slots=True)
class Detection:
    detector: str
    instrument_id: str
    pattern_id: str
    direction: str
    nodes: tuple[int, ...]
    prices: tuple[float, ...]
    scales: tuple[int, ...]
    min_total_skips: int
    min_max_leg_step: int

    @property
    def key(self) -> tuple[str, str, str, tuple[int, ...]]:
        return self.instrument_id, self.pattern_id, self.direction, self.nodes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    return parser.parse_args()


def _window_ends(size: int) -> tuple[int, ...]:
    if size <= WINDOW_BARS:
        return (size,)
    first = max(WINDOW_BARS, size - HISTORY_BARS + WINDOW_BARS)
    ends = list(range(first, size + 1, STEP_BARS))
    if not ends or ends[-1] != size:
        ends.append(size)
    return tuple(sorted(set(ends)))


def _merge(
    store: dict[tuple[str, str, str, tuple[int, ...]], Detection],
    item: Detection,
) -> None:
    prior = store.get(item.key)
    if prior is None:
        store[item.key] = item
        return
    store[item.key] = Detection(
        detector=item.detector,
        instrument_id=item.instrument_id,
        pattern_id=item.pattern_id,
        direction=item.direction,
        nodes=item.nodes,
        prices=item.prices,
        scales=tuple(sorted(set(prior.scales) | set(item.scales))),
        min_total_skips=min(prior.min_total_skips, item.min_total_skips),
        min_max_leg_step=min(prior.min_max_leg_step, item.min_max_leg_step),
    )


def _legacy_window(
    frame: pd.DataFrame,
    *,
    instrument_id: str,
    base_index: int,
) -> tuple[Detection, ...]:
    out: dict[tuple[str, str, str, tuple[int, ...]], Detection] = {}
    pivots_by_scale = detect_multi_scale_pivots(frame, scales=SCALES)
    for scale, pivots in pivots_by_scale.items():
        for window in iter_completed_xabcd_windows(pivots):
            points = window.harmonic_points()
            local_nodes = tuple(int(point.index) for point in points)
            if local_nodes[0] < LEFT_EDGE_GUARD:
                continue
            if local_nodes[-1] < len(frame) - D_RECENCY_BARS:
                continue
            absolute_nodes = tuple(base_index + value for value in local_nodes)
            prices = tuple(float(point.price) for point in points)
            for result in classify_completed_xabcd(window):
                _merge(
                    out,
                    Detection(
                        detector="legacy_consecutive",
                        instrument_id=instrument_id,
                        pattern_id=result.pattern_id,
                        direction=result.direction.value,
                        nodes=absolute_nodes,
                        prices=prices,
                        scales=(int(scale),),
                        min_total_skips=0,
                        min_max_leg_step=1,
                    ),
                )
    return tuple(out.values())


def _positions_for_nodes(pivots, nodes: tuple[int, ...]) -> tuple[int, ...] | None:
    index_to_position = {int(pivot.index): idx for idx, pivot in enumerate(pivots)}
    positions = tuple(index_to_position.get(value) for value in nodes)
    if any(value is None for value in positions):
        return None
    return tuple(int(value) for value in positions if value is not None)


def _v2_window(
    frame: pd.DataFrame,
    *,
    instrument_id: str,
    base_index: int,
) -> tuple[Detection, ...]:
    out: dict[tuple[str, str, str, tuple[int, ...]], Detection] = {}
    pivots_by_scale = detect_multi_scale_pivots(frame, scales=SCALES)
    for scale, pivots in pivots_by_scale.items():
        for candidate in iter_hierarchical_xabcd_windows(
            pivots,
            recent_pivots=V2_RECENT_PIVOTS,
            max_leg_step=V2_MAX_LEG_STEP,
            max_total_skips=V2_MAX_TOTAL_SKIPS,
        ):
            points = candidate.window.harmonic_points()
            local_nodes = tuple(int(point.index) for point in points)
            if local_nodes[0] < LEFT_EDGE_GUARD:
                continue
            if local_nodes[-1] < len(frame) - D_RECENCY_BARS:
                continue
            positions = _positions_for_nodes(pivots, local_nodes)
            if positions is None:
                continue
            steps = tuple(right - left for left, right in pairwise(positions))
            absolute_nodes = tuple(base_index + value for value in local_nodes)
            prices = tuple(float(point.price) for point in points)
            for result in classify_completed_xabcd(candidate.window):
                _merge(
                    out,
                    Detection(
                        detector="hierarchical_v2",
                        instrument_id=instrument_id,
                        pattern_id=result.pattern_id,
                        direction=result.direction.value,
                        nodes=absolute_nodes,
                        prices=prices,
                        scales=(int(scale),),
                        min_total_skips=sum(step - 1 for step in steps),
                        min_max_leg_step=max(steps),
                    ),
                )
    return tuple(out.values())


def _collect_symbol(
    frame: pd.DataFrame,
    *,
    instrument_id: str,
) -> tuple[dict, dict]:
    legacy: dict[tuple[str, str, str, tuple[int, ...]], Detection] = {}
    v2: dict[tuple[str, str, str, tuple[int, ...]], Detection] = {}
    size = len(frame)
    for end in _window_ends(size):
        start = max(0, end - WINDOW_BARS)
        window = frame.iloc[start:end].reset_index(drop=True)
        for item in _legacy_window(window, instrument_id=instrument_id, base_index=start):
            _merge(legacy, item)
        for item in _v2_window(window, instrument_id=instrument_id, base_index=start):
            _merge(v2, item)
    return legacy, v2


def _nearest_shift(
    source: Detection,
    candidates: list[Detection],
) -> dict[str, Any] | None:
    compatible = [
        item
        for item in candidates
        if item.instrument_id == source.instrument_id
        and item.pattern_id == source.pattern_id
        and item.direction == source.direction
        and abs(item.nodes[-1] - source.nodes[-1]) <= 20
    ]
    if not compatible:
        return None
    best = min(
        compatible,
        key=lambda item: (
            sum(abs(a - b) for a, b in zip(source.nodes, item.nodes, strict=True)),
            abs(source.nodes[-1] - item.nodes[-1]),
        ),
    )
    offsets = tuple(b - a for a, b in zip(source.nodes, best.nodes, strict=True))
    return {
        "other_nodes": list(best.nodes),
        "node_offsets": list(offsets),
        "sum_abs_node_offset": sum(abs(value) for value in offsets),
    }


def _row(item: Detection, frame: pd.DataFrame, name: str, bucket: str) -> dict[str, Any]:
    dates = [
        pd.Timestamp(frame.iloc[index]["trade_date"]).date().isoformat()
        for index in item.nodes
        if 0 <= index < len(frame)
    ]
    return {
        "instrument_id": item.instrument_id,
        "name": name,
        "bucket": bucket,
        "pattern_id": item.pattern_id,
        "direction": item.direction,
        "nodes": list(item.nodes),
        "dates": dates,
        "prices": [round(value, 6) for value in item.prices],
        "scale_support": list(item.scales),
        "scale_support_count": len(item.scales),
        "min_total_skips": item.min_total_skips,
        "min_max_leg_step": item.min_max_leg_step,
        "span_bars": item.nodes[-1] - item.nodes[0],
    }


def _cluster_stats(items: list[Detection]) -> dict[str, Any]:
    groups: dict[tuple[str, str, str], list[Detection]] = defaultdict(list)
    for item in items:
        groups[(item.instrument_id, item.pattern_id, item.direction)].append(item)
    cluster_sizes: list[int] = []
    for rows in groups.values():
        ordered = sorted(rows, key=lambda item: item.nodes[-1])
        current: list[Detection] = []
        prior_d: int | None = None
        for item in ordered:
            d = item.nodes[-1]
            if prior_d is None or d - prior_d <= 5:
                current.append(item)
            else:
                cluster_sizes.append(len(current))
                current = [item]
            prior_d = d
        if current:
            cluster_sizes.append(len(current))
    return {
        "cluster_count": len(cluster_sizes),
        "clusters_ge_3": sum(value >= 3 for value in cluster_sizes),
        "max_cluster_size": max(cluster_sizes, default=0),
    }


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    start = str(manifest["start_date"])
    cutoff = str(manifest["snapshot_cutoff"])
    max_bars = int(manifest["max_bars"])

    legacy_all: dict = {}
    v2_all: dict = {}
    frames: dict[str, pd.DataFrame] = {}
    metadata: dict[str, dict[str, str]] = {}
    failures = []

    for item in manifest["instruments"]:
        instrument_id = str(item["instrument_id"])
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
        frames[instrument_id] = frame
        metadata[instrument_id] = {
            "name": str(item.get("name") or instrument_id),
            "bucket": str(item.get("bucket") or ""),
        }
        legacy, v2 = _collect_symbol(frame, instrument_id=instrument_id)
        legacy_all.update(legacy)
        v2_all.update(v2)

    legacy_keys = set(legacy_all)
    v2_keys = set(v2_all)
    common_keys = legacy_keys & v2_keys
    v2_only_keys = v2_keys - legacy_keys
    legacy_only_keys = legacy_keys - v2_keys

    v2_only = [v2_all[key] for key in sorted(v2_only_keys)]
    legacy_only = [legacy_all[key] for key in sorted(legacy_only_keys)]
    common = [v2_all[key] for key in sorted(common_keys)]

    v2_only_rows = []
    for item in v2_only:
        meta = metadata[item.instrument_id]
        row = _row(item, frames[item.instrument_id], meta["name"], meta["bucket"])
        row["nearest_legacy_same_family"] = _nearest_shift(
            item,
            list(legacy_all.values()),
        )
        row["audit_priority"] = (
            3 * len(item.scales)
            + (2 if item.min_max_leg_step <= 5 else 0)
            + (1 if item.min_total_skips <= 8 else 0)
        )
        v2_only_rows.append(row)

    legacy_only_rows = []
    for item in legacy_only:
        meta = metadata[item.instrument_id]
        row = _row(item, frames[item.instrument_id], meta["name"], meta["bucket"])
        row["nearest_v2_same_family"] = _nearest_shift(item, list(v2_all.values()))
        legacy_only_rows.append(row)

    audited_bars = sum(min(HISTORY_BARS, len(frame)) for frame in frames.values())
    report = {
        "schema": 1,
        "gate_id": "recognition-real-market-disagreement-gate4-v1",
        "snapshot_dataset_id": manifest.get("dataset_id"),
        "snapshot_cutoff": cutoff,
        "raw_market_data_modified": False,
        "detectors": {
            "legacy": "same-scale consecutive completed XABCD + canonical classifier",
            "v2": {
                "name": "hierarchical swing graph + canonical classifier",
                "scales": list(SCALES),
                "recent_pivots": V2_RECENT_PIVOTS,
                "max_leg_step": V2_MAX_LEG_STEP,
                "max_total_skips": V2_MAX_TOTAL_SKIPS,
            },
        },
        "audit_sampling": {
            "history_bars_per_symbol_max": HISTORY_BARS,
            "window_bars": WINDOW_BARS,
            "window_step_bars": STEP_BARS,
            "D_recency_bars": D_RECENCY_BARS,
            "left_edge_guard": LEFT_EDGE_GUARD,
        },
        "loaded_symbols": len(frames),
        "snapshot_failures": failures,
        "audited_symbol_bars": audited_bars,
        "counts": {
            "legacy_unique": len(legacy_keys),
            "v2_unique": len(v2_keys),
            "exact_common": len(common_keys),
            "v2_only": len(v2_only_keys),
            "legacy_only": len(legacy_only_keys),
            "union": len(legacy_keys | v2_keys),
        },
        "rates": {
            "exact_agreement_over_union": (
                len(common_keys) / len(legacy_keys | v2_keys)
                if legacy_keys | v2_keys
                else 1.0
            ),
            "legacy_per_1000_bars": len(legacy_keys) / audited_bars * 1000
            if audited_bars
            else 0.0,
            "v2_per_1000_bars": len(v2_keys) / audited_bars * 1000
            if audited_bars
            else 0.0,
        },
        "v2_cluster_pressure": _cluster_stats(list(v2_all.values())),
        "v2_only_complexity": {
            "single_scale": sum(len(item.scales) == 1 for item in v2_only),
            "multi_scale": sum(len(item.scales) >= 2 for item in v2_only),
            "max_leg_step_7": sum(item.min_max_leg_step == 7 for item in v2_only),
            "total_skips_ge_10": sum(item.min_total_skips >= 10 for item in v2_only),
        },
        "top_v2_only_for_audit": sorted(
            v2_only_rows,
            key=lambda row: (
                -int(row["audit_priority"]),
                -int(row["span_bars"]),
                row["instrument_id"],
                row["nodes"],
            ),
        )[:120],
        "top_legacy_only_for_audit": sorted(
            legacy_only_rows,
            key=lambda row: (
                -int(row["scale_support_count"]),
                -int(row["span_bars"]),
                row["instrument_id"],
                row["nodes"],
            ),
        )[:80],
        "common_sample": [
            _row(
                item,
                frames[item.instrument_id],
                metadata[item.instrument_id]["name"],
                metadata[item.instrument_id]["bucket"],
            )
            for item in common[:40]
        ],
        "interpretation_boundary": (
            "V2-only is not automatically true and legacy-only is not automatically false. "
            "This gate measures disagreement, density, graph complexity and audit priority on "
            "unmodified real A-share bars. Production promotion requires adjudication of the "
            "high-information disagreements."
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
