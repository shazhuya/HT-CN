from datetime import datetime

import pandas as pd
import pytest

from htcn.data.intraday import (
    AkShareIntradayProvider,
    IntradayProviderError,
    ParquetIntradayCache,
)


class StubAk:
    def __init__(self, *, em=None, sina=None, em_error=None):
        self.em = em
        self.sina = sina
        self.em_error = em_error
        self.calls = []

    def stock_zh_a_hist_min_em(self, **kwargs):
        self.calls.append(("em", kwargs))
        if self.em_error is not None:
            raise self.em_error
        return self.em.copy()

    def stock_zh_a_minute(self, **kwargs):
        self.calls.append(("sina", kwargs))
        return self.sina.copy()


def _em_frame():
    return pd.DataFrame(
        {
            "时间": ["2026-09-24 14:00:00", "2026-09-24 15:00:00"],
            "开盘": [100.0, 101.0],
            "收盘": [101.0, 102.0],
            "最高": [102.0, 103.0],
            "最低": [99.0, 100.0],
            "成交量": [1000, 2000],
        }
    )


def _sina_frame():
    return pd.DataFrame(
        {
            "day": ["2026-09-24 14:00:00", "2026-09-24 15:00:00"],
            "open": [100.0, 101.0],
            "high": [102.0, 103.0],
            "low": [99.0, 100.0],
            "close": [101.0, 102.0],
            "volume": [1000, 2000],
        }
    )


def test_intraday_eastmoney_is_primary_and_normalized():
    ak = StubAk(em=_em_frame(), sina=_sina_frame())
    provider = AkShareIntradayProvider(ak)
    result = provider.fetch(
        "SSE.688256",
        timeframe="60m",
        start=datetime(2026, 9, 24, 9, 30),
        end=datetime(2026, 9, 24, 15, 0),
    )

    assert result.provider == "akshare_eastmoney"
    assert result.adjustment == "qfq"
    assert result.frame.columns.tolist() == [
        "trade_time", "open", "high", "low", "close", "volume"
    ]
    assert result.frame["close"].tolist() == [101.0, 102.0]
    assert ak.calls[0][1]["symbol"] == "688256"
    assert ak.calls[0][1]["period"] == "60"


def test_intraday_sina_is_bounded_fallback():
    ak = StubAk(
        em=pd.DataFrame(),
        sina=_sina_frame(),
        em_error=RuntimeError("provider down"),
    )
    provider = AkShareIntradayProvider(ak)
    result = provider.fetch(
        "SZSE.300750",
        timeframe="15m",
        start=datetime(2026, 9, 24, 14, 30),
        end=datetime(2026, 9, 24, 15, 0),
    )

    assert result.provider == "akshare_sina"
    assert result.frame["trade_time"].dt.strftime("%H:%M").tolist() == ["15:00"]
    assert ak.calls[-1][1]["symbol"] == "sz300750"
    assert ak.calls[-1][1]["period"] == "15"


def test_intraday_all_provider_failure_is_explicit():
    ak = StubAk(
        em=pd.DataFrame(),
        sina=pd.DataFrame(),
        em_error=RuntimeError("down"),
    )
    provider = AkShareIntradayProvider(ak)
    with pytest.raises(IntradayProviderError, match="no intraday provider succeeded"):
        provider.fetch(
            "SSE.688256",
            timeframe="60m",
            start=datetime(2026, 9, 1),
            end=datetime(2026, 9, 24, 15, 0),
        )


def test_intraday_cache_roundtrip_preserves_provenance(tmp_path):
    ak = StubAk(em=_em_frame(), sina=_sina_frame())
    bars = AkShareIntradayProvider(ak).fetch(
        "SSE.688256",
        timeframe="60m",
        start=datetime(2026, 9, 24, 9, 30),
        end=datetime(2026, 9, 24, 15, 0),
    )
    cache = ParquetIntradayCache(tmp_path)

    path = cache.write(bars)
    restored = cache.read("SSE.688256", "60m")

    assert path.exists()
    assert restored is not None
    assert restored.provider == "akshare_eastmoney"
    assert restored.adjustment == "qfq"
    pd.testing.assert_frame_equal(restored.frame, bars.frame)


def test_intraday_rejects_unsupported_timeframe():
    ak = StubAk(em=_em_frame(), sina=_sina_frame())
    with pytest.raises(ValueError, match="unsupported intraday timeframe"):
        AkShareIntradayProvider(ak).fetch(
            "SSE.688256",
            timeframe="5m",
            start=datetime(2026, 9, 1),
            end=datetime(2026, 9, 24),
        )
