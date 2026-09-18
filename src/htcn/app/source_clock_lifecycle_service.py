from __future__ import annotations

from typing import Any

import pandas as pd

from htcn.app.a_share_execution_context import (
    build_a_share_execution_context,
    load_daily_trading_metadata,
    load_security_metadata,
)
from htcn.app.source_aligned_service import SourceAlignedHarmonicService
from htcn.app.market_context import build_core_market_context
from htcn.app.sector_context import build_industry_context
from htcn.app.concept_context import build_concept_context
from htcn.app.context_integrity import build_context_integrity
from htcn.harmonic.execution import SourceExecutionAudit
from htcn.harmonic.models import PatternDirection
from htcn.harmonic.rsi_bamm_confluence import observe_source_execution_for_match
from htcn.harmonic.source_lifecycle import derive_source_lifecycle, unavailable_source_lifecycle


class M3SourceClockHarmonicService(SourceAlignedHarmonicService):
    """M3 product adapter that promotes the observable source clock to canonical lifecycle.

    M2.31 source-fidelity objects stay unchanged. This adapter adds product-facing
    ``source_lifecycle`` and A-share execution-context payloads. Historical
    ``reaction_audit`` remains diagnostic compatibility only and never drives current state.
    """

    @staticmethod
    def _completed_source_lifecycle_payload(item: Any, frame: pd.DataFrame) -> dict[str, Any]:
        current_bar = max(len(frame) - 1, 0)
        audit = observe_source_execution_for_match(frame, item)
        if audit is None:
            return unavailable_source_lifecycle(
                current_bar=current_bar,
                reason="completed_match_source_clock_not_reconstructable_from_pre_terminal_observable_state",
            ).as_payload()
        return derive_source_lifecycle(frame, audit).as_payload()

    @staticmethod
    def _audit_from_clock(clock: dict[str, Any], pattern: dict[str, Any]) -> SourceExecutionAudit | None:
        required = {
            "signal_bar",
            "state",
            "source_prz_available",
            "source_prz_low",
            "source_prz_high",
            "first_prz_entry_bar",
            "terminal_bar",
            "terminal_price",
            "execution_start_bar",
            "pez_low",
            "pez_high",
            "target_382",
            "target_618",
        }
        if not required.issubset(clock):
            return None
        return SourceExecutionAudit(
            signal_bar=int(clock["signal_bar"]),
            direction=PatternDirection(str(pattern["direction"])),
            state=str(clock["state"]),
            source_prz_available=bool(clock["source_prz_available"]),
            source_prz_low=(None if clock["source_prz_low"] is None else float(clock["source_prz_low"])),
            source_prz_high=(None if clock["source_prz_high"] is None else float(clock["source_prz_high"])),
            first_prz_entry_bar=(
                None if clock["first_prz_entry_bar"] is None else int(clock["first_prz_entry_bar"])
            ),
            terminal_bar=None if clock["terminal_bar"] is None else int(clock["terminal_bar"]),
            terminal_price=None if clock["terminal_price"] is None else float(clock["terminal_price"]),
            execution_start_bar=(
                None if clock["execution_start_bar"] is None else int(clock["execution_start_bar"])
            ),
            pez_low=None if clock["pez_low"] is None else float(clock["pez_low"]),
            pez_high=None if clock["pez_high"] is None else float(clock["pez_high"]),
            target_382=None if clock["target_382"] is None else float(clock["target_382"]),
            target_618=None if clock["target_618"] is None else float(clock["target_618"]),
        )

    @classmethod
    def _execution_clock_from_forming_payload(
        cls,
        pattern: dict[str, Any],
        frame: pd.DataFrame,
    ) -> dict[str, Any] | None:
        clock = super()._execution_clock_from_forming_payload(pattern, frame)
        if clock is None:
            return None
        audit = cls._audit_from_clock(clock, pattern)
        if audit is None:
            clock["lifecycle"] = unavailable_source_lifecycle(
                current_bar=max(len(frame) - 1, 0),
                reason=f"forming_execution_clock_unavailable:{clock.get('state', 'unknown')}",
            ).as_payload()
        else:
            clock["lifecycle"] = derive_source_lifecycle(frame, audit).as_payload()
        return clock

    def _completed_payload(self, *args, **kwargs) -> dict[str, Any]:
        payload = super()._completed_payload(*args, **kwargs)
        item = args[0] if args else kwargs["item"]
        frame = args[1] if len(args) > 1 else kwargs["frame"]
        payload["source_lifecycle"] = self._completed_source_lifecycle_payload(item, frame)
        return payload

    def _abcd_payload(self, *args, **kwargs) -> dict[str, Any]:
        payload = super()._abcd_payload(*args, **kwargs)
        item = args[0] if args else kwargs["item"]
        frame = args[1] if len(args) > 1 else kwargs["frame"]
        payload["source_lifecycle"] = self._completed_source_lifecycle_payload(item, frame)
        return payload

    def _shark_payload(self, *args, **kwargs) -> dict[str, Any]:
        payload = super()._shark_payload(*args, **kwargs)
        item = args[0] if args else kwargs["item"]
        frame = args[1] if len(args) > 1 else kwargs["frame"]
        payload["source_lifecycle"] = self._completed_source_lifecycle_payload(item, frame)
        return payload

    def _five_zero_payload(self, *args, **kwargs) -> dict[str, Any]:
        payload = super()._five_zero_payload(*args, **kwargs)
        frame = args[1] if len(args) > 1 else kwargs["frame"]
        payload["source_lifecycle"] = unavailable_source_lifecycle(
            current_bar=max(len(frame) - 1, 0),
            reason="five_zero_production_quarantine",
        ).as_payload()
        return payload

    def analyze(self, *args, **kwargs) -> dict[str, Any]:
        analysis = super().analyze(*args, **kwargs)
        for pattern in analysis.get("forming") or []:
            clock = pattern.get("execution_clock")
            if isinstance(clock, dict) and isinstance(clock.get("lifecycle"), dict):
                pattern["source_lifecycle"] = clock["lifecycle"]
            elif pattern.get("schema") == "FIVE_ZERO":
                pattern["source_lifecycle"] = unavailable_source_lifecycle(
                    current_bar=max(len(analysis.get("bars") or []) - 1, 0),
                    reason="five_zero_production_quarantine",
                ).as_payload()

        frame = pd.DataFrame(analysis.get("bars") or [])
        instrument_id = str(analysis["instrument_id"])
        catalog_path = self.data_root / "catalog.duckdb"
        metadata = load_security_metadata(catalog_path, instrument_id)

        as_of = None
        if not frame.empty and "trade_date" in frame.columns:
            stamp = pd.to_datetime(frame["trade_date"].iloc[-1], errors="coerce")
            if not pd.isna(stamp):
                as_of = stamp.date()
        daily_event = load_daily_trading_metadata(catalog_path, instrument_id, as_of)

        execution_context = build_a_share_execution_context(
            frame,
            instrument_id=instrument_id,
            metadata=metadata,
            daily_event=daily_event,
        ).as_payload()
        analysis["a_share_execution_context"] = execution_context
        market_context = build_core_market_context(
            frame,
            benchmark_root=self.data_root / "benchmarks",
        ).as_payload()
        sector_context = build_industry_context(
            catalog_path=catalog_path,
            instrument_id=instrument_id,
            instrument_frame=frame,
            as_of=as_of,
        ).as_payload()
        concept_context = build_concept_context(
            catalog_path=catalog_path,
            instrument_id=instrument_id,
            instrument_frame=frame,
            as_of=as_of,
        ).as_payload()
        analysis["market_context"] = market_context
        analysis["sector_context"] = sector_context
        analysis["concept_context"] = concept_context
        analysis["context_integrity"] = build_context_integrity(
            as_of_trade_date=None if as_of is None else as_of.isoformat(),
            execution_context=execution_context,
            market_context=market_context,
            sector_context=sector_context,
            concept_context=concept_context,
        ).as_payload()
        for pattern in [*(analysis.get("completed") or []), *(analysis.get("forming") or [])]:
            pattern["a_share_execution_context"] = execution_context

        analysis["source_lifecycle_contract"] = {
            "version": 3,
            "canonical_clock": "source_terminal_price_bar",
            "current_state_field": "*.source_lifecycle.state",
            "retrospective_reaction_audit_role": "diagnostic_compatibility_only",
            "geometry_terminal_promotes_live_state": False,
            "strict_type_ii_full_retest": True,
            "type_i_early_window_bars": 5,
            "type_i_early_confirmation_objective": "38.2_percent_reaction_target",
            "bamm_role": "evidence_only",
            "a_share_execution_context_field": "a_share_execution_context",
            "a_share_execution_context_role": "tradability_and_volatility_context_only",
            "market_context_field": "market_context",
            "market_context_role": "benchmark_and_relative_strength_evidence_only",
            "market_context_may_change_harmonic_identity": False,
            "market_context_may_change_source_raw_prz": False,
            "market_context_owns_lifecycle": False,
            "sector_context_field": "sector_context",
            "sector_context_role": "industry_breadth_and_relative_strength_evidence_only",
            "sector_context_may_change_harmonic_identity": False,
            "sector_context_may_change_source_raw_prz": False,
            "sector_context_owns_lifecycle": False,
            "concept_context_field": "concept_context",
            "concept_context_role": "multi_membership_theme_relative_strength_evidence_only",
            "concept_context_may_change_harmonic_identity": False,
            "concept_context_may_change_source_raw_prz": False,
            "concept_context_owns_lifecycle": False,
            "context_integrity_field": "context_integrity",
            "context_integrity_role": "freshness_coverage_conflict_diagnostics_not_score",
            "daily_event_metadata_table": "security_daily_event",
            "daily_event_complete_required_to_resolve_special_exceptions": True,
            "execution_context_may_change_harmonic_identity": False,
            "execution_context_may_change_source_raw_prz": False,
            "mutates_harmonic_identity": False,
            "mutates_source_raw_prz": False,
            "no_backdating": True,
        }
        analysis["engine_note"] = (
            str(analysis.get("engine_note") or "")
            + " M3 Phase 1：工作台 current lifecycle 已升级为 Source Terminal Price Bar 时钟；"
            "reaction_audit 仅保留后验诊断兼容，不得覆盖 source_lifecycle。"
            " M3 Phase 3：A股 T+1、涨跌幅制度、ATR/振幅/量比进入独立 execution context；"
            "该上下文只能解释可交易性与波动风险，禁止改写 harmonic identity 或 Source Raw PRZ。"
            " M3 Phase 3.1：当日停复牌/无涨跌幅/特殊限制只接受显式 daily-event metadata；"
            "缺失或不完整时继续 fail-safe，禁止把板块规则冒充当日精确制度。"
            " M3 Phase 3.2：科创50/创业板/沪深300/上证指数只作为市场与相对强弱证据；"
            "它们不拥有 lifecycle，也不得改写 identity 或 Source Raw PRZ。"
            " M3 Phase 3.3：行业映射来自可审计成分表，行业强弱/广度/量能由本地 M1 成分股重算；"
            "映射冲突时 fail-safe，不擅自选行业，也不改写谐波身份。"
            " M3 Phase 3.4：概念/题材天然多对多，完整保留 membership；"
            "概念排序仅按透明 5 日中位收益展示，不形成综合题材评分。"
            " M3 Phase 3.5：上下文完整性总览只报告 current/partial/stale/missing/conflicted 等状态；"
            "它不是分数，不拥有 lifecycle，也不产生买卖结论。"
        ).strip()
        return analysis
