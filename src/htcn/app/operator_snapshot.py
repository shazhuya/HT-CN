from __future__ import annotations

from concurrent.futures import Future
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
from threading import Lock, get_ident
from typing import Any, Callable, Iterable

import duckdb

from .operator_input_identity import OperatorCacheInputIdentity
from .operator_queue import (
    AnalysisService,
    AnalysisServiceFactory,
    OperatorProgressCallback,
    build_operator_queue,
)


OPERATOR_SNAPSHOT_SCHEMA_VERSION = 1
OPERATOR_SNAPSHOT_CONTRACT_VERSION = 2

_SINGLE_FLIGHT_GUARD = Lock()
_SINGLE_FLIGHT: dict[str, Future[dict[str, Any]]] = {}


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
    input_identity: OperatorCacheInputIdentity,
    input_identity_stable_during_build: bool | None = None,
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
        "input_identity_contract_version": input_identity.contract_version,
        "input_identity_fingerprint": input_identity.fingerprint,
        "data_input_fingerprint": input_identity.data.fingerprint,
        "analysis_code_fingerprint": input_identity.analysis_code.fingerprint,
        "input_identity_stable_during_build": (
            input_identity_stable_during_build
        ),
        "single_flight_scope": "process_local_cache_identity",
        "coalesced_from_status": None,
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
    input_identity: OperatorCacheInputIdentity,
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
    stored_identity = payload.get("input_identity")
    if not isinstance(stored_identity, dict):
        raise ValueError("operator snapshot input identity missing")
    if int(stored_identity.get("contract_version") or 0) != input_identity.contract_version:
        raise ValueError("operator snapshot input-identity contract mismatch")
    if str(stored_identity.get("fingerprint") or "") != input_identity.fingerprint:
        raise ValueError("operator snapshot input identity mismatch")
    stored_data = stored_identity.get("data") or {}
    stored_code = stored_identity.get("analysis_code") or {}
    if str(stored_data.get("fingerprint") or "") != input_identity.data.fingerprint:
        raise ValueError("operator snapshot data-input identity mismatch")
    if str(stored_code.get("fingerprint") or "") != input_identity.analysis_code.fingerprint:
        raise ValueError("operator snapshot analysis-code identity mismatch")
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


def _single_flight_key(
    *,
    cache_root: Path,
    expected_trade_date: str | None,
    bars: int,
    scales: tuple[int, ...],
    universe_hash: str,
    input_identity: OperatorCacheInputIdentity,
) -> str:
    material = {
        "cache_root": str(cache_root.resolve()),
        "expected_trade_date": expected_trade_date,
        "bars": int(bars),
        "scales": list(scales),
        "universe_hash": universe_hash,
        "contract_version": OPERATOR_SNAPSHOT_CONTRACT_VERSION,
        "input_identity_contract_version": input_identity.contract_version,
        "input_identity_fingerprint": input_identity.fingerprint,
    }
    return sha256(_canonical_json(material).encode("utf-8")).hexdigest()


def _load_valid_cached_snapshot(
    *,
    cache_path: Path | None,
    expected_trade_date: str | None,
    bars: int,
    scales: tuple[int, ...],
    universe_hash: str,
    input_identity: OperatorCacheInputIdentity,
) -> tuple[dict[str, Any], str] | None:
    if (
        cache_path is None
        or expected_trade_date is None
        or not cache_path.is_file()
    ):
        return None
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
            input_identity=input_identity,
            input_identity_stable_during_build=input_identity_unchanged,
        )
        return queue, str(stored.get("generated_at_utc") or "")
    except Exception:
        return None


def _mark_coalesced_wait(
    payload: dict[str, Any],
) -> dict[str, Any]:
    out = deepcopy(payload)
    cache = dict(out.get("product_cache") or {})
    original_status = str(cache.get("status") or "unknown")
    cache["status"] = "coalesced_wait"
    cache["coalesced_from_status"] = original_status
    cache["single_flight_scope"] = "process_local_cache_identity"
    out["product_cache"] = cache
    return out


