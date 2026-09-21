from __future__ import annotations

from datetime import timedelta

import pandas as pd

from scripts.m4_prepare_qfq_universe import (
    _fetch_candidate,
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
    assert reason.startswith(
        ("historical_factor_gap:", "factor_overlap_too_low:")
    )


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
    assert reason.startswith(
        ("historical_factor_gap:", "factor_overlap_too_low:")
    )


def test_legacy_saturday_gap_outside_formal_capture_window_can_bridge() -> None:
    early = pd.DataFrame({
        "instrument_id": ["SZSE.000001"] * 3,
        "trade_date": pd.to_datetime(["1991-04-12", "1991-04-13", "1991-04-15"]),
        "open": [10.0, 10.0, 12.0],
        "high": [10.2, 10.3, 12.2],
        "low": [9.9, 9.8, 11.8],
        "close": [10.0, 10.2, 12.0],
        "pre_close": [9.9, 8.0, 10.2],
        "volume": [1000.0, 1100.0, 1200.0],
    })
    recent_dates = pd.bdate_range("2024-01-02", periods=430)
    recent = pd.DataFrame({
        "instrument_id": ["SZSE.000001"] * len(recent_dates),
        "trade_date": recent_dates,
        "open": [12.0] * len(recent_dates),
        "high": [12.2] * len(recent_dates),
        "low": [11.8] * len(recent_dates),
        "close": [12.0] * len(recent_dates),
        "pre_close": [12.0] * len(recent_dates),
        "volume": [1200.0] * len(recent_dates),
    })
    raw = pd.concat([early, recent], ignore_index=True)
    keep = raw["trade_date"] != pd.Timestamp("1991-04-13")
    factors = pd.DataFrame({
        "instrument_id": ["SZSE.000001"] * int(keep.sum()),
        "trade_date": raw.loc[keep, "trade_date"].tolist(),
        "price_factor": [1.0] + [1.20] * (int(keep.sum()) - 1),
        "mode": ["qfq"] * int(keep.sum()),
        "source": ["baostock_qfq"] * int(keep.sum()),
    })

    repaired, audit = _repair_safe_internal_factor_gaps(raw, factors)

    assert len(repaired) == len(raw)
    assert len(audit) == 1
    assert audit[0]["fill_rule"] == "legacy_saturday_outside_formal_capture_window"
    assert audit[0]["allowed_factor_drift"] is None
    ready, reason = _strict_factor_candidate(raw, repaired)
    assert ready is True
    assert reason == "strict_factor_candidate_ready"


def test_legacy_saturday_bridge_never_applies_inside_formal_capture_window() -> None:
    raw = _historical_saturday_raw(saturday_pre_close=8.0)
    factors = pd.DataFrame({
        "instrument_id": ["SZSE.000001", "SZSE.000001"],
        "trade_date": pd.to_datetime(["1991-04-12", "1991-04-15"]),
        "price_factor": [1.0, 1.20],
        "mode": ["qfq", "qfq"],
        "source": ["baostock_qfq", "baostock_qfq"],
    })
    repaired, audit = _repair_safe_internal_factor_gaps(raw, factors)
    assert len(repaired) == len(factors)
    assert audit == []



class _FiveSaturdayAdjustedProvider:
    name = "five_saturday_fixture"

    def __init__(self, frame: pd.DataFrame) -> None:
        self.frame = frame

    def get_daily_adjusted(
        self,
        instrument_id,
        start,
        end,
        *,
        mode="qfq",
    ) -> pd.DataFrame:
        return self.frame.copy()


def _five_real_1991_saturday_fixture() -> tuple[pd.DataFrame, pd.DataFrame]:
    gap_dates = pd.to_datetime([
        "1991-04-13",
        "1991-04-20",
        "1991-05-04",
        "1991-07-20",
        "1991-11-23",
    ])
    early_dates: list[pd.Timestamp] = []
    pre_gap_dates: set[pd.Timestamp] = set()
    post_gap_dates: set[pd.Timestamp] = set()
    for value in gap_dates:
        stamp = pd.Timestamp(value)
        previous = stamp - timedelta(days=1)
        following = stamp + timedelta(days=2)
        early_dates.extend([previous, stamp, following])
        pre_gap_dates.add(previous)
        post_gap_dates.add(following)
    recent_dates = list(pd.bdate_range("2024-01-02", periods=430))
    dates = pd.DatetimeIndex(sorted(set(early_dates + recent_dates)))
    raw = pd.DataFrame({
        "instrument_id": ["SZSE.000001"] * len(dates),
        "trade_date": dates,
        "open": [10.0] * len(dates),
        "high": [10.5] * len(dates),
        "low": [9.5] * len(dates),
        "close": [10.0] * len(dates),
        "volume": [1000.0] * len(dates),
    })

    adjusted = raw.loc[
        ~raw["trade_date"].isin(gap_dates)
    ].copy()
    adjusted_factor = adjusted["trade_date"].map(
        lambda stamp: (
            1.0
            if pd.Timestamp(stamp) in pre_gap_dates
            else 1.2
        )
    )
    for column in ("open", "high", "low", "close"):
        adjusted[column] = adjusted[column] * adjusted_factor
    adjusted = adjusted.reset_index(drop=True)
    return raw, adjusted


def test_real_five_1991_saturday_gaps_bridge_without_preclose() -> None:
    raw, adjusted = _five_real_1991_saturday_fixture()
    factors, source, attempts, repairs = _fetch_candidate(
        instrument_id="SZSE.000001",
        raw=raw,
        provider=_FiveSaturdayAdjustedProvider(adjusted),
        retries=0,
    )

    assert source == "five_saturday_fixture_qfq"
    assert attempts == 1
    assert len(repairs) == 5
    assert {
        item["gap_start_trade_date"] for item in repairs
    } == {
        "1991-04-13",
        "1991-04-20",
        "1991-05-04",
        "1991-07-20",
        "1991-11-23",
    }
    assert {
        item["fill_rule"] for item in repairs
    } == {"legacy_saturday_outside_formal_capture_window"}
    assert all(item["allowed_factor_drift"] is None for item in repairs)
    ready, reason = _strict_factor_candidate(raw, factors)
    assert ready is True
    assert reason == "strict_factor_candidate_ready"


def test_legacy_bridge_without_preclose_stays_forbidden_inside_formal_window() -> None:
    raw = _historical_saturday_raw().drop(columns=["pre_close"])
    factors = pd.DataFrame({
        "instrument_id": ["SZSE.000001", "SZSE.000001"],
        "trade_date": pd.to_datetime(["1991-04-12", "1991-04-15"]),
        "price_factor": [1.0, 1.20],
        "mode": ["qfq", "qfq"],
        "source": ["baostock_qfq", "baostock_qfq"],
    })

    repaired, audit = _repair_safe_internal_factor_gaps(raw, factors)

    assert len(repaired) == len(factors)
    assert audit == []
