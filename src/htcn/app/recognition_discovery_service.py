from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from htcn.app.source_clock_lifecycle_service import M3SourceClockHarmonicService
from htcn.data.intraday import (
    SUPPORTED_INTRADAY_TIMEFRAMES,
    AkShareIntradayProvider,
    IntradayBars,
    IntradayProvider,
    IntradayProviderError,
    ParquetIntradayCache,
)
from htcn.harmonic.discovery import (
    DISCOVERY_SCALES,
    DiscoveryCandidate,
    discover_frame,
)
from htcn.harmonic.models import Pivot
from htcn.harmonic.pine_r34 import (
    PINE_R34_SCALES,
    PineR34Candidate,
    scan_pine_r34,
)


class RecognitionDiscoveryService(M3SourceClockHarmonicService):
    """Practical recognition layer around the frozen authoritative M3 service.

    Three channels remain explicit:
    - authoritative: frozen canonical identity / Source lifecycle from the parent service;
    - pine_r34: deterministic behavioral parity with the retained standalone Pine R3.4;
    - extended_graph: supplementary HT-CN high-recall XABCD graph discovery.

    Neither discovery channel can mutate canonical identity or M4 evidence.
    """

    def __init__(
        self,
        data_root: str | Path,
        *,
        intraday_provider: IntradayProvider | None = None,
    ) -> None:
        super().__init__(data_root)
        self.intraday_provider = intraday_provider or AkShareIntradayProvider()
        self.intraday_cache = ParquetIntradayCache(
            Path(data_root) / "intraday"
        )

    @staticmethod
    def _date_value(dates: pd.Series, index: int) -> str | None:
        if index < 0 or index >= len(dates):
            return None
        value = dates.iloc[index]
        stamp = pd.Timestamp(value)
        if stamp.hour or stamp.minute or stamp.second:
            return stamp.strftime("%Y-%m-%d %H:%M")
        return stamp.date().isoformat()

    def _graph_discovery_payload(
        self,
        item: DiscoveryCandidate,
        dates: pd.Series,
        pivots_by_scale: dict[int, tuple[Pivot, ...]],
        pivot_consensus: dict,
    ) -> dict[str, Any]:
        return {
            "pattern_id": item.pattern_id,
            "schema": "XABCD",
            "direction": item.direction.value,
            "state": "forming",
            "channel": "discovery",
            "discovery_only": True,
            "geometry_score": item.geometry_score,
            "scale": item.scale,
            "conflict_key": list(item.conflict_key),
            "identity_conflicts": [f"extended_graph:{item.pattern_id}@S{item.scale}"],
            "is_primary_identity": True,
            "points": [self._point_payload(point, dates) for point in item.points],
            "pivot_support": self._pivot_support_payload(
                item.points,
                source_scale=item.scale,
                pivots_by_scale=pivots_by_scale,
                consensus=pivot_consensus,
            ),
            "prz": self._prz_payload(item.prz),
            "metrics": {
                "b_xa": item.b_xa,
                "c_ab": item.c_ab,
            },
            "source_tolerance_used": item.source_tolerance_used,
            "bars_since_c": item.bars_since_c,
            "frontier": False,
            "discovery": {
                "source": "extended_graph",
                "behavioral_baseline": False,
                "authoritative_identity": False,
                "path_kind": item.path_kind,
                "skipped_pivots": item.skipped_pivots,
                "known_from_bar": item.known_from_bar,
                "prz_status": item.prz_status,
                "first_prz_test_bar": item.first_prz_test_bar,
                "c_family_target": item.c_family_target,
                "c_family_relative_error": item.c_family_relative_error,
                "source_family_aligned": item.source_family_aligned,
                "distance_to_source_prz_xa": item.distance_to_source_prz_xa,
                "research_only": False,
                "qualified": True,
                "precise": True,
                "projected_label": "D",
                "mutates_source_identity": False,
                "owns_lifecycle": False,
                "fabricates_d": False,
            },
        }

    def _pine_payload(
        self,
        item: PineR34Candidate,
        dates: pd.Series,
        *,
        latest_close: float,
    ) -> dict[str, Any]:
        points = []
        for label, node in zip(item.source_labels, item.source_nodes, strict=True):
            payload: dict[str, Any] = {
                "label": label,
                "index": node.index,
                "price": node.price,
            }
            trade_date = self._date_value(dates, node.index)
            if trade_date is not None:
                payload["trade_date"] = trade_date
            points.append(payload)

        distance = 0.0
        if latest_close < item.prz_low:
            distance = item.prz_low - latest_close
        elif latest_close > item.prz_high:
            distance = latest_close - item.prz_high

        components = [
            {
                "name": name,
                "price_low": value,
                "price_high": value,
                "ratio_low": 0.0,
                "ratio_high": 0.0,
            }
            for name, value in (
                ("R3.4 M1", item.m1),
                ("R3.4 M2", item.m2),
                ("R3.4 M3", item.m3),
            )
        ]
        return {
            "pattern_id": item.pattern_id,
            "schema": item.schema,
            "direction": "bullish" if item.direction == 1 else "bearish",
            "state": "forming",
            "channel": "discovery",
            "discovery_only": True,
            # No opaque pseudo-probability is invented for the behavioral channel.
            "geometry_score": 0.0,
            "scale": item.scale,
            "conflict_key": list(item.conflict_key),
            "identity_conflicts": [f"pine_r34:{item.pattern_id}@S{item.scale}"],
            "is_primary_identity": True,
            "points": points,
            "pivot_support": [],
            "prz": {
                "price_low": item.prz_low,
                "price_high": item.prz_high,
                "width": item.prz_high - item.prz_low,
                "component_price_low": min(item.m1, item.m2, item.m3),
                "component_price_high": max(item.m1, item.m2, item.m3),
                "components": components,
            },
            "metrics": {
                "m1": item.m1,
                "m2": item.m2,
                "m3": item.m3,
                "structural_limit": item.structural_limit,
                "distance_to_prz": distance,
                "distance_to_prz_atr": (
                    item.current_distance_atr
                    if item.current_distance_atr is not None
                    else distance / max(item.atr_at_birth, 1e-12)
                ),
                "distance_to_prz_pct": item.current_distance_pct,
                "source_age": item.source_age,
                "observable": item.observable,
                "monitoring_rank": item.monitoring_rank,
            },
            "source_tolerance_used": False,
            "bars_since_c": max(0, len(dates) - 1 - item.source_nodes[-1].index),
            "frontier": False,
            "discovery": {
                "source": "pine_r34",
                "behavioral_baseline": True,
                "authoritative_identity": False,
                "path_kind": "pine_r34",
                "skipped_pivots": 0,
                "known_from_bar": item.born_bar,
                "prz_status": "tested" if item.first_test_bar is not None else "projected",
                "first_prz_test_bar": item.first_test_bar,
                "c_family_target": item.c_ideal,
                "c_family_relative_error": item.c_error,
                "source_family_aligned": item.precise,
                "distance_to_source_prz_xa": distance / max(item.reference_scale, 1e-12),
                "research_only": item.research_only,
                "qualified": item.qualified,
                "precise": item.precise,
                "observable": item.observable,
                "monitoring_rank": item.monitoring_rank,
                "recently_tested": item.recently_tested,
                "projected_label": item.projected_label,
                "structural_limit": item.structural_limit,
                "pine_source_sha256": (
                    "84e1eb2267c9b80891e0ffb64a6d4abf5712fc5e756be81815e536f2fca4c3f5"
                ),
                "mutates_source_identity": False,
                "owns_lifecycle": False,
                "fabricates_d": False,
            },
        }

    def _append_discovery(
        self,
        analysis: dict[str, Any],
        frame: pd.DataFrame,
        *,
        max_discovery: int,
        include_extended_graph: bool = True,
    ) -> dict[str, Any]:
        if frame.empty:
            analysis["discovery"] = []
            analysis["discovery_scales"] = list(PINE_R34_SCALES)
            analysis["discovery_pivot_counts"] = {}
            analysis["recognition_diagnostics"] = {
                "authoritative_completed": len(analysis.get("completed") or []),
                "authoritative_forming": len(analysis.get("forming") or []),
                "pine_r34_live": 0,
                "extended_graph_candidates": 0,
                "discovery_candidates": 0,
            }
            return analysis

        date_column = "trade_time" if "trade_time" in frame.columns else "trade_date"
        dates = pd.Series(frame[date_column])
        latest_close = float(frame.iloc[-1]["close"])
        pine_scan = scan_pine_r34(frame)
        pine_items = [
            self._pine_payload(item, dates, latest_close=latest_close)
            for item in pine_scan.monitoring_candidates
        ]

        authoritative_keys: set[tuple[str, tuple[int, ...]]] = set()
        for pattern in [
            *(analysis.get("completed") or []),
            *(analysis.get("forming") or []),
        ]:
            points = pattern.get("points") or []
            if not points:
                continue
            authoritative_keys.add(
                (
                    str(pattern.get("pattern_id")),
                    tuple(int(point["index"]) for point in points[:-1] if "index" in point)
                    if pattern.get("state") == "completed"
                    else tuple(int(point["index"]) for point in points if "index" in point),
                )
            )

        pine_items = [
            payload
            for payload in pine_items
            if (
                str(payload["pattern_id"]),
                tuple(int(value) for value in payload["conflict_key"]),
            )
            not in authoritative_keys
        ]

        graph_items: list[dict[str, Any]] = []
        graph_diagnostics: dict[str, int] = {}
        graph_pivots: dict[int, tuple[Pivot, ...]] = {}
        if include_extended_graph:
            graph_scan = discover_frame(
                frame,
                scales=DISCOVERY_SCALES,
                max_candidates=max_discovery,
            )
            graph_pivots = {
                int(scale): tuple(pivots)
                for scale, pivots in graph_scan.pivots_by_scale.items()
            }
            pine_keys = {
                (
                    str(payload["pattern_id"]),
                    tuple(int(value) for value in payload["conflict_key"]),
                )
                for payload in pine_items
            }
            graph_items = [
                self._graph_discovery_payload(
                    item,
                    dates,
                    graph_pivots,
                    graph_scan.pivot_consensus,
                )
                for item in graph_scan.candidates
                if (item.pattern_id, item.conflict_key) not in authoritative_keys
                and (item.pattern_id, item.conflict_key) not in pine_keys
            ]
            graph_diagnostics = graph_scan.diagnostics

        discovery = [*pine_items, *graph_items][:max_discovery]
        analysis["discovery"] = discovery
        analysis["discovery_scales"] = list(PINE_R34_SCALES)
        analysis["discovery_pivot_counts"] = {
            str(scale): len(pivots)
            for scale, pivots in pine_scan.pivots_by_scale.items()
        }
        analysis["recognition_diagnostics"] = {
            "authoritative_completed": len(analysis.get("completed") or []),
            "authoritative_forming": len(analysis.get("forming") or []),
            "pine_r34_live": int(pine_scan.diagnostics.get("live_candidate_count") or 0),
            "pine_r34_monitoring": len(pine_items),
            "pine_r34_hidden_remote": int(pine_scan.diagnostics.get("hidden_remote_count") or 0),
            "extended_graph_candidates": len(graph_items),
            "discovery_candidates": len(discovery),
            **{f"graph_{key}": value for key, value in graph_diagnostics.items()},
        }
        analysis["pine_r34_diagnostics"] = pine_scan.diagnostics
        return analysis

    def analyze(
        self,
        *args,
        max_discovery: int = 80,
        **kwargs,
    ) -> dict[str, Any]:
        analysis = super().analyze(*args, **kwargs)
        bars = analysis.get("bars") or []
        frame = pd.DataFrame(bars)
        analysis["timeframe"] = "1d"
        analysis["data_provenance"] = {
            "kind": "canonical_daily",
            "price_mode": analysis.get("price_mode"),
            "price_basis_id": analysis.get("price_basis_id"),
            "last_trade_time": analysis.get("last_trade_date"),
        }
        analysis = self._append_discovery(
            analysis,
            frame,
            max_discovery=max_discovery,
            include_extended_graph=True,
        )
        analysis["engine_note"] = (
            str(analysis.get("engine_note") or "")
            + " CR-0089 recognition：Pine R3.4 行为基线(5/10/20)与 extended_graph 分离；"
            "前者用于同数据行为对照，后者只补充高召回 XABCD。两者都不拥有 Source lifecycle、"
            "不写 M4 evidence、不虚构完成节点，也不改变 canonical identity。"
        ).strip()
        return analysis

    @staticmethod
    def _intraday_window_days(timeframe: str, bars: int) -> int:
        bars_per_day = 16 if timeframe == "15m" else 4
        trading_days = max(20, (bars + bars_per_day - 1) // bars_per_day)
        return min(900, max(45, int(trading_days * 7 / 5) + 30))

    @staticmethod
    def _cache_fresh(cached: IntradayBars, timeframe: str) -> bool:
        now = pd.Timestamp.now(tz="Asia/Shanghai")
        fetched = pd.Timestamp(cached.fetched_at)
        if fetched.tzinfo is None:
            fetched = fetched.tz_localize("Asia/Shanghai")
        else:
            fetched = fetched.tz_convert("Asia/Shanghai")
        minutes = 10 if timeframe == "15m" else 20
        return (now - fetched).total_seconds() <= minutes * 60

    def _load_intraday(
        self,
        instrument_id: str,
        *,
        timeframe: str,
        bars: int,
        force_refresh: bool,
    ) -> tuple[IntradayBars, str | None]:
        cached = self.intraday_cache.read(instrument_id, timeframe)
        if (
            not force_refresh
            and cached is not None
            and len(cached.frame) >= min(bars, 80)
            and self._cache_fresh(cached, timeframe)
        ):
            return cached, None

        now = datetime.now(tz=ZoneInfo("Asia/Shanghai")).replace(tzinfo=None)
        start = now - timedelta(days=self._intraday_window_days(timeframe, bars))
        try:
            fetched = self.intraday_provider.fetch(
                instrument_id,
                timeframe=timeframe,
                start=start,
                end=now,
                adjust="qfq",
            )
            if fetched.frame.empty:
                raise IntradayProviderError("provider returned no intraday rows")
            self.intraday_cache.write(fetched)
            return fetched, None
        except Exception as exc:
            if cached is None or cached.frame.empty:
                if isinstance(exc, IntradayProviderError):
                    raise
                raise IntradayProviderError(str(exc)) from exc
            return cached, (
                f"分钟行情刷新失败，使用缓存 {cached.last_trade_time}: "
                f"{type(exc).__name__}: {exc}"
            )

    def analyze_intraday(
        self,
        instrument_id: str,
        *,
        timeframe: str,
        bars: int = 720,
        max_discovery: int = 80,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        if timeframe not in SUPPORTED_INTRADAY_TIMEFRAMES:
            raise ValueError(f"unsupported intraday timeframe: {timeframe}")
        market, warning = self._load_intraday(
            instrument_id,
            timeframe=timeframe,
            bars=bars,
            force_refresh=force_refresh,
        )
        selected = market.frame.tail(bars).reset_index(drop=True)
        if selected.empty:
            raise IntradayProviderError(
                f"no cached/fetched {timeframe} bars for {instrument_id}"
            )

        payload_bars: list[dict[str, Any]] = []
        for index, row in selected.iterrows():
            stamp = pd.Timestamp(row["trade_time"])
            shanghai_wall_clock = (
                stamp
                if stamp.tzinfo is None
                else stamp.tz_convert("Asia/Shanghai").tz_localize(None)
            )
            # lightweight-charts renders numeric timestamps in UTC. Encode the Shanghai
            # wall clock as UTC so its visible 14:00 label remains 14:00, while provenance
            # continues to state Asia/Shanghai explicitly.
            chart_time = shanghai_wall_clock.tz_localize("UTC")
            payload_bars.append(
                {
                    "index": int(index),
                    "trade_date": shanghai_wall_clock.strftime("%Y-%m-%d %H:%M"),
                    "time": int(chart_time.timestamp()),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]),
                }
            )

        first = pd.Timestamp(selected["trade_time"].iloc[0]).strftime("%Y-%m-%d %H:%M")
        last = pd.Timestamp(selected["trade_time"].iloc[-1]).strftime("%Y-%m-%d %H:%M")
        analysis: dict[str, Any] = {
            "instrument_id": instrument_id,
            "timeframe": timeframe,
            "price_mode": market.adjustment,
            "price_basis_id": f"intraday:{market.provider}:{market.adjustment}:{timeframe}",
            "warning": warning,
            "bars_requested": bars,
            "bars_returned": len(selected),
            "first_trade_date": first,
            "last_trade_date": last,
            "scales": [],
            "bars": payload_bars,
            "completed": [],
            "forming": [],
            "pivot_counts": {},
            "type_i_t5_events": [],
            "data_provenance": {
                "kind": "intraday_research",
                "provider": market.provider,
                "timeframe": timeframe,
                "adjustment": market.adjustment,
                "fetched_at": pd.Timestamp(market.fetched_at).isoformat(),
                "first_trade_time": first,
                "last_trade_time": last,
                "cache_warning": warning,
                "authoritative_source_lifecycle": False,
            },
            "engine_note": (
                "分钟级研究通道：Pine R3.4 行为识别从同一组 15/60 分钟 OHLC 顺序重放；"
                "不继承日线 Source lifecycle，不产生 M4 证据或交易执行。"
            ),
        }
        analysis_frame = selected.rename(columns={"trade_time": "trade_date"})
        return self._append_discovery(
            analysis,
            analysis_frame,
            max_discovery=max_discovery,
            include_extended_graph=True,
        )
