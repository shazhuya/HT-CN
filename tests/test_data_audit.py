import pandas as pd

from htcn.data.audit import compare_daily_sources


def frame(volume_second: float = 2000.0, close_second: float = 11.0) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "instrument_id": "SSE.688256",
                "trade_date": "2026-09-14",
                "open": 10.0,
                "high": 10.5,
                "low": 9.8,
                "close": 10.2,
                "volume": 1000.0,
            },
            {
                "instrument_id": "SSE.688256",
                "trade_date": "2026-09-15",
                "open": 10.3,
                "high": 11.2,
                "low": 10.1,
                "close": close_second,
                "volume": volume_second,
            },
        ]
    )


def test_equal_sources_pass() -> None:
    report = compare_daily_sources(frame(), frame())
    assert report.passed
    assert report.overlap_rows == 2
    assert report.price_mismatches == 0
    assert report.volume_mismatches == 0


def test_price_mismatch_is_detected() -> None:
    right = frame()
    right.loc[1, "close"] = 11.2
    report = compare_daily_sources(frame(), right)
    assert not report.passed
    assert report.price_mismatches == 1


def test_volume_mismatch_is_detected() -> None:
    report = compare_daily_sources(frame(), frame(volume_second=2200.0))
    assert not report.passed
    assert report.volume_mismatches == 1
