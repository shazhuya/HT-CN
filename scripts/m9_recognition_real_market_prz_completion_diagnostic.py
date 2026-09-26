from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from htcn.harmonic.discovery import iter_hierarchical_xabc_windows
from htcn.harmonic.pivots import detect_multi_scale_pivots
from htcn.harmonic.scanner import project_forming_xabcd
from htcn.research.snapshot_cache import load_research_snapshot

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "research" / "a-share-research-universe-v1.json"
DEFAULT_DATA_DIR = ROOT / "artifacts" / "ci-research" / "data"
REPORT_PATH = ROOT / "artifacts" / "reports" / "m9-recognition-real-market-prz-completion.json"

SCALES = (3, 5, 8)
WINDOW_BARS = 480
HISTORY_BARS = 1600
STEP_BARS = 160
LEFT_EDGE_GUARD = 20
RECENT_PIVOTS = 20
MAX_LEG_STEP = 7
MAX_TOTAL_SKIPS = 12
LIFETIME_BARS = 180
MIN_FULL_HORIZON = 180


@dataclass(frozen=True, slots=True)
class Projection:
    instrument_id: str
    pattern_id: str
    direction: str
    nodes: tuple[int, ...]
    prices: tuple[float, ...]
    known_at: int
    source_prz_low: float
    source_prz_high: float
    xa_completion_price: float
    xa_completion_ratio: float
    scales: tuple[int, ...]

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


def _xa_component(projection) -> tuple[float, float] | None:
    component = next(
        (
            item
            for item in projection.prz.components
            if item.name == "XA completion"
        ),
        None,
    )
    if component is None:
        return None
    return float(component.midpoint), float(component.ratio_low)


def _merge(store: dict, item: Projection) -> None:
    prior = store.get(item.key)
    if prior is None:
        store[item.key] = item
        return
    store[item.key] = Projection(
        instrument_id=item.instrument_id,
        pattern_id=item.pattern_id,
        direction=item.direction,
        nodes=item.nodes,
        prices=item.prices,
        known_at=min(prior.known_at, item.known_at),
        source_prz_low=item.source_prz_low,
        source_prz_high=item.source_prz_high,
        xa_completion_price=item.xa_completion_price,
        xa_completion_ratio=item.xa_completion_ratio,
        scales=tuple(sorted(set(prior.scales) | set(item.scales))),
    )


def _collect_window(
    frame: pd.DataFrame,
    *,
    instrument_id: str,
    base_index: int,
) -> tuple[Projection, ...]:
    out: dict = {}
    pivots_by_scale = detect_multi_scale_pivots(frame, scales=SCALES)
    for scale, pivots in pivots_by_scale.items():
        for candidate in iter_hierarchical_xabc_windows(
            pivots,
            recent_pivots=RECENT_PIVOTS,
            max_leg_step=MAX_LEG_STEP,
            max_total_skips=MAX_TOTAL_SKIPS,
        ):
            window = candidate.window
            x, a, b, c = window.harmonic_points()
            local_nodes = (int(x.index), int(a.index), int(b.index), int(c.index))
            if local_nodes[0] < LEFT_EDGE_GUARD:
                continue
            projections = project_forming_xabcd(
                window,
                include_source_conflict_patterns=False,
            )
            for projected in projections:
                if not projected.prz.has_source_prz:
                    continue
                xa = _xa_component(projected)
                if xa is None:
                    continue
                xa_price, xa_ratio = xa
                local_known_at = max(int(pivot.confirmed_at) for pivot in window.pivots)
                item = Projection(
                    instrument_id=instrument_id,
                    pattern_id=projected.pattern_id,
                    direction=projected.direction.value,
                    nodes=tuple(base_index + value for value in local_nodes),
                    prices=(float(x.price), float(a.price), float(b.price), float(c.price)),
                    known_at=base_index + local_known_at,
                    source_prz_low=float(projected.prz.source_prz_low),
                    source_prz_high=float(projected.prz.source_prz_high),
                    xa_completion_price=xa_price,
                    xa_completion_ratio=xa_ratio,
                    scales=(int(scale),),
                )
                _merge(out, item)
    return tuple(out.values())


def _bar_overlaps(row: pd.Series, low: float, high: float) -> bool:
    return float(row["low"]) <= high and float(row["high"]) >= low


def _bar_contains(row: pd.Series, price: float) -> bool:
    return float(row["low"]) <= price <= float(row["high"])


