from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .validation import normalize_daily


@dataclass(frozen=True, slots=True)
class DailyAuditReport:
    overlap_rows: int
    left_only_rows: int
    right_only_rows: int
    price_mismatches: int
    volume_mismatches: int
    max_price_abs_diff: float
    max_volume_rel_diff: float

    @property
    def passed(self) -> bool:
        return (
            self.overlap_rows > 0
            and self.left_only_rows == 0
            and self.right_only_rows == 0
            and self.price_mismatches == 0
            and self.volume_mismatches == 0
        )


def compare_daily_sources(
    left: pd.DataFrame,
    right: pd.DataFrame,
    *,
    price_abs_tolerance: float = 0.011,
    volume_relative_tolerance: float = 0.001,
) -> DailyAuditReport:
    """Compare two normalized raw daily feeds on common instrument/date keys.

    Prices are compared with an absolute tolerance slightly above one A-share tick.
    Volumes use a relative tolerance because some upstream feeds round small values.
    """

    a = normalize_daily(left)
    b = normalize_daily(right)

    keys = ["instrument_id", "trade_date"]
    outer = a.merge(b, on=keys, how="outer", suffixes=("_left", "_right"), indicator=True)
    left_only = int((outer["_merge"] == "left_only").sum())
    right_only = int((outer["_merge"] == "right_only").sum())

    common = outer[outer["_merge"] == "both"].copy()
    if common.empty:
        return DailyAuditReport(0, left_only, right_only, 0, 0, 0.0, 0.0)

    price_columns = ["open", "high", "low", "close"]
    price_diff = pd.DataFrame(
        {
            column: (common[f"{column}_left"] - common[f"{column}_right"]).abs()
            for column in price_columns
        }
    )
    price_row_mismatch = (price_diff > price_abs_tolerance).any(axis=1)

    left_volume = common["volume_left"].astype(float)
    right_volume = common["volume_right"].astype(float)
    denominator = pd.concat([left_volume.abs(), right_volume.abs()], axis=1).max(axis=1).clip(lower=1.0)
    volume_rel_diff = (left_volume - right_volume).abs() / denominator

    return DailyAuditReport(
        overlap_rows=len(common),
        left_only_rows=left_only,
        right_only_rows=right_only,
        price_mismatches=int(price_row_mismatch.sum()),
        volume_mismatches=int((volume_rel_diff > volume_relative_tolerance).sum()),
        max_price_abs_diff=float(price_diff.max().max()),
        max_volume_rel_diff=float(volume_rel_diff.max()),
    )
