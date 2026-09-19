from __future__ import annotations

import os
from pathlib import Path

from htcn.app.operator_input_identity import (
    ANALYSIS_CODE_IDENTITY_CONTRACT_VERSION,
    DATA_INPUT_IDENTITY_CONTRACT_VERSION,
    OPERATOR_INPUT_IDENTITY_CONTRACT_VERSION,
    AnalysisCodeIdentity,
    DataInputIdentity,
    OperatorCacheInputIdentity,
    build_analysis_code_identity,
    build_data_input_identity,
)


def _write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def test_data_input_identity_changes_when_finalized_market_input_changes(
    tmp_path,
) -> None:
    _write(tmp_path / "catalog.duckdb", b"catalog-v1")
    _write(tmp_path / "daily" / "SSE.1.parquet", b"daily-v1")
    _write(tmp_path / "adjustment" / "qfq" / "SSE.1.parquet", b"factor-v1")
    _write(tmp_path / "benchmarks" / "star50.parquet", b"benchmark-v1")

    first = build_data_input_identity(tmp_path)
    _write(tmp_path / "daily" / "SSE.1.parquet", b"daily-v2-longer")
    second = build_data_input_identity(tmp_path)

    assert first.contract_version == DATA_INPUT_IDENTITY_CONTRACT_VERSION
    assert first.fingerprint != second.fingerprint
    assert first.manifest_mode == "relative_path_size_mtime_ns"


def test_data_input_identity_detects_same_size_mtime_change(
    tmp_path,
) -> None:
    path = tmp_path / "daily" / "SSE.1.parquet"
    _write(path, b"1234")
    first = build_data_input_identity(tmp_path)
    stat = path.stat()
    os.utime(
        path,
        ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000),
    )
    second = build_data_input_identity(tmp_path)

    assert first.fingerprint != second.fingerprint


def test_data_input_identity_ignores_product_cache_outputs(
    tmp_path,
) -> None:
    _write(tmp_path / "daily" / "SSE.1.parquet", b"daily")
    first = build_data_input_identity(tmp_path)
    _write(
        tmp_path / "product" / "m5" / "operator_queue" / "cache.json",
        b"cache",
    )
    second = build_data_input_identity(tmp_path)

    assert first.fingerprint == second.fingerprint


def test_data_input_identity_tracks_missing_optional_inputs_as_state(
    tmp_path,
) -> None:
    first = build_data_input_identity(tmp_path)
    _write(tmp_path / "benchmarks" / "star50.parquet", b"benchmark")
    second = build_data_input_identity(tmp_path)

    assert first.fingerprint != second.fingerprint


def test_analysis_code_identity_changes_only_for_selected_code(
    tmp_path,
) -> None:
    code = tmp_path / "src" / "feature.py"
    docs = tmp_path / "README.md"
    _write(code, b"value = 1\n")
    _write(docs, b"docs-v1\n")

    first = build_analysis_code_identity(
        project_root=tmp_path,
        relative_paths=("src/feature.py",),
    )
    _write(docs, b"docs-v2\n")
    docs_changed = build_analysis_code_identity(
        project_root=tmp_path,
        relative_paths=("src/feature.py",),
    )
    _write(code, b"value = 2\n")
    code_changed = build_analysis_code_identity(
        project_root=tmp_path,
        relative_paths=("src/feature.py",),
    )

    assert first.contract_version == ANALYSIS_CODE_IDENTITY_CONTRACT_VERSION
    assert first.fingerprint == docs_changed.fingerprint
    assert first.fingerprint != code_changed.fingerprint


def test_analysis_code_identity_fails_closed_on_missing_component(
    tmp_path,
) -> None:
    try:
        build_analysis_code_identity(
            project_root=tmp_path,
            relative_paths=("src/missing.py",),
        )
    except FileNotFoundError as exc:
        assert "src/missing.py" in str(exc)
    else:
        raise AssertionError("missing analysis-code component must fail closed")


def test_operator_input_identity_payload_is_explicitly_non_authoritative() -> None:
    data = DataInputIdentity(
        DATA_INPUT_IDENTITY_CONTRACT_VERSION,
        "data-fingerprint",
        10,
    )
    code = AnalysisCodeIdentity(
        ANALYSIS_CODE_IDENTITY_CONTRACT_VERSION,
        "code-fingerprint",
        20,
    )
    identity = OperatorCacheInputIdentity(
        OPERATOR_INPUT_IDENTITY_CONTRACT_VERSION,
        "combined-fingerprint",
        data,
        code,
    )

    payload = identity.as_payload()

    assert payload["authoritative_evidence"] is False
    assert payload["writes_m4_evidence"] is False
    assert payload["methodology_identity"] is False
