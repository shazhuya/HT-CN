from fastapi.testclient import TestClient

from services.api.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ht-cn-api",
        "version": "0.2.0",
    }


def test_harmonic_rules_expose_executable_and_blocked_identities() -> None:
    client = TestClient(app)
    response = client.get("/api/harmonic/rules")
    assert response.status_code == 200
    rows = {item["pattern_id"]: item for item in response.json()["items"]}
    assert rows["gartley"]["executable_identity"] is True
    assert rows["shark"]["executable_identity"] is False
    assert rows["five_zero"]["source_conflict"] is True


def test_missing_local_dataset_returns_404() -> None:
    client = TestClient(app)
    response = client.get("/api/harmonic/SSE.999999")
    assert response.status_code == 404
