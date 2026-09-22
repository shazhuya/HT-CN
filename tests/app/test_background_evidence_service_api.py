from __future__ import annotations

from fastapi.testclient import TestClient

import services.api.main as api_main
from htcn.app.background_evidence_service import (
    write_background_evidence_service_status,
)
from services.api.main import app


def test_background_evidence_status_is_explicit_before_first_run(
    monkeypatch,
    tmp_path,
) -> None:
    status_path = tmp_path / "m9-background-evidence-service.json"
    monkeypatch.setattr(
        api_main,
        "BACKGROUND_EVIDENCE_SERVICE_STATUS_PATH",
        status_path,
    )

    response = TestClient(app).get("/api/evidence/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "not_started"
    assert payload["evidence_insufficient"] is True
    assert payload["calibration_state"] == "disabled_insufficient_evidence"


def test_background_evidence_endpoint_distinguishes_insufficiency_from_fault(
    monkeypatch,
    tmp_path,
) -> None:
    status_path = tmp_path / "m9-background-evidence-service.json"
    write_background_evidence_service_status(
        status_path,
        {
            "schema_version": 1,
            "service": "m9_background_evidence_service",
            "status": "healthy",
            "healthy": True,
            "operational_state": "healthy",
            "operational_fault": False,
            "evidence_state": "insufficient_evidence",
            "evidence_insufficient": True,
            "calibration_state": "disabled_insufficient_evidence",
            "latest_committed_capture_date": "2026-09-22",
            "prospective_candidate_count": 14,
            "outcome_snapshot_count": 2,
            "diagnostics_zh": [
                "产品运行正常，但前瞻样本仍不足；M8 保持禁用。"
            ],
        },
    )
    monkeypatch.setattr(
        api_main,
        "BACKGROUND_EVIDENCE_SERVICE_STATUS_PATH",
        status_path,
    )

    payload = TestClient(app).get("/api/evidence/status").json()

    assert payload["healthy"] is True
    assert payload["operational_fault"] is False
    assert payload["evidence_insufficient"] is True
    assert payload["prospective_candidate_count"] == 14
    assert payload["outcome_snapshot_count"] == 2
