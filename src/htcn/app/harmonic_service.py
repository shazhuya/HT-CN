from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from htcn.data.adjustment import AdjustmentFactorStore, apply_price_factors
from htcn.data.delta import DailyHistoryView, MarketDailyDeltaStore
from htcn.data.store import ParquetDailyStore
from htcn.harmonic.engine import CompletedMatch, FormingMatch, HarmonicScan, scan_frame


class DatasetNotFoundError(FileNotFoundError):
    pass


class LocalHarmonicService:
    """Read local A-share history and run the deterministic harmonic core."""

    def __init__(self, data_root: str | Path) -> None:
        self.data_root = Path(data_root)
        self.base = ParquetDailyStore(self.data_root / "daily")
        self.deltas = MarketDailyDeltaStore(self.data_root / "daily_delta")
        self.history = DailyHistoryView(self.base, self.deltas)
        self.factors = AdjustmentFactorStore(self.data_root / "adjustment" / "qfq")

    def _load_history(self, instrument_id: str) -> pd.DataFrame:
        frame = self.history.read(instrument_id)
        if frame.empty:
            raise DatasetNotFoundError(instrument_id)
        return frame.sort_values("trade_date").reset_index(drop=True)

    def _continuous_view(self, instrument_id: str, raw: pd.DataFrame) -> tuple[pd.DataFrame, str, str | None]:
        factors = self.factors.read(instrument_id)
        if factors.empty:
            return raw, "raw", "QFQ 因子尚未建立，本次仅展示原始价格；该结果不用于正式谐波结论。"

        factor_dates = set(pd.to_datetime(factors["trade_date"]).dt.normalize())
        raw_dates = pd.to_datetime(raw["trade_date"]).dt.normalize()
        missing = [stamp for stamp in raw_dates if stamp not in factor_dates]
        if not missing:
            return apply_price_factors(raw, factors), "qfq", None

        # Daily deltas may be one session newer than the last factor refresh. A price factor is
        # piecewise constant between corporate actions, so carrying the last known factor forward
        # for newer sessions preserves continuity while clearly flagging the assumption.
        latest_factor_date = pd.Timestamp(factors["trade_date"].max()).normalize()
        if all(stamp > latest_factor_date for stamp in missing):
            extended = factors.copy()
            last = extended.sort_values("trade_date").iloc[-1]
            additions = []
            for stamp in missing:
                additions.append(
                    {
                        "instrument_id": instrument_id,
                        "trade_date": stamp,
                        "price_factor": float(last["price_factor"]),
                        "mode": "qfq",
                        "source": f"{last['source']}:carry_forward",
                    }
                )
            extended = pd.concat([extended, pd.DataFrame(additions)], ignore_index=True)
            return (
                apply_price_factors(raw, extended),
                "qfq_carry_forward",
                f"QFQ 因子最新至 {latest_factor_date.date().isoformat()}，之后 {len(missing)} 个交易日沿用最近因子。",
            )

        return raw, "raw", "QFQ 因子存在历史缺口，本次退回原始价格并禁止把识别结果视为正式结论。"

    @staticmethod
    def _point_payload(point, dates: pd.Series) -> dict[str, Any]:
        payload = asdict(point)
        if 0 <= point.index < len(dates):
            payload["trade_date"] = pd.Timestamp(dates.iloc[point.index]).date().isoformat()
        return payload

    @staticmethod
    def _prz_payload(prz) -> dict[str, Any]:
        return {
            "price_low": float(prz.price_low),
            "price_high": float(prz.price_high),
            "width": float(prz.width),
            "component_price_low": float(prz.component_price_low),
            "component_price_high": float(prz.component_price_high),
            "components": [asdict(component) for component in prz.components],
        }

    @staticmethod
    def _identity_conflicts(items: tuple[CompletedMatch, ...] | tuple[FormingMatch, ...]) -> dict[tuple[int, ...], list[str]]:
        groups: dict[tuple[int, ...], list[tuple[float, str, int]]] = {}
        for item in items:
            groups.setdefault(item.conflict_key, []).append(
                (float(item.geometry_score), item.pattern_id, int(item.scale))
            )
        return {
            key: [f"{pattern_id}@S{scale}" for _, pattern_id, scale in sorted(rows, reverse=True)]
            for key, rows in groups.items()
        }

    def _completed_payload(
        self,
        item: CompletedMatch,
        dates: pd.Series,
        conflict_ids: list[str],
    ) -> dict[str, Any]:
        metrics = item.evaluation.metrics
        own_id = f"{item.pattern_id}@S{item.scale}"
        return {
            "pattern_id": item.pattern_id,
            "direction": item.direction.value,
            "state": item.state.value,
            "scale": item.scale,
            "geometry_score": item.geometry_score,
            "conflict_key": list(item.conflict_key),
            "identity_conflicts": conflict_ids,
            "is_primary_identity": bool(conflict_ids and conflict_ids[0] == own_id),
            "points": [self._point_payload(point, dates) for point in item.points],
            "prz": self._prz_payload(item.evaluation.prz),
            "metrics": {
                "b_xa": metrics.b_xa.value,
                "c_ab": metrics.c_ab.value,
                "bc_projection": metrics.bc_projection.value,
                "d_xa": metrics.d_xa.value,
                "cd_ab": metrics.cd_ab.value,
            },
            "checks": [asdict(check) for check in item.evaluation.checks],
            "abcd_distance": item.evaluation.abcd_distance,
        }

    def _forming_payload(
        self,
        item: FormingMatch,
        dates: pd.Series,
        conflict_ids: list[str],
    ) -> dict[str, Any]:
        own_id = f"{item.pattern_id}@S{item.scale}"
        c_index = int(item.points[-1].index)
        latest_index = max(len(dates) - 1, 0)
        return {
            "pattern_id": item.pattern_id,
            "direction": item.direction.value,
            "state": item.state.value,
            "scale": item.scale,
            "geometry_score": item.geometry_score,
            "conflict_key": list(item.conflict_key),
            "identity_conflicts": conflict_ids,
            "is_primary_identity": bool(conflict_ids and conflict_ids[0] == own_id),
            "points": [self._point_payload(point, dates) for point in item.points],
            "prz": self._prz_payload(item.projection.prz),
            "metrics": {"b_xa": item.projection.b_xa},
            "source_tolerance_used": item.projection.source_tolerance_used,
            "bars_since_c": max(0, latest_index - c_index),
            "frontier": True,
        }

    @staticmethod
    def _bar_payload(frame: pd.DataFrame) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for index, row in frame.iterrows():
            out.append(
                {
                    "index": int(index),
                    "trade_date": pd.Timestamp(row["trade_date"]).date().isoformat(),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]),
                }
            )
        return out

    def analyze(
        self,
        instrument_id: str,
        *,
        bars: int = 420,
        scales: tuple[int, ...] = (3, 5, 8, 13),
        max_completed: int = 30,
        max_forming: int = 30,
    ) -> dict[str, Any]:
        if bars < 80 or bars > 3000:
            raise ValueError("bars must be between 80 and 3000")
        if not scales or any(scale < 1 or scale > 55 for scale in scales):
            raise ValueError("scales must contain values between 1 and 55")

        raw = self._load_history(instrument_id)
        continuous, price_mode, warning = self._continuous_view(instrument_id, raw)
        selected = continuous.tail(bars).reset_index(drop=True)
        scan: HarmonicScan = scan_frame(
            selected,
            scales=scales,
            max_completed=max_completed,
            max_forming=max_forming,
        )
        dates = selected["trade_date"]
        completed_conflicts = self._identity_conflicts(scan.completed)
        forming_conflicts = self._identity_conflicts(scan.forming)
        completed = [
            self._completed_payload(item, dates, completed_conflicts[item.conflict_key])
            for item in scan.completed
        ]
        forming = [
            self._forming_payload(item, dates, forming_conflicts[item.conflict_key])
            for item in scan.forming
        ]

        return {
            "instrument_id": instrument_id,
            "price_mode": price_mode,
            "warning": warning,
            "bars_requested": bars,
            "bars_returned": len(selected),
            "first_trade_date": pd.Timestamp(selected["trade_date"].iloc[0]).date().isoformat(),
            "last_trade_date": pd.Timestamp(selected["trade_date"].iloc[-1]).date().isoformat(),
            "scales": list(scales),
            "bars": self._bar_payload(selected),
            "completed": completed,
            "forming": forming,
            "pivot_counts": {str(scale): len(pivots) for scale, pivots in scan.pivots_by_scale.items()},
            "engine_note": "geometry_score 仅衡量几何贴合度，不代表胜率、预期收益或交易建议；形成中只保留各尺度最新 XABC frontier，同节点多身份保留审计但默认只展示主身份。",
        }
