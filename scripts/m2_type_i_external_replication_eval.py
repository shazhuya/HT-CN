from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd

from htcn.data.adjusted_fetch import fetch_adjusted_history
from htcn.data.providers import AkShareProvider, BaoStockProvider
from htcn.data.validation import normalize_daily
from htcn.research.autonomous_calibration import enrich_walk_forward_records
from htcn.research.snapshot_cache import (
    CachedResearchSnapshot,
    load_research_snapshot,
    snapshot_manifest_entry,
    write_research_snapshot,
)
from htcn.research.type_i_external_replication import evaluate_external_type_i_replication
from htcn.research.walk_forward import walk_forward_forming_signals


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "research" / "a-share-type-i-external-replication-universe-v1.json"
ORIGINAL_MANIFEST = ROOT / "research" / "a-share-research-universe-v1.json"
PREREG = ROOT / "research" / "m2-type-i-external-replication-prereg-v1.json"
AUTHORIZATION = ROOT / "research" / "m2-type-i-external-replication-open-v1.json"
SOURCE_RESULT = ROOT / "research" / "m2-type-i-holdout-result-v1.json"
SOURCE_AUTHORIZATION = ROOT / "research" / "m2-type-i-holdout-open-v1.json"
OUT_DIR = ROOT / "artifacts" / "external-replication"
DATA_DIR = OUT_DIR / "data"
OUTPUT = OUT_DIR / "m2-type-i-external-replication-evaluation.json"
SNAPSHOT_MANIFEST = OUT_DIR / "m2-type-i-external-replication-snapshot-manifest.json"


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()


def _ids(payload: dict) -> list[str]:
    return [str(row["instrument_id"]) for row in payload.get("instruments") or []]


def _research_snapshot(
    *,
    instrument_id: str,
    start: date,
    end: date,
    max_bars: int,
    providers: list,
) -> tuple[CachedResearchSnapshot, int, str]:
    cached, miss_reason = load_research_snapshot(
        DATA_DIR,
        instrument_id=instrument_id,
        requested_start=start,
        requested_end=end,
        max_bars=max_bars,
        price_mode="qfq",
    )
    if cached is not None:
        return cached, 0, miss_reason

    fetched = fetch_adjusted_history(
        instrument_id=instrument_id,
        start=start,
        end=end,
        providers=providers,
        mode="qfq",
        retries_per_provider=2,
        base_delay=0.5,
    )
    frame = normalize_daily(fetched.frame).tail(max_bars).reset_index(drop=True)
    snapshot = write_research_snapshot(
        DATA_DIR,
        instrument_id=instrument_id,
        frame=frame,
        source=fetched.source,
        requested_start=start,
        requested_end=end,
        max_bars=max_bars,
        price_mode="qfq",
    )
    return snapshot, fetched.attempts, miss_reason


