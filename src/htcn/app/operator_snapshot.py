from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Iterable

import duckdb

from .operator_queue import AnalysisService, build_operator_queue


OPERATOR_SNAPSHOT_SCHEMA_VERSION = 1
OPERATOR_SNAPSHOT_CONTRACT_VERSION = 1


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def operator_universe_hash(instrument_ids: Iterable[str]) -> str:
    values = sorted({str(value) for value in instrument_ids})
    return sha256(_canonical_json(values).encode("utf-8")).hexdigest()


def latest_local_trade_date(catalog_path: str | Path) -> str | None:
    path = Path(catalog_path)
    if not path.is_file():
        return None
    with duckdb.connect(str(path), read_only=True) as con:
        row = con.execute(
            "SELECT MAX(trade_date) FROM trade_calendar"
        ).fetchone()
    if row is None or row[0] is None:
        return None
    return str(row[0])


def _cache_filename(
    *,
    expected_trade_date: str,
    bars: int,
    scales: tuple[int, ...],
) -> str:
    scale_text = "-".join(str(value) for value in scales)
    return (
        f"{expected_trade_date}__b{int(bars)}__s{scale_text}.json"
    )


def _attach_cache_metadata(
    queue: dict[str, Any],
    *,
    status: str,
    expected_trade_date: str | None,
    cache_path: Path | None,
    generated_at_utc: str | None,
) -> dict[str, Any]:
    payload = deepcopy(queue)
    as_of = payload.get("as_of_trade_date")
    if expected_trade_date is None or as_of is None:
        freshness = "unresolved"
    elif str(as_of) == str(expected_trade_date):
        freshness = "current"
    else:
        freshness = "stale"
    payload["product_cache"] = {
        "schema_version": OPERATOR_SNAPSHOT_SCHEMA_VERSION,
        "contract_version": OPERATOR_SNAPSHOT_CONTRACT_VERSION,
        "status": status,
        "expected_local_trade_date": expected_trade_date,
        "queue_as_of_trade_date": as_of,
        "freshness": freshness,
        "cache_path": None if cache_path is None else str(cache_path),
        "generated_at_utc": generated_at_utc,
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
    }
    return payload


def _validate_cached_snapshot(
    payload: dict[str, Any],
    *,
    expected_trade_date: str,
    bars: int,
    scales: tuple[int, ...],
    universe_hash: str,
) -> dict[str, Any]:
    if int(payload.get("schema_version") or 0) != OPERATOR_SNAPSHOT_SCHEMA_VERSION:
        raise ValueError("operator snapshot schema mismatch")
    if int(payload.get("contract_version") or 0) != OPERATOR_SNAPSHOT_CONTRACT_VERSION:
        raise ValueError("operator snapshot contract mismatch")
    if str(payload.get("expected_trade_date") or "") != expected_trade_date:
        raise ValueError("operator snapshot trade-date mismatch")
    if int(payload.get("bars") or 0) != int(bars):
        raise ValueError("operator snapshot bars mismatch")
    if tuple(int(value) for value in payload.get("scales") or []) != tuple(scales):
        raise ValueError("operator snapshot scales mismatch")
    if str(payload.get("universe_hash") or "") != universe_hash:
        raise ValueError("operator snapshot universe mismatch")
    queue = payload.get("queue")
    if not isinstance(queue, dict):
        raise ValueError("operator snapshot missing queue")
    contract = queue.get("contract") or {}
    for field in (
        "predictive_score_used",
        "historical_outcome_used",
        "alpha_inference_allowed",
        "is_trade_instruction",
        "mutates_harmonic_identity",
        "mutates_source_raw_prz",
        "owns_lifecycle",
    ):
        if contract.get(field) is not False:
            raise ValueError(
                f"operator snapshot queue boundary violation: {field}"
            )
    return queue


