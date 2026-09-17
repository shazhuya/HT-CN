from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path

from htcn.harmonic.engine import scan_frame
from htcn.harmonic.rsi_bamm import RSIBammDirection, scan_rsi_bamm_frame
from htcn.harmonic.rsi_bamm_confluence import confirm_rsi_bamm_with_match
from htcn.research.snapshot_cache import load_research_snapshot


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "research" / "a-share-research-universe-v1.json"
DATA_DIR = ROOT / "artifacts" / "ci-research" / "data"
REPORT_PATH = ROOT / "artifacts" / "ci-research" / "m2-rsi-bamm-observability-v1.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Observe RSI BAMM frequency/confluence on frozen A-share snapshots without outcome fitting"
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--max-symbols", type=int, default=0)
    return parser.parse_args()


def _load_manifest(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not payload.get("instruments"):
        raise ValueError("research manifest has no instruments")
    return payload


def main() -> int:
    args = parse_args()
    manifest = _load_manifest(args.manifest)
    instruments = list(manifest["instruments"])
    if args.max_symbols > 0:
        instruments = instruments[: args.max_symbols]

    start = date.fromisoformat(str(manifest["start_date"]))
    end = date.fromisoformat(str(manifest["snapshot_cutoff"]))
    max_bars = int(manifest.get("max_bars", 3000))
    scales = tuple(int(value) for value in manifest.get("scales", [3, 5, 8, 13, 21]))

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    profile_counts: Counter[str] = Counter()
    relation_counts: Counter[str] = Counter()
    pattern_counts: Counter[str] = Counter()
    confirmed_pattern_counts: Counter[str] = Counter()
    blocked_status_counts: Counter[str] = Counter()
    symbols: list[dict] = []
    failures: list[dict] = []

    total_sequences = 0
    total_completed_matches = 0
    total_source_confirmed = 0
    confirmed_at_terminal = 0
    confirmed_after_terminal = 0

    for item in instruments:
        instrument_id = str(item["instrument_id"])
        snapshot, miss_reason = load_research_snapshot(
            DATA_DIR,
            instrument_id=instrument_id,
            requested_start=start,
            requested_end=end,
            max_bars=max_bars,
            price_mode="qfq",
        )
        if snapshot is None:
            failures.append({"instrument_id": instrument_id, "reason": miss_reason})
            continue

        frame = snapshot.frame.reset_index(drop=True)
        bullish = scan_rsi_bamm_frame(frame, direction=RSIBammDirection.BULLISH)
        bearish = scan_rsi_bamm_frame(frame, direction=RSIBammDirection.BEARISH)
        sequences_by_direction = {
            "bullish": bullish,
            "bearish": bearish,
        }
        sequence_count = len(bullish) + len(bearish)
        total_sequences += sequence_count
        for sequence in (*bullish, *bearish):
            profile_counts[sequence.profile.value] += 1
            relation_counts[sequence.relation.value] += 1

        scan = scan_frame(
            frame,
            scales=scales,
            include_source_conflict_patterns=False,
            max_completed=200,
            max_forming=120,
        )
        matches = (
            *scan.completed,
            *scan.abcd_completed,
            *scan.shark_completed,
        )
        total_completed_matches += len(matches)

        symbol_confirmed = 0
        symbol_late = 0
        for match in matches:
            pattern_counts[str(match.pattern_id)] += 1
            direction_sequences = sequences_by_direction[match.direction.value]
            match_confirmed = []
            for sequence in direction_sequences:
                confluence = confirm_rsi_bamm_with_match(sequence, match)
                if confluence.source_confirmed:
                    match_confirmed.append(confluence)
                elif confluence.temporal_alignment:
                    blocked_status_counts[confluence.status] += 1

            if not match_confirmed:
                continue

            confirmed_pattern_counts[str(match.pattern_id)] += 1
            total_source_confirmed += len(match_confirmed)
            symbol_confirmed += len(match_confirmed)
            terminal_bar = int(match.points[-1].index)
            for confluence in match_confirmed:
                available_from = max(terminal_bar, int(confluence.sequence.completion_bar))
                if available_from <= terminal_bar:
                    confirmed_at_terminal += 1
                else:
                    confirmed_after_terminal += 1
                    symbol_late += 1

        symbols.append(
            {
                "instrument_id": instrument_id,
                "name": item.get("name"),
                "bucket": item.get("bucket"),
                "bars": len(frame),
                "rsi_bamm_sequences": sequence_count,
                "completed_source_scannable_matches": len(matches),
                "source_confirmed_confluences": symbol_confirmed,
                "source_confirmed_after_pattern_terminal": symbol_late,
            }
        )

    report = {
        "schema_version": 1,
        "report_id": "m2-rsi-bamm-observability-v1",
        "purpose": (
            "Observability only. Counts source-defined RSI BAMM sequences and their temporal "
            "confluence with source-cleared harmonic matches on frozen A-share snapshots."
        ),
        "research_boundary": {
            "outcome_fitting": False,
            "quality_threshold_fitting": False,
            "identity_mutation": False,
            "source_raw_prz_mutation": False,
            "lookahead_policy": "BAMM evidence is timestamped no earlier than sequence completion.",
            "five_zero": "production quarantine; excluded from source-confirmed observability",
        },
        "dataset_id": manifest.get("dataset_id"),
        "snapshot_cutoff": manifest.get("snapshot_cutoff"),
        "requested_symbols": len(instruments),
        "successful_symbols": len(symbols),
        "failed_symbols": len(failures),
        "total_rsi_bamm_sequences": total_sequences,
        "profile_counts": dict(sorted(profile_counts.items())),
        "relation_counts": dict(sorted(relation_counts.items())),
        "total_completed_source_scannable_matches": total_completed_matches,
        "pattern_counts": dict(sorted(pattern_counts.items())),
        "source_confirmed_confluences": total_source_confirmed,
        "confirmed_pattern_counts": dict(sorted(confirmed_pattern_counts.items())),
        "source_confirmed_available_at_pattern_terminal": confirmed_at_terminal,
        "source_confirmed_after_pattern_terminal": confirmed_after_terminal,
        "temporally_aligned_blocked_statuses": dict(sorted(blocked_status_counts.items())),
        "symbols": symbols,
        "failures": failures,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        "[HT-CN M2.31 BAMM] "
        f"symbols={len(symbols)}/{len(instruments)} sequences={total_sequences} "
        f"matches={total_completed_matches} source_confirmed={total_source_confirmed} "
        f"at_terminal={confirmed_at_terminal} after_terminal={confirmed_after_terminal}"
    )
    print(f"[HT-CN M2.31 BAMM] report={REPORT_PATH.relative_to(ROOT)}")

    return 0 if symbols else 1


if __name__ == "__main__":
    raise SystemExit(main())