def _write_snapshot_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(
        f".{path.name}.{os.getpid()}.{get_ident()}.tmp"
    )
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
    input_identity: OperatorCacheInputIdentity,
    input_identity_factory: (
        Callable[[], OperatorCacheInputIdentity] | None
    ) = None,
    bars: int = 420,
    scales: tuple[int, ...] = (3, 5, 8, 13),
    force_refresh: bool = False,
    max_workers: int = 1,
    service_factory: AnalysisServiceFactory | None = None,
    progress_callback: OperatorProgressCallback | None = None,
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

    if not force_refresh:
        cached = _load_valid_cached_snapshot(
            cache_path=cache_path,
            expected_trade_date=expected_trade_date,
            bars=bars,
            scales=scales,
            universe_hash=universe_hash,
            input_identity=input_identity,
        )
        if cached is not None:
            queue, generated_at = cached
            return _attach_cache_metadata(
                queue,
                status="hit",
                expected_trade_date=expected_trade_date,
                cache_path=cache_path,
                generated_at_utc=generated_at,
                input_identity=input_identity,
                input_identity_stable_during_build=True,
            )

    flight_key = _single_flight_key(
        cache_root=cache_dir,
        expected_trade_date=expected_trade_date,
        bars=bars,
        scales=scales,
        universe_hash=universe_hash,
        input_identity=input_identity,
    )
    with _SINGLE_FLIGHT_GUARD:
        existing = _SINGLE_FLIGHT.get(flight_key)
        if existing is None:
            future: Future[dict[str, Any]] = Future()
            _SINGLE_FLIGHT[flight_key] = future
            owner = True
        else:
            future = existing
            owner = False

    if not owner:
        return _mark_coalesced_wait(future.result())

    try:
        # Re-check after becoming owner. Another process or a just-finished
        # local request may have populated a valid cache between the fast-path
        # check and single-flight ownership.
        if not force_refresh:
            cached = _load_valid_cached_snapshot(
                cache_path=cache_path,
                expected_trade_date=expected_trade_date,
                bars=bars,
                scales=scales,
                universe_hash=universe_hash,
                input_identity=input_identity,
            )
            if cached is not None:
                queue, generated_at = cached
                result = _attach_cache_metadata(
                    queue,
                    status="hit_after_race",
                    expected_trade_date=expected_trade_date,
                    cache_path=cache_path,
                    generated_at_utc=generated_at,
                    input_identity=input_identity,
                    input_identity_stable_during_build=True,
                )
                future.set_result(deepcopy(result))
                return result

        queue = build_operator_queue(
            service,
            instruments,
            bars=bars,
            scales=scales,
            include_evidence_insufficient=True,
            max_workers=max_workers,
            service_factory=service_factory,
            progress_callback=progress_callback,
        )
        generated_at = datetime.now(timezone.utc).isoformat()

        if cache_path is None and queue.get("as_of_trade_date"):
            cache_path = cache_dir / _cache_filename(
                expected_trade_date=str(queue["as_of_trade_date"]),
                bars=bars,
                scales=scales,
            )

        final_input_identity = (
            input_identity_factory()
            if input_identity_factory is not None
            else input_identity
        )
        input_identity_unchanged = (
            final_input_identity.fingerprint
            == input_identity.fingerprint
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
            and input_identity_unchanged
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
                "input_identity": input_identity.as_payload(),
                "queue": queue,
                "authoritative_evidence": False,
                "writes_m4_evidence": False,
            }
            _write_snapshot_atomic(cache_path, stored_payload)
            status = "rebuilt_force" if force_refresh else "rebuilt"
        else:
            status = (
                "live_not_cached"
                if input_identity_unchanged
                else "live_not_cached_input_changed"
            )

        result = _attach_cache_metadata(
            queue,
            status=status,
            expected_trade_date=expected_trade_date,
            cache_path=cache_path if can_cache else None,
            generated_at_utc=generated_at,
            input_identity=input_identity,
        )
        future.set_result(deepcopy(result))
        return result
    except BaseException as exc:
        future.set_exception(exc)
        raise
    finally:
        with _SINGLE_FLIGHT_GUARD:
            if _SINGLE_FLIGHT.get(flight_key) is future:
                _SINGLE_FLIGHT.pop(flight_key, None)

