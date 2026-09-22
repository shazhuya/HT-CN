from fastapi.testclient import TestClient

from htcn.version import HTCN_VERSION
from services.api.main import app


def test_api_health_uses_stable_product_version() -> None:
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json()["version"] == HTCN_VERSION == "1.0.0"
    assert app.version == HTCN_VERSION
