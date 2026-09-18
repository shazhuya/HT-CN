from fastapi.testclient import TestClient

from services.api.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ht-cn-api",
        "version": "0.4.0",
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



def test_operator_delta_endpoint_is_product_observation_only() -> None:
    client = TestClient(app)
    contract = {
        "predictive_score_used": False,
        "historical_outcome_used": False,
        "alpha_inference_allowed": False,
        "is_trade_instruction": False,
        "mutates_harmonic_identity": False,
        "mutates_source_raw_prz": False,
        "owns_lifecycle": False,
    }
    previous = {
        "schema_version": 2,
        "contract": contract,
        "as_of_trade_date": "2026-09-17",
        "observed_trade_dates": ["2026-09-17"],
        "observation_integrity": "single_as_of",
        "items": [],
        "errors": [],
    }
    current = {
        **previous,
        "as_of_trade_date": "2026-09-18",
        "observed_trade_dates": ["2026-09-18"],
    }

    response = client.post(
        "/api/operator/delta",
        json={"previous": previous, "current": current},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["contract"]["semantics"] == "product_observation_only"
    assert payload["contract"]["authoritative_transition"] is False
    assert payload["contract"]["writes_m4_evidence"] is False
