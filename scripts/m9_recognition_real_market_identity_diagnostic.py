from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from htcn.harmonic.candidates import iter_completed_xabcd_windows
from htcn.harmonic.discovery import iter_hierarchical_xabcd_windows
from htcn.harmonic.evaluator import audit_xabcd_identity
from htcn.harmonic.pivots import detect_multi_scale_pivots
from htcn.harmonic.scanner import executable_xabcd_rules
from htcn.research.snapshot_cache import load_research_snapshot

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "research" / "a-share-research-universe-v1.json"
DEFAULT_DATA_DIR = ROOT / "artifacts" / "ci-research" / "data"
REPORT_PATH = ROOT / "artifacts" / "reports" / "m9-recognition-real-market-identity-diagnostic.json"

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
class Candidate:
    detector: str
    instrument_id: str
    nodes: tuple[int, ...]
    prices: tuple[float, ...]
    scales: tuple[int, ...]

    @property
    def key(self) -> tuple[str, str, tuple[int, ...]]:
        return self.detector, self.instrument_id, self.nodes


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


def _merge(store: dict, item: Candidate) -> None:
    prior = store.get(item.key)
    if prior is None:
        store[item.key] = item
        return
    store[item.key] = Candidate(
        detector=item.detector,
        instrument_id=item.instrument_id,
        nodes=item.nodes,
        prices=item.prices,
        scales=tuple(sorted(set(prior.scales) | set(item.scales))),
    )


def _candidate_ok(nodes: tuple[int, ...], size: int) -> bool:
    return nodes[0] >= LEFT_EDGE_GUARD and nodes[-1] >= size - D_RECENCY_BARS


def _collect_window(
    frame: pd.DataFrame,
    *,
    instrument_id: str,
    base_index: int,
) -> tuple[tuple[Candidate, ...], tuple[Candidate, ...]]:
    legacy: dict = {}
    v2: dict = {}
    pivots_by_scale = detect_multi_scale_pivots(frame, scales=SCALES)

    for scale, pivots in pivots_by_scale.items():
        for window in iter_completed_xabcd_windows(pivots):
            points = window.harmonic_points()
            local_nodes = tuple(int(point.index) for point in points)
            if not _candidate_ok(local_nodes, len(frame)):
                continue
            item = Candidate(
                detector="legacy_consecutive",
                instrument_id=instrument_id,
                nodes=tuple(base_index + value for value in local_nodes),
                prices=tuple(float(point.price) for point in points),
                scales=(int(scale),),
            )
            _merge(legacy, item)

        for candidate in iter_hierarchical_xabcd_windows(
            pivots,
            recent_pivots=V2_RECENT_PIVOTS,
            max_leg_step=V2_MAX_LEG_STEP,
            max_total_skips=V2_MAX_TOTAL_SKIPS,
        ):
            points = candidate.window.harmonic_points()
            local_nodes = tuple(int(point.index) for point in points)
            if not _candidate_ok(local_nodes, len(frame)):
                continue
            item = Candidate(
                detector="hierarchical_v2",
                instrument_id=instrument_id,
                nodes=tuple(base_index + value for value in local_nodes),
                prices=tuple(float(point.price) for point in points),
                scales=(int(scale),),
            )
            _merge(v2, item)

    return tuple(legacy.values()), tuple(v2.values())


def _points(candidate: Candidate):
    from htcn.harmonic.models import HarmonicPoint

    return tuple(
        HarmonicPoint(label, index, price)
        for label, index, price in zip(
            ("X", "A", "B", "C", "D"),
            candidate.nodes,
            candidate.prices,
            strict=True,
        )
    )


