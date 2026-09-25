from fastapi.testclient import TestClient

from services.api import main


def test_harmonic_api_preserves_discovery_as_separate_non_authoritative_channel(
    monkeypatch,
) -> None:
    discovery = {
        "pattern_id": "gartley",
        "schema": "XABCD",
        "direction": "bullish",
        "state": "forming",
        "channel": "discovery",
        "discovery_only": True,
        "scale": 10,
        "geometry_score": 82.0,
        "points": [
            {"label": "X", "index": 0, "price": 100.0},
            {"label": "A", "index": 10, "price": 120.0},
            {"label": "B", "index": 20, "price": 107.64},
            {"label": "C", "index": 30, "price": 116.91},
        ],
        "prz": {
            "price_low": 104.0,
            "price_high": 104.5,
            "width": 0.5,
            "components": [],
        },
        "metrics": {"b_xa": 0.618, "c_ab": 0.75},
        "discovery": {
            "authoritative_identity": False,
            "prz_status": "projected",
            "fabricates_d": False,
            "owns_lifecycle": False,
        },
    }

    class StubService:
        def analyze(self, instrument_id: str, *, bars: int, scales: tuple[int, ...]):
            return {
                "instrument_id": instrument_id,
                "price_mode": "qfq",
                "price_basis_id": "fixture",
                "warning": None,
                "bars_requested": bars,
                "bars_returned": 2,
                "first_trade_date": "2026-09-23",
                "last_trade_date": "2026-09-24",
                "scales": list(scales),
                "bars": [
                    {
                        "index": 0,
                        "trade_date": "2026-09-23",
                        "open": 100.0,
                        "high": 101.0,
                        "low": 99.0,
                        "close": 100.0,
                        "volume": 1.0,
                    },
                    {
                        "index": 1,
                        "trade_date": "2026-09-24",
                        "open": 100.0,
                        "high": 102.0,
                        "low": 99.5,
                        "close": 101.0,
                        "volume": 1.0,
                    },
                ],
                "completed": [],
                "forming": [],
                "discovery": [discovery],
                "pivot_counts": {},
                "discovery_scales": [5, 10, 20],
                "discovery_pivot_counts": {"5": 4, "10": 4, "20": 4},
                "recognition_diagnostics": {
                    "authoritative_completed": 0,
                    "authoritative_forming": 0,
                    "discovery_candidates": 1,
                },
                "engine_note": "fixture",
            }

    monkeypatch.setattr(main, "service", StubService())
    monkeypatch.setattr(main, "build_type_i_t5_events", lambda *args, **kwargs: [])

    response = TestClient(main.app).get(
        "/api/harmonic/SSE.688256?bars=420&scales=3,5,8,13"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["completed"] == []
    assert payload["forming"] == []
    assert len(payload["discovery"]) == 1
    candidate = payload["discovery"][0]
    assert candidate["discovery_only"] is True
    assert [point["label"] for point in candidate["points"]] == ["X", "A", "B", "C"]
    assert candidate["discovery"]["authoritative_identity"] is False
    assert candidate["discovery"]["fabricates_d"] is False
    assert candidate["discovery"]["owns_lifecycle"] is False



def test_harmonic_api_routes_intraday_timeframe_without_daily_source_clock(
    monkeypatch,
) -> None:
    calls: list[tuple[str, str, int, bool]] = []

    class StubService:
        def analyze_intraday(
            self,
            instrument_id: str,
            *,
            timeframe: str,
            bars: int,
            force_refresh: bool,
        ):
            calls.append((instrument_id, timeframe, bars, force_refresh))
            return {
                "instrument_id": instrument_id,
                "timeframe": timeframe,
                "price_mode": "qfq",
                "price_basis_id": "intraday:fixture",
                "warning": None,
                "bars_requested": bars,
                "bars_returned": 2,
                "first_trade_date": "2026-09-24 14:00",
                "last_trade_date": "2026-09-24 15:00",
                "scales": [],
                "bars": [
                    {
                        "index": 0,
                        "trade_date": "2026-09-24 14:00",
                        "time": 1790258400,
                        "open": 100.0,
                        "high": 102.0,
                        "low": 99.0,
                        "close": 101.0,
                        "volume": 1000.0,
                    },
                    {
                        "index": 1,
                        "trade_date": "2026-09-24 15:00",
                        "time": 1790262000,
                        "open": 101.0,
                        "high": 103.0,
                        "low": 100.0,
                        "close": 102.0,
                        "volume": 2000.0,
                    },
                ],
                "completed": [],
                "forming": [],
                "discovery": [],
                "pivot_counts": {},
                "type_i_t5_events": [],
                "data_provenance": {
                    "kind": "intraday_research",
                    "provider": "fixture",
                    "timeframe": timeframe,
                    "authoritative_source_lifecycle": False,
                },
                "engine_note": "fixture intraday",
            }

    monkeypatch.setattr(main, "service", StubService())

    response = TestClient(main.app).get(
        "/api/harmonic/SSE.688256?bars=420&timeframe=60m&force_refresh=true"
    )

    assert response.status_code == 200
    payload = response.json()
    assert calls == [("SSE.688256", "60m", 420, True)]
    assert payload["timeframe"] == "60m"
    assert payload["data_provenance"]["kind"] == "intraday_research"
    assert payload["data_provenance"]["authoritative_source_lifecycle"] is False
    assert payload["type_i_t5_events"] == []


def test_harmonic_api_rejects_unknown_timeframe(monkeypatch) -> None:
    class StubService:
        pass

    monkeypatch.setattr(main, "service", StubService())

    response = TestClient(main.app).get(
        "/api/harmonic/SSE.688256?bars=420&timeframe=5m"
    )

    assert response.status_code == 400
    assert "timeframe must be one of" in response.json()["detail"]
