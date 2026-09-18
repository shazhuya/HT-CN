from __future__ import annotations

from pathlib import Path

import scripts.m3_metadata_tradability_smoke as smoke


def test_metadata_smoke_parser_contract_is_strict_only_when_requested() -> None:
    # The standalone diagnostic keeps its migration-friendly status vocabulary.
    # Formal M3 acceptance adds --require-parquet in qa_local.py.
    source = Path(smoke.__file__).read_text(encoding="utf-8")
    assert "--require-parquet" in source
    assert "strict_real_m1_parquet_required" in source