def _write_snapshot_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    encoded = (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    )
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def build_or_load_operator_snapshot(
    service: AnalysisService,
    instrument_ids: Iterable[str],
    *,
    cache_root: str | Path,
    expected_trade_date: str | None,
    bars: int = 420,
    scales: tuple[int, ...] = (3, 5, 8, 13),
    force_refresh: bool = False,
) -> dict[str, Any]:
    instruments = [str(value) for value in instrument_ids]
    universe_hash = operator_universe_hash(instruments)
    cache_dir = Path(cache_root)

    cache_path: Path | None = None
    if expected_trade_date:
        cache_path = cache_dir / _cache_filename(
            expected_trade_date=expected_trade_date,
            bars=bars,
            scales=scales,
        )

    if (
        not force_refresh
        and cache_path is not None
        and cache_path.is_file()
    ):
        try:
            stored = json.loads(cache_path.read_text(encoding="utf-8"))
            if not isinstance(stored, dict):
                raise ValueError("operator snapshot must be a JSON object")
            queue = _validate_cached_snapshot(
                stored,
                expected_trade_date=expected_trade_date,
                bars=bars,
                scales=scales,
                universe_hash=universe_hash,
            )
            return _attach_cache_metadata(
                queue,
                status="hit",
                expected_trade_date=expected_trade_date,
                cache_path=cache_path,
                generated_at_utc=str(stored.get("generated_at_utc") or ""),
            )
        except Exception:
            # Product cache corruption/staleness must never block live rebuild.
            pass

    queue = build_operator_queue(
        service,
        instruments,
        bars=bars,
        scales=scales,
        include_evidence_insufficient=True,
    )
    generated_at = datetime.now(timezone.utc).isoformat()

    if cache_path is None and queue.get("as_of_trade_date"):
        cache_path = cache_dir / _cache_filename(
            expected_trade_date=str(queue["as_of_trade_date"]),
            bars=bars,
            scales=scales,
        )

    queue_as_of = (
        None
        if queue.get("as_of_trade_date") is None
        else str(queue.get("as_of_trade_date"))
    )
    expected_matches = (
        expected_trade_date is None
        or queue_as_of == str(expected_trade_date)
    )
    can_cache = (
        cache_path is not None
        and queue.get("observation_integrity") == "single_as_of"
        and queue_as_of is not None
        and expected_matches
    )
    if can_cache:
        stored_payload = {
            "schema_version": OPERATOR_SNAPSHOT_SCHEMA_VERSION,
            "contract_version": OPERATOR_SNAPSHOT_CONTRACT_VERSION,
            "generated_at_utc": generated_at,
            "expected_trade_date": (
                expected_trade_date
                or str(queue.get("as_of_trade_date"))
            ),
            "bars": int(bars),
            "scales": list(scales),
            "universe_hash": universe_hash,
            "instrument_count": len(instruments),
            "queue": queue,
            "authoritative_evidence": False,
            "writes_m4_evidence": False,
        }
        _write_snapshot_atomic(cache_path, stored_payload)
        status = "rebuilt_force" if force_refresh else "rebuilt"
    else:
        status = "live_not_cached"

    return _attach_cache_metadata(
        queue,
        status=status,
        expected_trade_date=expected_trade_date,
        cache_path=cache_path if can_cache else None,
        generated_at_utc=generated_at,
    )


def evaluate_operator_snapshot_readiness(
    payload: dict[str, Any],
) -> tuple[bool, tuple[str, ...]]:
    """Return whether a daily product snapshot is complete enough for handoff."""
    reasons: list[str] = []
    if payload.get("observation_integrity") != "single_as_of":
        reasons.append("observation_integrity_not_single_as_of")
    instrument_count = int(payload.get("instrument_count") or 0)
    analyzed_count = int(payload.get("analyzed_instrument_count") or 0)
    failed_count = int(payload.get("failed_instrument_count") or 0)
    if failed_count != 0:
        reasons.append(f"instrument_failures:{failed_count}")
    if analyzed_count != instrument_count:
        reasons.append(
            f"analysis_coverage_incomplete:{analyzed_count}/{instrument_count}"
        )
    cache = payload.get("product_cache") or {}
    if cache.get("freshness") != "current":
        reasons.append(
            f"cache_freshness:{cache.get('freshness') or 'missing'}"
        )
    if not payload.get("as_of_trade_date"):
        reasons.append("as_of_trade_date_missing")
    return (not reasons, tuple(reasons))

