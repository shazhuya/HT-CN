from __future__ import annotations

from datetime import datetime

import pandas as pd

from htcn.app.recognition_discovery_service import RecognitionDiscoveryService
from htcn.data.intraday import IntradayBars


class FixtureIntradayProvider:
    def __init__(self, frame: pd.DataFrame) -> None:
        self.frame = frame
        self.calls: list[tuple[str, str, str]] = []

    def fetch(
        self,
        instrument_id: str,
        *,
        timeframe: str,
        start: datetime,
        end: datetime,
        adjust: str = "qfq",
    ) -> IntradayBars:
        self.calls.append((instrument_id, timeframe, adjust))
        return IntradayBars(
            instrument_id=instrument_id,
            timeframe=timeframe,
            adjustment=adjust,
            provider="fixture_intraday",
            fetched_at=pd.Timestamp.now(tz="Asia/Shanghai"),
            frame=self.frame.copy(),
        )


def _frame(rows: int = 260) -> pd.DataFrame:
    times = pd.date_range("2026-09-01 09:30", periods=rows, freq="15min")
    values = []
    for index, stamp in enumerate(times):
        base = 100.0 + (index % 17) * 0.3
        values.append(
            {
                "trade_time": stamp,
                "open": base,
                "high": base + 1.0,
                "low": base - 1.0,
                "close": base + 0.2,
                "volume": 1000.0 + index,
            }
        )
    return pd.DataFrame(values)


def test_intraday_analysis_is_self_contained_and_preserves_visible_shanghai_clock(
    tmp_path,
) -> None:
    provider = FixtureIntradayProvider(_frame())
    service = RecognitionDiscoveryService(tmp_path, intraday_provider=provider)

    payload = service.analyze_intraday(
        "SSE.688256",
        timeframe="15m",
        bars=240,
        force_refresh=True,
    )

    assert provider.calls == [("SSE.688256", "15m", "qfq")]
    assert payload["timeframe"] == "15m"
    assert payload["price_mode"] == "qfq"
    assert payload["bars_returned"] == 240
    assert payload["completed"] == []
    assert payload["forming"] == []
    assert payload["data_provenance"]["kind"] == "intraday_research"
    assert payload["data_provenance"]["provider"] == "fixture_intraday"
    assert payload["data_provenance"]["authoritative_source_lifecycle"] is False
    assert payload["discovery_scales"] == [5, 10, 20]

    first = payload["bars"][0]
    expected_stamp = pd.Timestamp(first["trade_date"], tz="UTC")
    assert first["time"] == int(expected_stamp.timestamp())

    cache_path = tmp_path / "intraday" / "15m" / "SSE.688256.parquet"
    assert cache_path.exists()


def test_intraday_analysis_can_reuse_fresh_cache_without_provider_call(tmp_path) -> None:
    provider = FixtureIntradayProvider(_frame())
    service = RecognitionDiscoveryService(tmp_path, intraday_provider=provider)

    first = service.analyze_intraday(
        "SSE.688256",
        timeframe="60m",
        bars=200,
        force_refresh=True,
    )
    assert first["data_provenance"]["provider"] == "fixture_intraday"
    assert len(provider.calls) == 1

    second = service.analyze_intraday(
        "SSE.688256",
        timeframe="60m",
        bars=200,
        force_refresh=False,
    )

    assert len(provider.calls) == 1
    assert second["data_provenance"]["provider"] == "fixture_intraday"
    assert second["bars_returned"] == 200
