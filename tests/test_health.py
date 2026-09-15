from fastapi.testclient import TestClient

from services.api.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ht-cn-api",
        "version": "0.1.0",
    }
