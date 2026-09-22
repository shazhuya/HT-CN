from __future__ import annotations

from fastapi.testclient import TestClient

import services.api.main as api_main
from htcn.app.harmonic_analysis_runtime import (
    write_harmonic_analysis_runtime_status,
)
from services.api.main import app


def test_harmonic_runtime_status_endpoint_is_explicit_before_first_run(
    monkeypatch,
    tmp_path,
) -> None:
    status_path = tmp_path / "m9-harmonic-analysis-runtime.json"
    monkeypatch.setattr(
        api_main,
        "HARMONIC_ANALYSIS_RUNTIME_STATUS_PATH",
        status_path,
    )

    response = TestClient(app).get("/api/harmonic/runtime/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "not_started"
    assert payload["healthy"] is False
    assert "尚未产生运行状态" in payload["diagnostics_zh"][0]


def test_harmonic_runtime_status_endpoint_exposes_provenance_and_chinese_diagnostics(
    monkeypatch,
    tmp_path,
) -> None:
    status_path = tmp_path / "m9-harmonic-analysis-runtime.json"
    write_harmonic_analysis_runtime_status(
        status_path,
        {
            "schema_version": 1,
            "service": "m9_harmonic_analysis_runtime",
            "status": "healthy",
            "healthy": True,
            "diagnostics_zh": ["自动谐波分析运行时正常。"],
            "cycle": {
                "provenance": {
                    "viewport_inputs_used": False,
                    "runtime_mutates_harmonic_identity": False,
                    "writes_m4_evidence": False,
                }
            },
        },
    )
    monkeypatch.setattr(
        api_main,
        "HARMONIC_ANALYSIS_RUNTIME_STATUS_PATH",
        status_path,
    )

    response = TestClient(app).get("/api/harmonic/runtime/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["diagnostics_zh"] == ["自动谐波分析运行时正常。"]
    assert payload["cycle"]["provenance"]["viewport_inputs_used"] is False
    assert (
        payload["cycle"]["provenance"]["runtime_mutates_harmonic_identity"]
        is False
    )
