from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from htcn.data.adjustment import AdjustmentFactorStore, apply_price_factors
from htcn.data.delta import DailyHistoryView, MarketDailyDeltaStore
from htcn.data.store import ParquetDailyStore
from htcn.harmonic.abcd import ABCDFormingMatch, ABCDMatch
from htcn.harmonic.engine import CompletedMatch, FormingMatch, HarmonicScan, scan_frame
from htcn.harmonic.five_zero import FiveZeroFormingMatch, FiveZeroMatch
from htcn.harmonic.lifecycle import audit_completed_reaction
from htcn.harmonic.models import HarmonicPoint, PatternDirection, Pivot
from htcn.harmonic.pivots import build_pivot_consensus
from htcn.harmonic.shark import SharkFormingMatch, SharkMatch


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

    @staticmethod
    def _pivot_support_payload(
        points: tuple[HarmonicPoint, ...],
        *,
        source_scale: int,
        pivots_by_scale: dict[int, tuple[Pivot, ...]],
        consensus: dict,
    ) -> list[dict[str, Any]]:
        source_by_index = {
            int(pivot.index): pivot
            for pivot in pivots_by_scale.get(int(source_scale), ())
        }
        out: list[dict[str, Any]] = []
        for point in points:
            source = source_by_index.get(int(point.index))
            if source is None:
                out.append(
                    {
                        "label": point.label,
                        "index": int(point.index),
                        "kind": None,
                        "scales": [int(source_scale)],
                        "support_count": 1,
                        "max_scale": int(source_scale),
                    }
                )
                continue
            scales = consensus.get((int(point.index), source.kind), (int(source_scale),))
            out.append(
                {
                    "label": point.label,
                    "index": int(point.index),
                    "kind": source.kind.value,
                    "scales": list(scales),
                    "support_count": len(scales),
                    "max_scale": max(scales),
                }
            )
        return out

    @staticmethod
    def _bars_to_target(
        frame: pd.DataFrame,
        *,
        completion_index: int,
        target: float,
        direction: PatternDirection,
    ) -> int | None:
        future = frame.iloc[completion_index + 1 :]
        for offset, (_, row) in enumerate(future.iterrows(), start=1):
            if direction is PatternDirection.BULLISH and float(row["high"]) >= target:
                return offset
            if direction is PatternDirection.BEARISH and float(row["low"]) <= target:
                return offset
        return None

    def _completed_payload(
        self,
        item: CompletedMatch,
        frame: pd.DataFrame,
        dates: pd.Series,
        conflict_ids: list[str],
        pivots_by_scale: dict[int, tuple[Pivot, ...]],
        pivot_consensus: dict,
    ) -> dict[str, Any]:
        metrics = item.evaluation.metrics
        own_id = f"{item.pattern_id}@S{item.scale}"
        reaction = audit_completed_reaction(
            frame,
            points=item.points,
            direction=item.direction,
            prz=item.evaluation.prz,
        )
        return {
            "pattern_id": item.pattern_id,
            "schema": "XABCD",
            "direction": item.direction.value,
            "state": item.state.value,
            "scale": item.scale,
            "geometry_score": item.geometry_score,
            "conflict_key": list(item.conflict_key),
            "identity_conflicts": conflict_ids,
            "is_primary_identity": bool(conflict_ids and conflict_ids[0] == own_id),
            "points": [self._point_payload(point, dates) for point in item.points],
            "pivot_support": self._pivot_support_payload(
                item.points,
                source_scale=item.scale,
                pivots_by_scale=pivots_by_scale,
                consensus=pivot_consensus,
            ),
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
            "reaction_audit": reaction.as_payload(),
        }

    def _abcd_payload(
        self,
        item: ABCDMatch,
        frame: pd.DataFrame,
        dates: pd.Series,
        pivots_by_scale: dict[int, tuple[Pivot, ...]],
        pivot_consensus: dict,
    ) -> dict[str, Any]:
        evaluation = item.evaluation
        metrics = evaluation.metrics
        reaction = audit_completed_reaction(
            frame,
            points=item.points,
            direction=item.direction,
            prz=evaluation.prz,
        )
        return {
            "pattern_id": "abcd",
            "schema": "ABCD",
            "direction": item.direction.value,
            "state": item.state.value,
            "scale": item.scale,
            "geometry_score": item.geometry_score,
            "conflict_key": list(item.conflict_key),
            "identity_conflicts": [f"abcd@S{item.scale}"],
            "is_primary_identity": True,
            "points": [self._point_payload(point, dates) for point in item.points],
            "pivot_support": self._pivot_support_payload(
                item.points,
                source_scale=item.scale,
                pivots_by_scale=pivots_by_scale,
                consensus=pivot_consensus,
            ),
            "prz": self._prz_payload(evaluation.prz),
            "metrics": {
                "c_ab": metrics.c_ab.value,
                "bc_projection": metrics.bc_projection.value,
                "cd_ab": metrics.cd_ab.value,
                "reciprocal_c_target": evaluation.reciprocal_c_target,
                "reciprocal_bc_target": evaluation.reciprocal_bc_target,
            },
            "checks": [asdict(check) for check in evaluation.checks],
            "reaction_audit": reaction.as_payload(),
        }

    def _abcd_forming_payload(
        self,
        item: ABCDFormingMatch,
        dates: pd.Series,
        pivots_by_scale: dict[int, tuple[Pivot, ...]],
        pivot_consensus: dict,
    ) -> dict[str, Any]:
        projection = item.projection
        return {
            "pattern_id": "abcd",
            "schema": "ABCD",
            "direction": item.direction.value,
            "state": item.state.value,
            "scale": item.scale,
            "geometry_score": item.geometry_score,
            "conflict_key": list(item.conflict_key),
            "identity_conflicts": [f"abcd@S{item.scale}"],
            "is_primary_identity": True,
            "points": [self._point_payload(point, dates) for point in item.points],
            "pivot_support": self._pivot_support_payload(
                item.points,
                source_scale=item.scale,
                pivots_by_scale=pivots_by_scale,
                consensus=pivot_consensus,
            ),
            "prz": self._prz_payload(projection.prz),
            "metrics": {
                "c_ab": projection.c_ab,
                "reciprocal_c_target": projection.reciprocal_c_target,
                "reciprocal_bc_target": projection.reciprocal_bc_target,
            },
            "source_tolerance_used": projection.source_tolerance_used,
            "frontier": True,
        }

    def _shark_payload(
        self,
        item: SharkMatch,
        frame: pd.DataFrame,
        dates: pd.Series,
        pivots_by_scale: dict[int, tuple[Pivot, ...]],
        pivot_consensus: dict,
    ) -> dict[str, Any]:
        evaluation = item.evaluation
        metrics = evaluation.metrics
        completion_index = int(item.points[-1].index)
        return {
            "pattern_id": "shark",
            "schema": "0XABC",
            "direction": item.direction.value,
            "state": item.state.value,
            "scale": item.scale,
            "geometry_score": item.geometry_score,
            "conflict_key": list(item.conflict_key),
            "identity_conflicts": [f"shark@S{item.scale}"],
            "is_primary_identity": True,
            "points": [self._point_payload(point, dates) for point in item.points],
            "pivot_support": self._pivot_support_payload(
                item.points,
                source_scale=item.scale,
                pivots_by_scale=pivots_by_scale,
                consensus=pivot_consensus,
            ),
            "prz": self._prz_payload(evaluation.prz),
            "metrics": {
                "a_0x": metrics.a_0x.value,
                "b_xa": metrics.b_xa.value,
                "c_ab": metrics.c_ab.value,
                "c_0b": metrics.c_0b.value,
            },
            "reaction_targets": {
                "target_50": evaluation.target_50,
                "target_618": evaluation.target_618,
                "reciprocal_abcd": evaluation.reciprocal_abcd_target,
                "bars_to_50": self._bars_to_target(
                    frame,
                    completion_index=completion_index,
                    target=evaluation.target_50,
                    direction=item.direction,
                ),
                "bars_to_618": self._bars_to_target(
                    frame,
                    completion_index=completion_index,
                    target=evaluation.target_618,
                    direction=item.direction,
                ),
                "bars_to_reciprocal_abcd": self._bars_to_target(
                    frame,
                    completion_index=completion_index,
                    target=evaluation.reciprocal_abcd_target,
                    direction=item.direction,
                ),
                "source_note": "Shark 是反应型结构；第三卷优先关注进入 5-0 PRZ 的 50%-61.8% 与 Reciprocal AB=CD 目标。",
            },
        }

    def _shark_forming_payload(
        self,
        item: SharkFormingMatch,
        dates: pd.Series,
        pivots_by_scale: dict[int, tuple[Pivot, ...]],
        pivot_consensus: dict,
    ) -> dict[str, Any]:
        projection = item.projection
        return {
            "pattern_id": "shark",
            "schema": "0XABC",
            "direction": item.direction.value,
            "state": item.state.value,
            "scale": item.scale,
            "geometry_score": item.geometry_score,
            "conflict_key": list(item.conflict_key),
            "identity_conflicts": [f"shark@S{item.scale}"],
            "is_primary_identity": True,
            "points": [self._point_payload(point, dates) for point in item.points],
            "pivot_support": self._pivot_support_payload(
                item.points,
                source_scale=item.scale,
                pivots_by_scale=pivots_by_scale,
                consensus=pivot_consensus,
            ),
            "prz": self._prz_payload(projection.prz),
            "metrics": {
                "a_0x": projection.a_0x,
                "b_xa": projection.b_xa,
            },
            "frontier": True,
        }

    def _five_zero_payload(
        self,
        item: FiveZeroMatch,
        frame: pd.DataFrame,
        dates: pd.Series,
        pivots_by_scale: dict[int, tuple[Pivot, ...]],
        pivot_consensus: dict,
    ) -> dict[str, Any]:
        evaluation = item.evaluation
        metrics = evaluation.metrics
        reaction = audit_completed_reaction(
            frame,
            points=item.points,
            direction=item.direction,
            prz=evaluation.prz,
        )
        return {
            "pattern_id": "five_zero",
            "schema": "FIVE_ZERO",
            "direction": item.direction.value,
            "state": item.state.value,
            "scale": item.scale,
            "geometry_score": item.geometry_score,
            "conflict_key": list(item.conflict_key),
            "identity_conflicts": [f"five_zero@S{item.scale}"],
            "is_primary_identity": True,
            "points": [self._point_payload(point, dates) for point in item.points],
            "pivot_support": self._pivot_support_payload(
                item.points,
                source_scale=item.scale,
                pivots_by_scale=pivots_by_scale,
                consensus=pivot_consensus,
            ),
            "prz": self._prz_payload(evaluation.prz),
            "metrics": {
                "b_xa": metrics.b_xa.value,
                "c_ab": metrics.c_ab.value,
                "d_bc": metrics.d_bc.value,
                "cd_ab": metrics.cd_ab.value,
                "reciprocal_abcd_price": evaluation.reciprocal_abcd_price,
            },
            "completion_class": evaluation.completion_class,
            "reciprocal_inside_execution_band": evaluation.reciprocal_inside_execution_band,
            "reaction_audit": reaction.as_payload(),
        }

    def _five_zero_forming_payload(
        self,
        item: FiveZeroFormingMatch,
        dates: pd.Series,
        pivots_by_scale: dict[int, tuple[Pivot, ...]],
        pivot_consensus: dict,
    ) -> dict[str, Any]:
        projection = item.projection
        return {
            "pattern_id": "five_zero",
            "schema": "FIVE_ZERO",
            "direction": item.direction.value,
            "state": item.state.value,
            "scale": item.scale,
            "geometry_score": item.geometry_score,
            "conflict_key": list(item.conflict_key),
            "identity_conflicts": [f"five_zero@S{item.scale}"],
            "is_primary_identity": True,
            "points": [self._point_payload(point, dates) for point in item.points],
            "pivot_support": self._pivot_support_payload(
                item.points,
                source_scale=item.scale,
                pivots_by_scale=pivots_by_scale,
                consensus=pivot_consensus,
            ),
            "prz": self._prz_payload(projection.prz),
            "metrics": {
                "b_xa": projection.b_xa,
                "c_ab": projection.c_ab,
                "reciprocal_abcd_price": projection.reciprocal_abcd_price,
            },
            "frontier": True,
        }

    def _forming_payload(
        self,
        item: FormingMatch,
        dates: pd.Series,
        conflict_ids: list[str],
        pivots_by_scale: dict[int, tuple[Pivot, ...]],
        pivot_consensus: dict,
    ) -> dict[str, Any]:
        own_id = f"{item.pattern_id}@S{item.scale}"
        c_index = int(item.points[-1].index)
        latest_index = max(len(dates) - 1, 0)
        return {
            "pattern_id": item.pattern_id,
            "schema": "XABCD",
            "direction": item.direction.value,
            "state": item.state.value,
            "scale": item.scale,
            "geometry_score": item.geometry_score,
            "conflict_key": list(item.conflict_key),
            "identity_conflicts": conflict_ids,
            "is_primary_identity": bool(conflict_ids and conflict_ids[0] == own_id),
            "points": [self._point_payload(point, dates) for point in item.points],
            "pivot_support": self._pivot_support_payload(
                item.points,
                source_scale=item.scale,
                pivots_by_scale=pivots_by_scale,
                consensus=pivot_consensus,
            ),
            "prz": self._prz_payload(item.projection.prz),
            "metrics": {
                "b_xa": item.projection.b_xa,
                "c_ab": item.projection.c_ab,
            },
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
        pivots_by_scale: dict[int, tuple[Pivot, ...]] = {
            int(scale): tuple(pivots) for scale, pivots in scan.pivots_by_scale.items()
        }
        pivot_consensus = build_pivot_consensus(pivots_by_scale)
        dates = selected["trade_date"]
        completed_conflicts = self._identity_conflicts(scan.completed)
        forming_conflicts = self._identity_conflicts(scan.forming)

        xabcd_completed = [
            self._completed_payload(
                item,
                selected,
                dates,
                completed_conflicts[item.conflict_key],
                pivots_by_scale,
                pivot_consensus,
            )
            for item in scan.completed
        ]
        abcd_completed = [
            self._abcd_payload(item, selected, dates, pivots_by_scale, pivot_consensus)
            for item in scan.abcd_completed
        ]
        shark_completed = [
            self._shark_payload(item, selected, dates, pivots_by_scale, pivot_consensus)
            for item in scan.shark_completed
        ]
        five_zero_completed = [
            self._five_zero_payload(item, selected, dates, pivots_by_scale, pivot_consensus)
            for item in scan.five_zero_completed
        ]
        completed = sorted(
            [*xabcd_completed, *abcd_completed, *shark_completed, *five_zero_completed],
            key=lambda pattern: (
                -int(pattern["points"][-1]["index"]),
                -float(pattern["geometry_score"]),
                -int(pattern["scale"]),
                str(pattern["pattern_id"]),
            ),
        )[:max_completed]

        xabcd_forming = [
            self._forming_payload(
                item,
                dates,
                forming_conflicts[item.conflict_key],
                pivots_by_scale,
                pivot_consensus,
            )
            for item in scan.forming
        ]
        abcd_forming = [
            self._abcd_forming_payload(item, dates, pivots_by_scale, pivot_consensus)
            for item in scan.abcd_forming
        ]
        shark_forming = [
            self._shark_forming_payload(item, dates, pivots_by_scale, pivot_consensus)
            for item in scan.shark_forming
        ]
        five_zero_forming = [
            self._five_zero_forming_payload(item, dates, pivots_by_scale, pivot_consensus)
            for item in scan.five_zero_forming
        ]
        forming = sorted(
            [*xabcd_forming, *abcd_forming, *shark_forming, *five_zero_forming],
            key=lambda pattern: (
                -int(pattern["points"][-1]["index"]),
                -float(pattern["geometry_score"]),
                -int(pattern["scale"]),
                str(pattern["pattern_id"]),
            ),
        )[:max_forming]

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
            "engine_note": "Carney 几何身份与后续证据严格分层：M/W XABCD、独立 AB=CD、Shark 0XABC 与 5-0 使用独立 schema；geometry_score 与 pivot_support 都不是胜率。Shark 单独审计 50%/61.8% 与 Reciprocal AB=CD 反应目标；其他完成结构可附带 Type-I/Type-II 与 Wilder RSI 证据，但不会自动转化为交易建议。",
        }