def _audit_candidates(candidates: list[Candidate], frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    rules = executable_xabcd_rules()
    nearest_rule_counts: Counter[str] = Counter()
    failed_checks: Counter[str] = Counter()
    failed_count_hist: Counter[int] = Counter()
    passed = 0
    near_miss_count = 0
    degenerate_count = 0
    degenerate_examples = []
    near_misses = []

    for candidate in candidates:
        points = _points(candidate)
        per_rule = []
        try:
            for rule in rules:
                result = audit_xabcd_identity(rule, points)
                failed = tuple(check for check in result.checks if not check.passed)
                score = (
                    len(result.reasons),
                    sum(
                        (
                            check.relative_error
                            if check.relative_error is not None
                            else check.distance_to_canonical
                        )
                        for check in failed
                    ),
                )
                per_rule.append((score, rule.pattern_id, result, failed))
        except ValueError as exc:
            degenerate_count += 1
            if len(degenerate_examples) < 40:
                degenerate_examples.append(
                    {
                        "detector": candidate.detector,
                        "instrument_id": candidate.instrument_id,
                        "nodes": list(candidate.nodes),
                        "prices": [round(value, 6) for value in candidate.prices],
                        "error": str(exc),
                    }
                )
            continue

        per_rule.sort(key=lambda item: (item[0], item[1]))
        _, pattern_id, result, failed = per_rule[0]
        nearest_rule_counts[pattern_id] += 1
        failed_count_hist[len(result.reasons)] += 1
        if result.passed:
            passed += 1
            continue

        for check in failed:
            failed_checks[check.name] += 1

        if len(result.reasons) == 1:
            near_miss_count += 1
        if len(result.reasons) == 1 and len(near_misses) < 120:
            frame = frames[candidate.instrument_id]
            dates = [
                pd.Timestamp(frame.iloc[index]["trade_date"]).date().isoformat()
                for index in candidate.nodes
            ]
            near_misses.append(
                {
                    "detector": candidate.detector,
                    "instrument_id": candidate.instrument_id,
                    "nearest_pattern": pattern_id,
                    "nodes": list(candidate.nodes),
                    "dates": dates,
                    "prices": [round(value, 6) for value in candidate.prices],
                    "scale_support": list(candidate.scales),
                    "reason": result.reasons[0],
                    "failed_checks": [
                        {
                            "name": check.name,
                            "value": check.value,
                            "target": check.target,
                            "relative_error": check.relative_error,
                            "distance_to_canonical": check.distance_to_canonical,
                        }
                        for check in failed
                    ],
                }
            )

    return {
        "candidate_count": len(candidates),
        "identity_pass_count": passed,
        "identity_pass_rate": passed / len(candidates) if candidates else 0.0,
        "degenerate_geometry_count": degenerate_count,
        "degenerate_geometry_examples": degenerate_examples,
        "nearest_rule_counts": dict(nearest_rule_counts.most_common()),
        "failed_reason_count_histogram": {
            str(key): value for key, value in sorted(failed_count_hist.items())
        },
        "top_failed_checks": failed_checks.most_common(20),
        "near_miss_one_reason_count": near_miss_count,
        "near_miss_examples": near_misses,
    }


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    start = str(manifest["start_date"])
    cutoff = str(manifest["snapshot_cutoff"])
    max_bars = int(manifest["max_bars"])

    legacy_store: dict = {}
    v2_store: dict = {}
    frames: dict[str, pd.DataFrame] = {}
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
        for end in _window_ends(len(frame)):
            window_start = max(0, end - WINDOW_BARS)
            window = frame.iloc[window_start:end].reset_index(drop=True)
            legacy, v2 = _collect_window(
                window,
                instrument_id=instrument_id,
                base_index=window_start,
            )
            for candidate in legacy:
                _merge(legacy_store, candidate)
            for candidate in v2:
                _merge(v2_store, candidate)

    report = {
        "schema": 1,
        "gate_id": "recognition-real-market-identity-diagnostic-v1",
        "snapshot_dataset_id": manifest.get("dataset_id"),
        "snapshot_cutoff": cutoff,
        "raw_market_data_modified": False,
        "loaded_symbols": len(frames),
        "snapshot_failures": failures,
        "source_cleared_rules": [rule.pattern_id for rule in executable_xabcd_rules()],
        "legacy": _audit_candidates(list(legacy_store.values()), frames),
        "hierarchical_v2": _audit_candidates(list(v2_store.values()), frames),
        "interpretation_boundary": (
            "This report explains why structural real-market XABCD candidates fail or pass "
            "the frozen source-cleared identity rules. It does not authorize tolerance changes. "
            "A dominant rejection reason is a diagnostic fact, not permission to loosen Carney rules."
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
