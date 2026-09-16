from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "research" / "a-share-research-universe-v1.json"
REPLICATION = ROOT / "research" / "a-share-type-i-external-replication-universe-v1.json"
PREREG = ROOT / "research" / "m2-type-i-external-replication-prereg-v1.json"
SOURCE_RESULT = ROOT / "research" / "m2-type-i-holdout-result-v1.json"


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()


def _ids(payload: dict) -> list[str]:
    return [str(row["instrument_id"]) for row in payload.get("instruments") or []]


def main() -> int:
    original = json.loads(ORIGINAL.read_text(encoding="utf-8"))
    replication = json.loads(REPLICATION.read_text(encoding="utf-8"))
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    source_result = json.loads(SOURCE_RESULT.read_text(encoding="utf-8"))

    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    original_ids = _ids(original)
    replication_ids = _ids(replication)
    overlap = sorted(set(original_ids) & set(replication_ids))
    dataset = prereg.get("replication_dataset") or {}
    contrast = prereg.get("primary_contrast") or {}
    test = prereg.get("confirmatory_test") or {}
    multiplicity = prereg.get("multiplicity") or {}
    freeze = prereg.get("freeze") or {}

    require(len(replication_ids) == 60, "replication universe must contain exactly 60 symbols")
    require(len(set(replication_ids)) == 60, "replication universe contains duplicate symbols")
    require(not overlap, f"replication universe overlaps original 45 symbols: {overlap}")
    require(
        replication.get("dataset_id") == dataset.get("dataset_id"),
        "replication dataset_id does not match preregistration",
    )
    require(
        replication.get("snapshot_cutoff") == dataset.get("snapshot_cutoff"),
        "replication cutoff does not match preregistration",
    )
    require(
        int(replication.get("minimum_successful_symbols") or 0)
        == int(dataset.get("minimum_successful_symbols") or -1)
        == 48,
        "replication provider coverage gate must remain 48/60",
    )
    require(
        _git_blob_sha(REPLICATION) == dataset.get("manifest_git_blob_sha"),
        "replication manifest Git blob SHA differs from frozen preregistration",
    )
    require(
        source_result.get("result_id") == (prereg.get("source_result") or {}).get("result_id"),
        "source frozen result id mismatch",
    )
    require(
        (source_result.get("primary_contrast") or {}).get("result") == "confirmed",
        "source M2.22 primary result must remain confirmed",
    )
    require(
        (contrast.get("exposure") or {}).get("name") == "full_prz_exit_by_t5",
        "replication exposure threshold changed",
    )
    require(
        (contrast.get("comparator") or {}).get("name") == "no_full_exit_by_t5",
        "replication comparator changed",
    )
    require(
        int((prereg.get("endpoint") or {}).get("landmark_bar") or 0) == 5
        and int((prereg.get("endpoint") or {}).get("reaction_horizon_bars") or 0) == 20,
        "replication endpoint window changed",
    )
    require(
        int(test.get("minimum_records_per_group") or 0) == 20,
        "replication group floor must remain 20",
    )
    require(
        float(test.get("z") or 0.0) == 1.959963984540054,
        "replication Newcombe z value changed",
    )
    require(multiplicity.get("primary_tests_planned") == 1, "exactly one primary replication test is allowed")
    require(multiplicity.get("alternate_thresholds_allowed") is False, "alternate thresholds must remain disabled")
    require(multiplicity.get("alternate_endpoints_allowed") is False, "alternate endpoints must remain disabled")
    require(freeze.get("symbol_outcomes_read_before_freeze") is False, "preregistration must precede replication outcome inspection")
    require(freeze.get("original_45_symbol_holdout_reopened") is False, "original Holdout must remain consumed and closed")

    if failures:
        for failure in failures:
            print(f"[HT-CN M2 EXT-PREREG] FAIL: {failure}")
        return 2

    print(
        "[HT-CN M2 EXT-PREREG] status=external_replication_preregistered, "
        f"symbols={len(replication_ids)}, original_overlap=0, coverage_gate=48"
    )
    print(
        "[HT-CN M2 EXT-PREREG] primary=full_prz_exit_by_t5 vs no_full_exit_by_t5; "
        "endpoint=T+6..T+20 first T2 among T+5-pending-T2 events"
    )
    print(
        "[HT-CN M2 EXT-PREREG] criterion=95% Newcombe lower bound > 0; "
        "min_group=20; primary_tests=1"
    )
    print("[HT-CN M2 EXT-PREREG] PREREGISTRATION FROZEN; this verifier does not inspect replication outcomes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
