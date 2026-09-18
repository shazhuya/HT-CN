from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

import services.api.main as api


def test_operator_history_api_passes_product_query_filters(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def fake_query(**kwargs):
        captured.update(kwargs)
        return {
            "schema_version": 1,
            "observation_count": 0,
            "observations": [],
            "authoritative_evidence": False,
            "writes_m4_evidence": False,
        }

    monkeypatch.setattr(api, "query_operator_history", fake_query)
    monkeypatch.setattr(api, "OPERATOR_HISTORY_ROOT", tmp_path)

    payload = api.operator_history(
        instrument_id="SSE.688256",
        display_key=None,
        start_trade_date="2026-09-01",
        end_trade_date="2026-09-18",
        all_revisions=True,
        summary_only=False,
        limit=25,
    )

    assert payload["observation_count"] == 0
    assert captured["history_root"] == tmp_path
    assert captured["instrument_id"] == "SSE.688256"
    assert captured["start_trade_date"] == "2026-09-01"
    assert captured["end_trade_date"] == "2026-09-18"
    assert captured["latest_revision_per_day"] is False
    assert captured["summary_only"] is False
    assert captured["limit"] == 25


def test_operator_history_api_surfaces_integrity_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_query(**_kwargs):
        raise RuntimeError("operator_history_integrity_failure:tampered")

    monkeypatch.setattr(api, "query_operator_history", fail_query)

    with pytest.raises(HTTPException) as raised:
        api.operator_history(
            instrument_id=None,
            display_key=None,
            start_trade_date=None,
            end_trade_date=None,
            all_revisions=False,
            summary_only=True,
            limit=20,
        )

    assert raised.value.status_code == 500
    assert "integrity error" in str(raised.value.detail)
