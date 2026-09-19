from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from htcn.data.validation import normalize_daily

SNAPSHOT_META_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class CachedResearchSnapshot:
    frame: pd.DataFrame
    source: str
    sha256: str
    cache_status: str
    metadata: dict[str, Any]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_paths(data_dir: Path, instrument_id: str) -> tuple[Path, Path]:
    return data_dir / f"{instrument_id}.parquet", data_dir / f"{instrument_id}.snapshot.json"


def _iso(value: date | str) -> str:
    return value.isoformat() if isinstance(value, date) else str(value)


def write_research_snapshot(
    data_dir: Path,
    *,
    instrument_id: str,
    frame: pd.DataFrame,
    source: str,
    requested_start: date | str,
    requested_end: date | str,
    max_bars: int,
    price_mode: str = "qfq",
) -> CachedResearchSnapshot:
    if max_bars < 1:
        raise ValueError("max_bars must be >= 1")
    normalized = normalize_daily(frame).tail(max_bars).reset_index(drop=True)
    if normalized.empty:
        raise ValueError("cannot snapshot an empty frame")
    ids = set(str(value) for value in normalized["instrument_id"].unique())
    if ids != {instrument_id}:
        raise ValueError(f"snapshot instrument mismatch: expected {instrument_id}, got {sorted(ids)}")

    data_dir.mkdir(parents=True, exist_ok=True)
    parquet_path, meta_path = snapshot_paths(data_dir, instrument_id)
    normalized.to_parquet(parquet_path, index=False)
    digest = _sha256(parquet_path)
    metadata: dict[str, Any] = {
        "schema_version": SNAPSHOT_META_SCHEMA_VERSION,
        "instrument_id": instrument_id,
        "price_mode": price_mode,
        "source": str(source),
        "requested_start": _iso(requested_start),
        "snapshot_cutoff": _iso(requested_end),
        "max_bars": int(max_bars),
        "bars": len(normalized),
        "first_trade_date": pd.Timestamp(normalized.iloc[0]["trade_date"]).date().isoformat(),
        "last_trade_date": pd.Timestamp(normalized.iloc[-1]["trade_date"]).date().isoformat(),
        "parquet_sha256": digest,
    }
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return CachedResearchSnapshot(
        frame=normalized,
        source=str(source),
        sha256=digest,
        cache_status="miss_fetched",
        metadata=metadata,
    )


def load_research_snapshot(
    data_dir: Path,
    *,
    instrument_id: str,
    requested_start: date | str,
    requested_end: date | str,
    max_bars: int,
    price_mode: str = "qfq",
) -> tuple[CachedResearchSnapshot | None, str]:
    """Load a byte-verified pinned research snapshot or return a deterministic miss reason.

    A restored GitHub Actions cache may come from an older research-manifest key. Sidecar
    metadata therefore validates cutoff, requested range, price mode and capacity before any
    cached data is trusted. Provider restatements cannot silently alter an accepted cache hit.
    """
    if max_bars < 1:
        raise ValueError("max_bars must be >= 1")
    parquet_path, meta_path = snapshot_paths(data_dir, instrument_id)
    if not parquet_path.exists() or not meta_path.exists():
        return None, "missing_snapshot_or_metadata"

    try:
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return None, "invalid_metadata_json"

    expected_start = _iso(requested_start)
    expected_end = _iso(requested_end)
    checks = {
        "schema_version": metadata.get("schema_version") == SNAPSHOT_META_SCHEMA_VERSION,
        "instrument_id": metadata.get("instrument_id") == instrument_id,
        "price_mode": metadata.get("price_mode") == price_mode,
        "snapshot_cutoff": metadata.get("snapshot_cutoff") == expected_end,
        "start_coverage": str(metadata.get("requested_start", "9999-12-31")) <= expected_start,
        "bar_capacity": int(metadata.get("max_bars", 0)) >= max_bars,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        return None, "metadata_mismatch:" + ",".join(failed)

    expected_digest = str(metadata.get("parquet_sha256") or "")
    if not expected_digest:
        return None, "metadata_missing_sha256"
    actual_digest = _sha256(parquet_path)
    if actual_digest != expected_digest:
        return None, "sha256_mismatch"

    try:
        frame = normalize_daily(pd.read_parquet(parquet_path))
    except Exception:
        return None, "invalid_cached_parquet"
    if frame.empty:
        return None, "empty_cached_parquet"
    ids = set(str(value) for value in frame["instrument_id"].unique())
    if ids != {instrument_id}:
        return None, "cached_instrument_mismatch"

    dates = pd.to_datetime(frame["trade_date"])
    start_ts = pd.Timestamp(expected_start)
    end_ts = pd.Timestamp(expected_end)
    frame = frame[(dates >= start_ts) & (dates <= end_ts)].tail(max_bars).reset_index(drop=True)
    if frame.empty:
        return None, "cached_range_empty"

    return (
        CachedResearchSnapshot(
            frame=frame,
            source=str(metadata.get("source") or "unknown_qfq"),
            sha256=actual_digest,
            cache_status="hit_verified",
            metadata=metadata,
        ),
        "hit_verified",
    )


def snapshot_manifest_entry(snapshot: CachedResearchSnapshot) -> dict[str, Any]:
    frame = snapshot.frame
    return {
        "instrument_id": snapshot.metadata["instrument_id"],
        "source": snapshot.source,
        "cache_status": snapshot.cache_status,
        "bars": len(frame),
        "first_trade_date": pd.Timestamp(frame.iloc[0]["trade_date"]).date().isoformat(),
        "last_trade_date": pd.Timestamp(frame.iloc[-1]["trade_date"]).date().isoformat(),
        "sha256": snapshot.sha256,
        "snapshot_cutoff": snapshot.metadata["snapshot_cutoff"],
        "price_mode": snapshot.metadata["price_mode"],
    }
