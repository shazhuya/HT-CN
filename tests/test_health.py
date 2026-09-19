from fastapi.testclient import TestClient

import services.api.main as api_main
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



def test_operator_queue_legacy_limit_cannot_shrink_scan_universe(
    monkeypatch,
) -> None:
    seen: dict[str, object] = {}

    def fake_discover(data_root, *, limit: int = 0):
        seen["discover_limit"] = limit
        return ["SSE.1", "SSE.2", "SZSE.3"]

    def fake_snapshot(service, instrument_ids, **kwargs):
        seen["instrument_ids"] = list(instrument_ids)
        return {
            "schema_version": 2,
            "contract": {
                "predictive_score_used": False,
                "historical_outcome_used": False,
                "alpha_inference_allowed": False,
                "is_trade_instruction": False,
                "mutates_harmonic_identity": False,
                "mutates_source_raw_prz": False,
                "owns_lifecycle": False,
            },
            "as_of_trade_date": "2026-09-18",
            "observed_trade_dates": ["2026-09-18"],
            "observation_integrity": "single_as_of",
            "instrument_count": 3,
            "analyzed_instrument_count": 3,
            "failed_instrument_count": 0,
            "candidate_count": 0,
            "candidate_instrument_count": 0,
            "action_state_counts": {},
            "lifecycle_state_counts": {},
            "items": [],
            "errors": [],
        }

    monkeypatch.setattr(
        api_main,
        "discover_local_instruments",
        fake_discover,
    )
    monkeypatch.setattr(
        api_main,
        "latest_local_trade_date",
        lambda path: "2026-09-18",
    )
    monkeypatch.setattr(
        api_main,
        "build_or_load_operator_snapshot",
        fake_snapshot,
    )

    client = TestClient(app)
    response = client.get("/api/operator/queue?limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert seen["discover_limit"] == 0
    assert seen["instrument_ids"] == [
        "SSE.1",
        "SSE.2",
        "SZSE.3",
    ]
    assert payload["operator_index"]["universe_scope"] == (
        "all_initialized_local_instruments"
    )
    assert payload["operator_index"]["universe_instrument_count"] == 3
    assert payload["operator_index"]["legacy_limit_ignored"] == 1
    assert payload["operator_index"][
        "presentation_does_not_define_universe"
    ] is True