def _validate_freeze(
    manifest: dict,
    original: dict,
    prereg: dict,
    authorization: dict,
    source_result: dict,
    source_authorization: dict,
) -> list[str]:
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    dataset = prereg.get("replication_dataset") or {}
    auth_dataset = authorization.get("dataset") or {}
    replication_ids = _ids(manifest)
    original_ids = _ids(original)

    require(len(replication_ids) == 60, "replication manifest must contain exactly 60 symbols")
    require(len(set(replication_ids)) == 60, "replication manifest contains duplicate symbols")
    require(
        not (set(replication_ids) & set(original_ids)),
        "replication manifest overlaps the consumed original research universe",
    )
    require(
        _git_blob_sha(MANIFEST) == dataset.get("manifest_git_blob_sha"),
        "replication manifest Git blob SHA differs from frozen preregistration",
    )
    require(
        auth_dataset.get("manifest_git_blob_sha") == dataset.get("manifest_git_blob_sha"),
        "authorization manifest SHA differs from preregistration",
    )
    require(
        manifest.get("dataset_id") == dataset.get("dataset_id") == auth_dataset.get("dataset_id"),
        "replication dataset id mismatch",
    )
    require(
        manifest.get("snapshot_cutoff")
        == dataset.get("snapshot_cutoff")
        == auth_dataset.get("snapshot_cutoff"),
        "replication snapshot cutoff mismatch",
    )
    require(
        authorization.get("authorized") is True
        and authorization.get("one_time_external_replication") is True,
        "explicit one-time external replication authorization is missing",
    )
    require(
        authorization.get("preregistration_id") == prereg.get("preregistration_id"),
        "authorization/preregistration id mismatch",
    )
    require(
        authorization.get("frozen_preregistration_commit")
        == "7f62ff4abde3e9154738e949233a9b6745b2461c",
        "authorization does not point to the frozen preregistration commit",
    )
    require(
        (source_result.get("primary_contrast") or {}).get("result") == "confirmed",
        "source M2.22 Type-I result is no longer frozen as confirmed",
    )
    require(source_result.get("holdout_consumed") is True, "source Holdout must remain consumed")
    require(
        source_authorization.get("authorized") is False
        and source_authorization.get("one_time_holdout_open") is False
        and source_authorization.get("evaluated_once") is True,
        "source Holdout authorization must remain permanently closed",
    )
    return failures


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    original = json.loads(ORIGINAL_MANIFEST.read_text(encoding="utf-8"))
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    authorization = json.loads(AUTHORIZATION.read_text(encoding="utf-8"))
    source_result = json.loads(SOURCE_RESULT.read_text(encoding="utf-8"))
    source_authorization = json.loads(SOURCE_AUTHORIZATION.read_text(encoding="utf-8"))

    failures = _validate_freeze(
        manifest,
        original,
        prereg,
        authorization,
        source_result,
        source_authorization,
    )
    if failures:
        for failure in failures:
            print(f"[HT-CN M2 EXT-REPL] FAIL: {failure}")
        return 2

    instruments = list(manifest["instruments"])
    start = date.fromisoformat(str(manifest["start_date"]))
    end = date.fromisoformat(str(manifest["snapshot_cutoff"]))
    max_bars = int(manifest.get("max_bars", 3000))
    forming_horizon = int(manifest.get("forming_horizon_bars", 60))
    scales = tuple(int(value) for value in manifest.get("scales", [3, 5, 8, 13, 21]))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    providers = [AkShareProvider(), BaoStockProvider()]
    all_records: list[dict] = []
    datasets: list[dict] = []
    failed_symbols: list[dict] = []
    snapshots: list[dict] = []
    cache_miss_reasons: Counter[str] = Counter()

    print(
        "[HT-CN M2 EXT-REPL] START "
        f"symbols={len(instruments)}, window={start}..{end}, bars<={max_bars}, "
        f"scales={scales}, forming_horizon={forming_horizon}"
    )

    for position, item in enumerate(instruments, start=1):
        instrument_id = str(item["instrument_id"])
        try:
            snapshot, attempts, cache_reason = _research_snapshot(
                instrument_id=instrument_id,
                start=start,
                end=end,
                max_bars=max_bars,
                providers=providers,
            )
            frame = snapshot.frame
            if len(frame) < 120:
                raise RuntimeError(f"too few QFQ bars: {len(frame)}")
            if pd.Timestamp(frame["trade_date"].max()).date() > end:
                raise RuntimeError("snapshot contains bars after the frozen cutoff")
            if snapshot.cache_status != "hit_verified":
                cache_miss_reasons[cache_reason] += 1

            signals = walk_forward_forming_signals(
                frame,
                scales=scales,
                horizon=forming_horizon,
            )
            enriched = enrich_walk_forward_records(
                signals,
                frame=frame,
                instrument_id=instrument_id,
                horizon=forming_horizon,
            )
            all_records.extend(enriched)
            snapshots.append(snapshot_manifest_entry(snapshot))
            datasets.append(
                {
                    "instrument_id": instrument_id,
                    "name": item.get("name"),
                    "bucket": item.get("bucket"),
                    "source": snapshot.source,
                    "attempts": attempts,
                    "cache_status": snapshot.cache_status,
                    "cache_miss_reason": (
                        None if snapshot.cache_status == "hit_verified" else cache_reason
                    ),
                    "bars": len(frame),
                    "first_trade_date": pd.Timestamp(frame.iloc[0]["trade_date"]).date().isoformat(),
                    "last_trade_date": pd.Timestamp(frame.iloc[-1]["trade_date"]).date().isoformat(),
                    "forming_signals": len(signals),
                    "sha256": snapshot.sha256,
                }
            )
            print(
                f"[HT-CN M2 EXT-REPL] {position}/{len(instruments)} OK {instrument_id}: "
                f"cache={snapshot.cache_status}, source={snapshot.source}, bars={len(frame)}, "
                f"forming={len(signals)}"
            )
        except Exception as exc:
            failed_symbols.append(
                {
                    "instrument_id": instrument_id,
                    "name": item.get("name"),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            print(
                f"[HT-CN M2 EXT-REPL] {position}/{len(instruments)} WARN {instrument_id}: "
                f"{type(exc).__name__}: {exc}"
            )

    snapshot_manifest = {
        "schema_version": 1,
        "dataset_id": manifest.get("dataset_id"),
        "snapshot_cutoff": manifest.get("snapshot_cutoff"),
        "price_mode": "qfq",
        "requested_symbols": len(instruments),
        "successful_symbols": len(datasets),
        "cache_hits": sum(row["cache_status"] == "hit_verified" for row in datasets),
        "cache_misses": sum(row["cache_status"] != "hit_verified" for row in datasets),
        "cache_miss_reasons": dict(sorted(cache_miss_reasons.items())),
        "snapshots": sorted(snapshots, key=lambda row: row["instrument_id"]),
    }
    SNAPSHOT_MANIFEST.write_text(
        json.dumps(snapshot_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    evaluation = evaluate_external_type_i_replication(
        all_records,
        prereg,
        successful_symbols=len(datasets),
        requested_symbols=len(instruments),
    )
    evaluation.update(
        {
            "authorization_id": authorization.get("authorization_id"),
            "frozen_preregistration_commit": authorization.get(
                "frozen_preregistration_commit"
            ),
            "snapshot_cutoff": manifest.get("snapshot_cutoff"),
            "successful_datasets": datasets,
            "failed_symbols": failed_symbols,
            "snapshot_manifest": str(SNAPSHOT_MANIFEST.relative_to(ROOT)),
            "operational_policy": {
                "provider_order": [provider.name for provider in providers],
                "retries_per_provider": 2,
                "provider_failover": True,
                "outcome_dependent_refetch": False,
                "same_replication_set_retuning": False,
            },
        }
    )
    OUTPUT.write_text(
        json.dumps(evaluation, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    primary = evaluation["primary_contrast"]
    exposure = primary["exposure"]
    comparator = primary["comparator"]
    interval = primary.get("newcombe_95_ci") or {}
    print(
        "[HT-CN M2 EXT-REPL] coverage="
        f"{evaluation['successful_symbols']}/{evaluation['requested_symbols']} "
        f"minimum={evaluation['minimum_successful_symbols']} ok={evaluation['coverage_ok']}"
    )
    print(
        "[HT-CN M2 EXT-REPL] primary "
        f"{primary['exposure_name']}: n={exposure['records']}, hits={exposure['endpoint_hits']}, "
        f"rate={exposure['endpoint_rate']}; {primary['comparator_name']}: "
        f"n={comparator['records']}, hits={comparator['endpoint_hits']}, "
        f"rate={comparator['endpoint_rate']}"
    )
    print(
        "[HT-CN M2 EXT-REPL] effect="
        f"{primary['absolute_rate_difference']}, "
        f"CI95=[{interval.get('lower')}, {interval.get('upper')}], "
        f"result={primary['result']}"
    )
    print(
        "[HT-CN M2 EXT-REPL] one primary test only; descriptive subgroups cannot replace it."
    )
    print(f"[HT-CN M2 EXT-REPL] report={OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
