from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from htcn.research.snapshot_cache import (
    load_research_snapshot,
    snapshot_manifest_entry,
    snapshot_paths,
    write_research_snapshot,
)


def _frame(instrument_id: str = "SSE.600000", bars: int = 12) -> pd.DataFrame:
    rows = []
    start = date(2024, 1, 1)
    for index in range(bars):
        close = 10.0 + index * 0.1
        rows.append(
            {
                "instrument_id": instrument_id,
                "trade_date": start + timedelta(days=index),
                "open": close,
                "high": close + 0.2,
                "low": close - 0.2,
                "close": close + 0.05,
                "volume": 1000 + index,
            }
        )
    return pd.DataFrame(rows)


def test_snapshot_round_trip_is_sha_verified(tmp_path) -> None:
    saved = write_research_snapshot(
        tmp_path,
        instrument_id="SSE.600000",
        frame=_frame(),
        source="baostock_qfq",
        requested_start="2024-01-01",
        requested_end="2024-01-12",
        max_bars=12,
    )
    loaded, reason = load_research_snapshot(
        tmp_path,
        instrument_id="SSE.600000",
        requested_start="2024-01-01",
        requested_end="2024-01-12",
        max_bars=12,
    )
    assert reason == "hit_verified"
    assert loaded is not None
    assert loaded.cache_status == "hit_verified"
    assert loaded.source == "baostock_qfq"
    assert loaded.sha256 == saved.sha256
    assert len(loaded.frame) == 12

    manifest = snapshot_manifest_entry(loaded)
    assert manifest["instrument_id"] == "SSE.600000"
    assert manifest["snapshot_cutoff"] == "2024-01-12"
    assert manifest["sha256"] == saved.sha256


def test_changed_cutoff_invalidates_restored_cache(tmp_path) -> None:
    write_research_snapshot(
        tmp_path,
        instrument_id="SSE.600000",
        frame=_frame(),
        source="akshare_qfq",
        requested_start="2024-01-01",
        requested_end="2024-01-12",
        max_bars=12,
    )
    loaded, reason = load_research_snapshot(
        tmp_path,
        instrument_id="SSE.600000",
        requested_start="2024-01-01",
        requested_end="2024-01-13",
        max_bars=12,
    )
    assert loaded is None
    assert "snapshot_cutoff" in reason


def test_larger_requested_capacity_invalidates_smaller_snapshot(tmp_path) -> None:
    write_research_snapshot(
        tmp_path,
        instrument_id="SSE.600000",
        frame=_frame(),
        source="akshare_qfq",
        requested_start="2024-01-01",
        requested_end="2024-01-12",
        max_bars=8,
    )
    loaded, reason = load_research_snapshot(
        tmp_path,
        instrument_id="SSE.600000",
        requested_start="2024-01-01",
        requested_end="2024-01-12",
        max_bars=12,
    )
    assert loaded is None
    assert "bar_capacity" in reason


def test_tampered_parquet_is_rejected(tmp_path) -> None:
    write_research_snapshot(
        tmp_path,
        instrument_id="SSE.600000",
        frame=_frame(),
        source="baostock_qfq",
        requested_start="2024-01-01",
        requested_end="2024-01-12",
        max_bars=12,
    )
    parquet_path, _ = snapshot_paths(tmp_path, "SSE.600000")
    parquet_path.write_bytes(parquet_path.read_bytes() + b"tamper")

    loaded, reason = load_research_snapshot(
        tmp_path,
        instrument_id="SSE.600000",
        requested_start="2024-01-01",
        requested_end="2024-01-12",
        max_bars=12,
    )
    assert loaded is None
    assert reason == "sha256_mismatch"


def test_earlier_cached_start_covers_later_requested_start(tmp_path) -> None:
    write_research_snapshot(
        tmp_path,
        instrument_id="SSE.600000",
        frame=_frame(),
        source="baostock_qfq",
        requested_start="2024-01-01",
        requested_end="2024-01-12",
        max_bars=12,
    )
    loaded, reason = load_research_snapshot(
        tmp_path,
        instrument_id="SSE.600000",
        requested_start="2024-01-04",
        requested_end="2024-01-12",
        max_bars=8,
    )
    assert reason == "hit_verified"
    assert loaded is not None
    assert len(loaded.frame) == 8
    assert pd.Timestamp(loaded.frame.iloc[0]["trade_date"]).date().isoformat() == "2024-01-05"