def _evaluate_projection(item: Projection, frame: pd.DataFrame) -> dict[str, Any]:
    start = max(item.known_at, item.nodes[-1] + 1)
    stop = min(len(frame), start + LIFETIME_BARS)
    available = max(0, stop - start)
    first_touch: int | None = None
    xa_tested = False
    touch_extreme_ratio: float | None = None
    touch_extreme_error: float | None = None

    x_price, a_price, _, _ = item.prices
    xa_span = abs(a_price - x_price)

    for index in range(start, stop):
        row = frame.iloc[index]
        if not _bar_overlaps(row, item.source_prz_low, item.source_prz_high):
            continue
        first_touch = index
        xa_tested = _bar_contains(row, item.xa_completion_price)
        if xa_span > 0:
            terminal_extreme = (
                float(row["low"])
                if item.direction == "bullish"
                else float(row["high"])
            )
            touch_extreme_ratio = abs(a_price - terminal_extreme) / xa_span
            touch_extreme_error = abs(
                touch_extreme_ratio / item.xa_completion_ratio - 1.0
            )
        break

    return {
        "available_future_bars": available,
        "full_horizon": available >= MIN_FULL_HORIZON,
        "touched": first_touch is not None,
        "first_touch_bar": first_touch,
        "bars_to_touch": (
            first_touch - start if first_touch is not None else None
        ),
        "xa_completion_level_tested_on_touch_bar": xa_tested,
        "terminal_extreme_d_xa": touch_extreme_ratio,
        "terminal_extreme_relative_error_to_xa_completion": touch_extreme_error,
    }


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    touched = [row for row in rows if row["touched"]]
    full = [row for row in rows if row["full_horizon"]]
    full_touched = [row for row in full if row["touched"]]
    bars_to_touch = [
        int(row["bars_to_touch"])
        for row in touched
        if row["bars_to_touch"] is not None
    ]
    d_errors = [
        float(row["terminal_extreme_relative_error_to_xa_completion"])
        for row in touched
        if row["terminal_extreme_relative_error_to_xa_completion"] is not None
    ]
    return {
        "projection_count": len(rows),
        "touched_count": len(touched),
        "touch_rate_available_horizon": len(touched) / len(rows) if rows else 0.0,
        "full_180_bar_horizon_count": len(full),
        "full_horizon_touched_count": len(full_touched),
        "full_horizon_touch_rate": (
            len(full_touched) / len(full) if full else None
        ),
        "xa_completion_exact_level_tested_count": sum(
            bool(row["xa_completion_level_tested_on_touch_bar"])
            for row in touched
        ),
        "xa_completion_exact_level_test_rate_among_touches": (
            sum(
                bool(row["xa_completion_level_tested_on_touch_bar"])
                for row in touched
            )
            / len(touched)
            if touched
            else None
        ),
        "terminal_extreme_within_3pct_of_xa_ratio_count": sum(
            error <= 0.03 for error in d_errors
        ),
        "terminal_extreme_within_3pct_of_xa_ratio_rate_among_touches": (
            sum(error <= 0.03 for error in d_errors) / len(d_errors)
            if d_errors
            else None
        ),
        "bars_to_touch_median": statistics.median(bars_to_touch)
        if bars_to_touch
        else None,
        "bars_to_touch_p90": (
            sorted(bars_to_touch)[
                min(len(bars_to_touch) - 1, int(len(bars_to_touch) * 0.9))
            ]
            if bars_to_touch
            else None
        ),
    }


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    start = str(manifest["start_date"])
    cutoff = str(manifest["snapshot_cutoff"])
    max_bars = int(manifest["max_bars"])

    projections: dict = {}
    frames: dict[str, pd.DataFrame] = {}
    names: dict[str, str] = {}
    failures = []

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
        frames[instrument_id] = frame
        names[instrument_id] = str(instrument.get("name") or instrument_id)

        for end in _window_ends(len(frame)):
            window_start = max(0, end - WINDOW_BARS)
            window = frame.iloc[window_start:end].reset_index(drop=True)
            for item in _collect_window(
                window,
                instrument_id=instrument_id,
                base_index=window_start,
            ):
                _merge(projections, item)

    rows = []
    per_pattern: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in projections.values():
        result = _evaluate_projection(item, frames[item.instrument_id])
        row = {
            "instrument_id": item.instrument_id,
            "name": names[item.instrument_id],
            "pattern_id": item.pattern_id,
            "direction": item.direction,
            "nodes": list(item.nodes),
            "known_at": item.known_at,
            "source_prz_low": item.source_prz_low,
            "source_prz_high": item.source_prz_high,
            "xa_completion_price": item.xa_completion_price,
            "xa_completion_ratio": item.xa_completion_ratio,
            "scale_support": list(item.scales),
            **result,
        }
        rows.append(row)
        per_pattern[item.pattern_id].append(row)

    report = {
        "schema": 1,
        "gate_id": "recognition-real-market-prz-completion-diagnostic-v1",
        "snapshot_dataset_id": manifest.get("dataset_id"),
        "snapshot_cutoff": cutoff,
        "raw_market_data_modified": False,
        "loaded_symbols": len(frames),
        "snapshot_failures": failures,
        "detector": {
            "path": "hierarchical_xabc",
            "scales": list(SCALES),
            "recent_pivots": RECENT_PIVOTS,
            "max_leg_step": MAX_LEG_STEP,
            "max_total_skips": MAX_TOTAL_SKIPS,
            "source_conflict_patterns": False,
        },
        "completion_test": {
            "source": "frozen Source Raw PRZ projected from source-cleared XABC",
            "starts_at": "max(C pivot confirmation, C+1)",
            "lifetime_bars": LIFETIME_BARS,
            "touch_definition": "bar high/low overlaps Source Raw PRZ",
            "three_percent_metric": (
                "diagnostic comparison only; matches existing Pine/HT-CN operational "
                "3% family convention and does not mutate Source identity"
            ),
        },
        "overall": _summarize(rows),
        "by_pattern": {
            pattern: _summarize(pattern_rows)
            for pattern, pattern_rows in sorted(per_pattern.items())
        },
        "first_100_touches": [
            row for row in rows if row["touched"]
        ][:100],
        "interpretation_boundary": (
            "This is a counterfactual completion-semantic diagnostic. It does not promote "
            "XABC projections to completed identity and does not change Carney ratios. A high "
            "PRZ-touch rate alongside zero strict 5-pivot completions indicates a mismatch "
            "between projected-zone completion semantics and exact-D-pivot classification."
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
