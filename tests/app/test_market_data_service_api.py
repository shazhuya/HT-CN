from __future__ import annotations

from fastapi.testclient import TestClient

import services.api.main as api_main
from htcn.app.market_data_service import write_market_data_service_status
from services.api.main import app


def test_market_data_status_endpoint_is_explicit_before_first_service_run(
    monkeypatch,
    tmp_path,
) -> None:
    status_path = tmp_path / "m9-market-data-service.json"
    monkeypatch.setattr(api_main, "MARKET_DATA_SERVICE_STATUS_PATH", status_path)

    response = TestClient(app).get("/api/market-data/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "not_started"
    assert payload["healthy"] is False
    assert "尚未产生运行状态" in payload["diagnostics_zh"][0]


def test_market_data_status_endpoint_exposes_persisted_chinese_diagnostics(
    monkeypatch,
    tmp_path,
) -> None:
    status_path = tmp_path / "m9-market-data-service.json"
    write_market_data_service_status(
        status_path,
        {
            "schema_version": 1,
            "service": "m9_market_data_service",
            "status": "degraded",
            "healthy": False,
            "diagnostics_zh": ["前复权服务异常，原始行情已更新。"],
        },
    )
    monkeypatch.setattr(api_main, "MARKET_DATA_SERVICE_STATUS_PATH", status_path)

    response = TestClient(app).get("/api/market-data/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["diagnostics_zh"] == ["前复权服务异常，原始行情已更新。"]
