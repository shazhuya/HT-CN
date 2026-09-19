from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import duckdb

from htcn.app.harmonic_service import LocalHarmonicService

UNIVERSE_COVERAGE_SCHEMA_VERSION = 1
UNIVERSE_COVERAGE_CONTRACT_VERSION = 1
DEFAULT_EXCHANGES = ("SSE", "SZSE")
FORMAL_QFQ_MODES = {"qfq", "qfq_carry_forward"}


@dataclass(frozen=True, slots=True)
class UniverseCoverageContract:
    version: int = UNIVERSE_COVERAGE_CONTRACT_VERSION
    listed_source: str = "security_master.status=listed"
    initialized_source: str = "listed_with_valid_local_daily_dataset"
    formal_qfq_source: str = "initialized_with_qfq_or_qfq_carry_forward"
    scanner_universe: str = "initialized_default_scope"
    research_scanner_universe: str = "formal_qfq_ready_subset"
    operator_universe: str = "exact_product_scanner_universe"
    candidate_set: str = "downstream_harmonic_matches_not_coverage_denominator"
    presentation_defines_universe: bool = False
    bse_default_scope: str = "deferred"
    coverage_gap_is_product_failure: bool = False
    authoritative_evidence: bool = False
    writes_m4_evidence: bool = False
    mutates_harmonic_identity: bool = False
    is_trade_instruction: bool = False

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


