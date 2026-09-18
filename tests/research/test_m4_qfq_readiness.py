from __future__ import annotations

import pandas as pd

from scripts.m4_prepare_qfq_universe import (
    _repair_safe_internal_factor_gaps,
    _strict_factor_candidate,
)


def _raw(days: int = 20) -> pd.DataFrame:
    dates = pd.bdate_range("2026-01-01", periods=days)
    return pd.DataFrame({
        "instrument_id": ["SSE.600000"] * len(dates),
        "trade_date": dates,
        "open": [10.0] * len(dates),
        "high": [10.5] * len(dates),
        "low": [9.5] * len(dates),
        "close": [10.0] * len(dates),
        "volume": [1000.0] * len(dates),
    })


def _factors(raw: pd.DataFrame, keep: list[int]) -> pd.DataFrame:
    selected = raw.iloc[keep]
    return pd.DataFrame({
        "instrument_id": selected["instrument_id"].tolist(),
        "trade_date": selected["trade_date"].tolist(),
        "price_factor": [1.0] * len(selected),
        "mode": ["qfq"] * len(selected),
        "source": ["test"] * len(selected),
    })


def test_strict_qfq_candidate_accepts_full_history() -> None:
    raw = _raw()
    factors = _factors(raw, list(range(len(raw))))
    ready, reason = _strict_factor_candidate(raw, factors)
    assert ready is True
    assert reason == "strict_factor_candidate_ready"


def test_strict_qfq_candidate_allows_small_trailing_gap_for_carry_forward() -> None:
    raw = _raw(20)
    factors = _factors(raw, list(range(19)))
    ready, reason = _strict_factor_candidate(raw, factors)
    assert ready is True
    assert reason == "strict_factor_candidate_ready"


def test_strict_qfq_candidate_rejects_historical_internal_gap() -> None:
    raw = _raw(20)
    keep = [index for index in range(20) if index != 10]
    factors = _factors(raw, keep)
    ready, reason = _strict_factor_candidate(raw, factors)
    assert ready is False
    assert reason.startswith("historical_factor_gap:")


def test_strict_qfq_candidate_rejects_low_overlap() -> None:
    raw = _raw(20)
    factors = _factors(raw, list(range(10)))
    ready, reason = _strict_factor_candidate(raw, factors)
    assert ready is False
    assert reason.startswith("factor_overlap_too_low:")


def test_strict_qfq_candidate_rejects_nonpositive_factor() -> None:
    raw = _raw()
    factors = _factors(raw, list(range(len(raw))))
    factors.loc[factors.index[-1], "price_factor"] = 0.0
    ready, reason = _strict_factor_candidate(raw, factors)
    assert ready is False
    assert reason == "non_positive_factor"



def test_safe_internal_gap_repair_fills_stable_bracketed_session() -> None:
    raw = _raw(20)
    keep = [index for index in range(20) if index != 10]
    factors = _factors(raw, keep)
    factors.loc[factors.index < 10, "price_factor"] = 1.0000
    factors.loc[factors.index >= 10, "price_factor"] = 1.0004

    repaired, audit = _repair_safe_internal_factor_gaps(raw, factors)

    assert len(repaired) == len(raw)
    assert len(audit) == 1
    assert audit[0]["gap_raw_session_count"] == 1
    assert audit[0]["relative_factor_drift"] < 0.005
    ready, reason = _strict_factor_candidate(raw, repaired)
    assert ready is True
    assert reason == "strict_factor_candidate_ready"


def test_safe_internal_gap_repair_refuses_factor_regime_jump() -> None:
    raw = _raw(20)
    keep = [index for index in range(20) if index != 10]
    factors = _factors(raw, keep)
    factors.loc[factors.index < 10, "price_factor"] = 1.0
    factors.loc[factors.index >= 10, "price_factor"] = 0.9

    repaired, audit = _repair_safe_internal_factor_gaps(raw, factors)

    assert len(repaired) == len(factors)
    assert audit == []
    ready, reason = _strict_factor_candidate(raw, repaired)
    assert ready is False
    assert reason.startswith("historical_factor_gap:")


def test_safe_internal_gap_repair_does_not_fill_trailing_freshness_gap() -> None:
    raw = _raw(20)
    factors = _factors(raw, list(range(19)))

    repaired, audit = _repair_safe_internal_factor_gaps(raw, factors)

    assert len(repaired) == 19
    assert audit == []
    ready, reason = _strict_factor_candidate(raw, repaired)
    assert ready is True
    assert reason == "strict_factor_candidate_ready"



def _historical_saturday_raw(
    *,
    saturday_pre_close: float = 10.0,
    monday_pre_close: float = 10.2,
) -> pd.DataFrame:
    dates = pd.to_datetime([
        "1991-04-12",
        "1991-04-13",
        "1991-04-15",
    ])
    closes = [10.0, 10.2, 10.3]
    return pd.DataFrame({
        "instrument_id": ["SZSE.000001"] * 3,
        "trade_date": dates,
        "open": [10.0, 10.0, 10.2],
        "high": [10.2, 10.3, 10.4],
        "low": [9.9, 9.9, 10.1],
        "close": closes,
        "volume": [1000.0, 1100.0, 1200.0],
        "pre_close": [9.9, saturday_pre_close, monday_pre_close],
    })


def test_historical_saturday_gap_can_use_raw_preclose_continuity() -> None:
    raw = _historical_saturday_raw()
    factors = pd.DataFrame({
        "instrument_id": ["SZSE.000001", "SZSE.000001"],
        "trade_date": pd.to_datetime(["1991-04-12", "1991-04-15"]),
        "price_factor": [1.0, 1.02],
        "mode": ["qfq", "qfq"],
        "source": ["baostock_qfq", "baostock_qfq"],
    })

    repaired, audit = _repair_safe_internal_factor_gaps(raw, factors)

    assert len(repaired) == 3
    assert len(audit) == 1
    assert audit[0]["fill_rule"] == (
        "historical_saturday_raw_preclose_continuity"
    )
    assert audit[0]["relative_factor_drift"] > 0.005
    assert audit[0]["relative_factor_drift"] < 0.05
    ready, reason = _strict_factor_candidate(raw, repaired)
    assert ready is True
    assert reason == "strict_factor_candidate_ready"


def test_historical_saturday_gap_refuses_raw_preclose_discontinuity() -> None:
    raw = _historical_saturday_raw(saturday_pre_close=8.0)
    factors = pd.DataFrame({
        "instrument_id": ["SZSE.000001", "SZSE.000001"],
        "trade_date": pd.to_datetime(["1991-04-12", "1991-04-15"]),
        "price_factor": [1.0, 1.02],
        "mode": ["qfq", "qfq"],
        "source": ["baostock_qfq", "baostock_qfq"],
    })

    repaired, audit = _repair_safe_internal_factor_gaps(raw, factors)

    assert len(repaired) == 2
    assert audit == []
    ready, reason = _strict_factor_candidate(raw, repaired)
    assert ready is False
    assert reason.startswith("historical_factor_gap:")