def universe_hash(values: Iterable[str]) -> str:
    ids = sorted({str(value) for value in values if str(value)})
    material = json.dumps(
        ids,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(material.encode("utf-8")).hexdigest()


def _exchange(instrument_id: str) -> str:
    return str(instrument_id).split(".", 1)[0].upper()


def _default_scope(
    values: Iterable[str],
    *,
    exchanges: tuple[str, ...] = DEFAULT_EXCHANGES,
) -> list[str]:
    allowed = {str(value).upper() for value in exchanges}
    return sorted({
        str(value)
        for value in values
        if str(value) and _exchange(str(value)) in allowed
    })


def _layer(ids: Iterable[str]) -> dict[str, Any]:
    values = sorted({str(value) for value in ids if str(value)})
    return {
        "count": len(values),
        "hash": universe_hash(values),
        "instrument_ids": values,
    }


def build_universe_coverage(
    *,
    listed_ids: Iterable[str],
    initialized_ids: Iterable[str],
    qfq_ready_ids: Iterable[str] = (),
    operator_ids: Iterable[str] | None = None,
    candidate_count: int | None = None,
    qfq_evaluated: bool = True,
    exchanges: tuple[str, ...] = DEFAULT_EXCHANGES,
    excluded_local_ids: Iterable[str] = (),
    initialization_errors: Iterable[dict[str, Any]] = (),
    qfq_errors: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    listed_input = tuple(str(value) for value in listed_ids if str(value))
    initialized_input = tuple(
        str(value) for value in initialized_ids if str(value)
    )
    qfq_input = tuple(str(value) for value in qfq_ready_ids if str(value))
    excluded_input = tuple(
        str(value) for value in excluded_local_ids if str(value)
    )
    operator_input = (
        None
        if operator_ids is None
        else tuple(str(value) for value in operator_ids if str(value))
    )

    listed = _default_scope(listed_input, exchanges=exchanges)
    listed_set = set(listed)

    initialized_scope = _default_scope(initialized_input, exchanges=exchanges)
    invalid_initialized_not_listed = sorted(set(initialized_scope) - listed_set)
    initialized = [
        value for value in initialized_scope if value in listed_set
    ]
    initialized_set = set(initialized)

    qfq_scope = _default_scope(qfq_input, exchanges=exchanges)
    invalid_qfq_not_initialized = sorted(set(qfq_scope) - initialized_set)
    qfq_ready = [
        value for value in qfq_scope if value in initialized_set
    ]
    scanner = list(initialized)
    research_scanner = list(qfq_ready) if qfq_evaluated else []

    actual_operator = (
        scanner
        if operator_input is None
        else _default_scope(operator_input, exchanges=exchanges)
    )
    operator_matches_scanner = actual_operator == scanner

    listed_not_initialized = sorted(listed_set - initialized_set)
    initialized_not_qfq = (
        sorted(initialized_set - set(qfq_ready))
        if qfq_evaluated
        else []
    )

    input_ids = {
        str(value)
        for values in (
            listed_input,
            initialized_input,
            qfq_input,
            excluded_input,
        )
        for value in values
        if str(value)
    }
    deferred_bse = sorted(
        value for value in input_ids if _exchange(value) == "BSE"
    )
    non_default_exchange = sorted(
        value
        for value in input_ids
        if _exchange(value) not in {item.upper() for item in exchanges}
        and _exchange(value) != "BSE"
    )

    gaps: dict[str, Any] = {
        "listed_not_initialized": _layer(listed_not_initialized),
        "initialized_not_formal_qfq": (
            _layer(initialized_not_qfq)
            if qfq_evaluated
            else {
                "count": None,
                "hash": None,
                "instrument_ids": [],
                "status": "not_evaluated",
            }
        ),
        "deferred_bse": _layer(deferred_bse),
        "non_default_exchange": _layer(non_default_exchange),
        "excluded_local_not_initialized": _layer(excluded_input),
        "invalid_initialized_not_listed": _layer(
            invalid_initialized_not_listed
        ),
        "invalid_formal_qfq_not_initialized": _layer(
            invalid_qfq_not_initialized
        ),
    }

    layers: dict[str, Any] = {
        "listed_universe": _layer(listed),
        "initialized_universe": _layer(initialized),
        "formal_qfq_ready_universe": (
            _layer(qfq_ready)
            if qfq_evaluated
            else {
                "count": None,
                "hash": None,
                "instrument_ids": [],
                "status": "not_evaluated",
            }
        ),
        "scanner_universe": _layer(scanner),
        "research_scanner_universe": (
            _layer(research_scanner)
            if qfq_evaluated
            else {
                "count": None,
                "hash": None,
                "instrument_ids": [],
                "status": "not_evaluated",
            }
        ),
        "operator_universe": _layer(actual_operator),
    }

    listed_count = len(listed)
    initialized_count = len(initialized)
    qfq_count = len(qfq_ready)
    coverage = {
        "initialized_over_listed": (
            initialized_count / listed_count if listed_count else None
        ),
        "formal_qfq_over_initialized": (
            qfq_count / initialized_count
            if qfq_evaluated and initialized_count
            else None
        ),
    }

    invariants = {
        "initialized_subset_of_listed": not invalid_initialized_not_listed,
        "formal_qfq_subset_of_initialized": not invalid_qfq_not_initialized,
        "scanner_equals_initialized": scanner == initialized,
        "research_scanner_equals_formal_qfq": (
            research_scanner == qfq_ready if qfq_evaluated else None
        ),
        "operator_equals_scanner": operator_matches_scanner,
        "presentation_does_not_define_universe": True,
        "candidate_set_excluded_from_coverage_denominator": (
            downstream_sets["candidate_set"]["coverage_denominator"] is False
        ),
        "bse_excluded_from_default_scope": not any(
            value.startswith("BSE.")
            for value in scanner + actual_operator
        ),
    }
    hard_invariants = [
        value
        for value in invariants.values()
        if value is not None
    ]
    status = "valid" if all(hard_invariants) else "invalid"

    downstream_sets = {
        "candidate_set": {
            "count": (
                None if candidate_count is None else int(candidate_count)
            ),
            "status": (
                "not_observed"
                if candidate_count is None
                else "observed"
            ),
            "coverage_denominator": False,
            "defines_scanner_universe": False,
            "definition": (
                "扫描后产生的谐波候选集合；不是 universe，"
                "不得用于计算 listed/initialized/scanner 覆盖率。"
            ),
        }
    }

    return {
        "schema_version": UNIVERSE_COVERAGE_SCHEMA_VERSION,
        "status": status,
        "default_exchanges": list(exchanges),
        "contract": UniverseCoverageContract().as_payload(),
        "qfq_evaluated": bool(qfq_evaluated),
        "layers": layers,
        "coverage": coverage,
        "gaps": gaps,
        "downstream_sets": downstream_sets,
        "initialization_errors": list(initialization_errors),
        "qfq_errors": list(qfq_errors),
        "invariants": invariants,
        "terminology": {
            "listed_universe": (
                "当前 security_master 中 status=listed 且属于默认交易所范围的证券。"
            ),
            "initialized_universe": (
                "listed universe 中已经建立有效本地 daily_dataset 和基础 "
                "Parquet 的证券。"
            ),
            "formal_qfq_ready_universe": (
                "initialized universe 中当前可形成 qfq 或 "
                "qfq_carry_forward 连续价格视图的证券。"
            ),
            "scanner_universe": (
                "产品日常扫描实际输入集合；默认严格等于 initialized universe。"
            ),
            "research_scanner_universe": (
                "正式研究/统计通道允许进入的扫描集合；严格等于 "
                "formal-QFQ-ready universe。"
            ),
            "operator_universe": (
                "传给 M5 Operator Queue 的精确集合；必须与产品 "
                "scanner universe 一致。"
            ),
            "candidate_set": (
                "扫描后得到的形态候选子集，不是 universe，也不得反推覆盖率。"
            ),
        },
        "coverage_claim": {
            "may_claim_full_a_share_coverage": False,
            "initialized_may_be_called_full_a_share": False,
            "scanner_may_be_called_all_listed": scanner == listed,
            "required_wording": (
                "必须报告具体 universe 层级、数量、hash 与 gap；"
                "不得把 initialized/scanner coverage 表述为全 A 股覆盖。"
            ),
        },
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "mutates_harmonic_identity": False,
        "is_trade_instruction": False,
    }


def load_catalog_universes(
    data_root: str | Path,
    *,
    exchanges: tuple[str, ...] = DEFAULT_EXCHANGES,
) -> dict[str, Any]:
    root = Path(data_root)
    catalog = root / "catalog.duckdb"
    if not catalog.is_file():
        raise FileNotFoundError(catalog)

    scope_sql = " OR ".join(
        f"instrument_id LIKE '{exchange}.%'"
        for exchange in exchanges
    )
    with duckdb.connect(str(catalog), read_only=True) as con:
        listed_rows = con.execute(
            "SELECT instrument_id FROM security_master "
            f"WHERE status='listed' AND ({scope_sql}) "
            "ORDER BY instrument_id"
        ).fetchall()
        dataset_rows = con.execute(
            "SELECT instrument_id, parquet_path, row_count, "
            "first_trade_date, last_trade_date "
            f"FROM daily_dataset WHERE ({scope_sql}) "
            "ORDER BY instrument_id"
        ).fetchall()

    listed = [str(row[0]) for row in listed_rows]
    listed_set = set(listed)
    initialized: list[str] = []
    errors: list[dict[str, Any]] = []

    for instrument_id, parquet_path, row_count, first_date, last_date in dataset_rows:
        instrument = str(instrument_id)
        if instrument not in listed_set:
            continue
        candidate = Path(str(parquet_path or ""))
        if candidate and not candidate.is_absolute():
            candidate = root.parents[1] / candidate
        valid = (
            bool(parquet_path)
            and int(row_count or 0) > 0
            and first_date is not None
            and last_date is not None
            and first_date <= last_date
            and candidate.is_file()
        )
        if valid:
            initialized.append(instrument)
        else:
            errors.append({
                "instrument_id": instrument,
                "reason": "invalid_or_missing_daily_dataset",
                "parquet_path": str(parquet_path or ""),
                "row_count": int(row_count or 0),
                "first_trade_date": (
                    None if first_date is None else str(first_date)
                ),
                "last_trade_date": (
                    None if last_date is None else str(last_date)
                ),
            })

    local_daily_ids = sorted(
        path.stem for path in (root / "daily").glob("*.parquet")
    ) if (root / "daily").is_dir() else []
    excluded_local = sorted(set(local_daily_ids) - set(initialized))

    return {
        "listed_ids": listed,
        "initialized_ids": sorted(initialized),
        "excluded_local_ids": excluded_local,
        "initialization_errors": errors,
    }


def assess_formal_qfq_ready(
    data_root: str | Path,
    instrument_ids: Iterable[str],
) -> tuple[list[str], list[dict[str, str]]]:
    service = LocalHarmonicService(data_root)
    ready: list[str] = []
    errors: list[dict[str, str]] = []

    for instrument_id in sorted({str(value) for value in instrument_ids}):
        try:
            raw = service._load_history(instrument_id)
            _frame, mode, warning, basis_id = service._continuous_view(
                instrument_id,
                raw,
            )
            if mode in FORMAL_QFQ_MODES and str(basis_id).startswith("qfq:"):
                ready.append(instrument_id)
            else:
                errors.append({
                    "instrument_id": instrument_id,
                    "mode": str(mode),
                    "basis_id": str(basis_id),
                    "reason": str(warning or "formal_qfq_not_ready"),
                })
        except Exception as exc:  # noqa: BLE001 - isolate one instrument's local QFQ probe
            errors.append({
                "instrument_id": instrument_id,
                "mode": "error",
                "basis_id": "error",
                "reason": f"{type(exc).__name__}: {exc}",
            })
    return ready, errors


def build_live_universe_coverage(
    data_root: str | Path,
    *,
    include_qfq: bool = True,
    operator_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    catalog = load_catalog_universes(data_root)
    qfq_ready: list[str] = []
    qfq_errors: list[dict[str, str]] = []
    if include_qfq:
        qfq_ready, qfq_errors = assess_formal_qfq_ready(
            data_root,
            catalog["initialized_ids"],
        )

    return build_universe_coverage(
        listed_ids=catalog["listed_ids"],
        initialized_ids=catalog["initialized_ids"],
        qfq_ready_ids=qfq_ready,
        operator_ids=operator_ids,
        qfq_evaluated=include_qfq,
        excluded_local_ids=catalog["excluded_local_ids"],
        initialization_errors=catalog["initialization_errors"],
        qfq_errors=qfq_errors,
    )
