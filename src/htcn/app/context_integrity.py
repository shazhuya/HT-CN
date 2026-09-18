from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True, slots=True)
class ContextLayerIntegrity:
    layer: str
    state: str
    evidence_date: str | None
    source: str | None
    coverage: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class ContextIntegrity:
    as_of_trade_date: str | None
    summary_state: str
    layers: tuple[ContextLayerIntegrity, ...]
    is_score: bool = False
    mutates_harmonic_identity: bool = False
    mutates_source_raw_prz: bool = False
    owns_lifecycle: bool = False

    def as_payload(self) -> dict[str, object]:
        return {
            "as_of_trade_date": self.as_of_trade_date,
            "summary_state": self.summary_state,
            "layers": [asdict(item) for item in self.layers],
            "is_score": self.is_score,
            "mutates_harmonic_identity": self.mutates_harmonic_identity,
            "mutates_source_raw_prz": self.mutates_source_raw_prz,
            "owns_lifecycle": self.owns_lifecycle,
        }


def _parse(value: object) -> date | None:
    if value in {None, ""}:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _dated_state(
    *,
    layer: str,
    as_of: date | None,
    evidence_date: date | None,
    source: str | None,
    coverage: str | None,
    current_reason: str,
) -> ContextLayerIntegrity:
    if evidence_date is None:
        return ContextLayerIntegrity(
            layer, "missing", None, source, coverage,
            "缺少可对齐到分析日的证据日期。"
        )
    if as_of is not None and evidence_date > as_of:
        return ContextLayerIntegrity(
            layer, "future_observation", evidence_date.isoformat(), source, coverage,
            "证据观测日晚于分析日，禁止回填历史分析。"
        )
    if as_of is not None and evidence_date < as_of:
        return ContextLayerIntegrity(
            layer, "stale", evidence_date.isoformat(), source, coverage,
            f"最近证据停留在 {evidence_date.isoformat()}，早于分析日。"
        )
    return ContextLayerIntegrity(
        layer, "current", evidence_date.isoformat(), source, coverage, current_reason
    )


def build_context_integrity(
    *,
    as_of_trade_date: str | None,
    execution_context: dict[str, Any] | None,
    market_context: dict[str, Any] | None,
    sector_context: dict[str, Any] | None,
    concept_context: dict[str, Any] | None,
) -> ContextIntegrity:
    as_of = _parse(as_of_trade_date)
    layers: list[ContextLayerIntegrity] = []

    execution = execution_context or {}
    if not execution_context:
        layers.append(ContextLayerIntegrity(
            "execution", "missing", None, None, None,
            "A股执行上下文 payload 缺失。"
        ))
    elif execution.get("bse_deferred"):
        layers.append(ContextLayerIntegrity(
            "execution", "missing", as_of_trade_date, None, None,
            "北交所执行规则当前 deferred。"
        ))
    elif _parse(execution.get("as_of_trade_date")) is not None and as_of is not None and _parse(execution.get("as_of_trade_date")) != as_of:
        execution_date = _parse(execution.get("as_of_trade_date"))
        assert execution_date is not None
        layers.append(ContextLayerIntegrity(
            "execution",
            "future_observation" if execution_date > as_of else "stale",
            execution_date.isoformat(),
            execution.get("daily_event_source") or execution.get("metadata_source"),
            None,
            "执行上下文交易日与分析交易日不一致。"
        ))
    elif execution.get("special_event_exceptions_unresolved"):
        layers.append(ContextLayerIntegrity(
            "execution", "unresolved", as_of_trade_date,
            execution.get("daily_event_source") or execution.get("metadata_source"),
            "partial",
            "T+1/板块规则可用，但当日特殊事件例外没有完整来源证明。"
        ))
    else:
        layers.append(ContextLayerIntegrity(
            "execution", "current", as_of_trade_date,
            execution.get("daily_event_source") or execution.get("metadata_source"),
            "complete",
            "执行约束已对齐分析交易日，且特殊事件例外已显式解析。"
        ))

    market = market_context or {}
    benchmarks = list(market.get("benchmarks") or [])
    available = [item for item in benchmarks if item.get("available")]
    if not available:
        layers.append(ContextLayerIntegrity(
            "market", "missing", None, None, "0/4",
            "四大核心指数本地数据均不可用。"
        ))
    elif len(available) < len(benchmarks) or market.get("status") != "complete":
        dates = [_parse(item.get("as_of_trade_date")) for item in available]
        latest = max((item for item in dates if item is not None), default=None)
        layers.append(ContextLayerIntegrity(
            "market", "partial",
            None if latest is None else latest.isoformat(),
            "local_core_benchmarks",
            f"{len(available)}/{len(benchmarks) or 4}",
            "核心指数覆盖不完整，不把部分指数冒充全市场环境。"
        ))
    else:
        dates = [_parse(item.get("as_of_trade_date")) for item in available]
        valid_dates = [item for item in dates if item is not None]
        earliest = min(valid_dates) if valid_dates else None
        latest = max(valid_dates) if valid_dates else None
        if as_of is not None and latest is not None and latest > as_of:
            state = "future_observation"
            reason = "至少一个核心指数证据日晚于分析日。"
        elif as_of is not None and (earliest is None or earliest < as_of):
            state = "stale"
            reason = "至少一个核心指数尚未更新到分析交易日。"
        elif len(valid_dates) != len(available):
            state = "partial"
            reason = "至少一个核心指数缺少可审计证据日期。"
        else:
            state = "current"
            reason = "四大核心指数均对齐分析交易日。"
        layers.append(ContextLayerIntegrity(
            "market", state,
            None if earliest is None else earliest.isoformat(),
            "local_core_benchmarks", f"{len(available)}/{len(benchmarks)}", reason
        ))

    sector = sector_context or {}
    sector_status = str(sector.get("status") or "membership_unavailable")
    if sector_status == "membership_ambiguous":
        layers.append(ContextLayerIntegrity(
            "industry", "conflicted", sector.get("mapping_observed_on"),
            sector.get("mapping_source"), None,
            "同一来源返回多个行业，系统拒绝自动选择。"
        ))
    elif sector_status == "mapping_after_as_of":
        layers.append(ContextLayerIntegrity(
            "industry", "future_observation", sector.get("mapping_observed_on"),
            sector.get("mapping_source"), None,
            "行业映射观测日晚于分析日。"
        ))
    elif sector_status != "resolved":
        layers.append(ContextLayerIntegrity(
            "industry",
            "partial" if sector.get("sector_name") else "missing",
            sector.get("snapshot_trade_date") or sector.get("mapping_observed_on"),
            sector.get("mapping_source"), None,
            f"行业层状态：{sector_status}。"
        ))
    else:
        layers.append(_dated_state(
            layer="industry",
            as_of=as_of,
            evidence_date=_parse(sector.get("snapshot_trade_date")),
            source=sector.get("mapping_source"),
            coverage=(
                None if sector.get("total_member_count") is None
                else f"{sector.get('return_20d_count')}/{sector.get('total_member_count')}"
            ),
            current_reason="行业本地成分聚合已对齐分析交易日。",
        ))

    concept = concept_context or {}
    concept_status = str(concept.get("status") or "membership_unavailable")
    if concept_status == "mapping_after_as_of":
        layers.append(ContextLayerIntegrity(
            "concept", "future_observation", concept.get("mapping_observed_on"),
            concept.get("mapping_source"),
            f"0/{concept.get('membership_count', 0)}",
            "概念映射观测日晚于分析日。"
        ))
    elif concept_status in {"membership_unavailable", "mapped_snapshots_unavailable"}:
        layers.append(ContextLayerIntegrity(
            "concept", "missing" if concept_status == "membership_unavailable" else "partial",
            concept.get("mapping_observed_on"), concept.get("mapping_source"),
            f"{concept.get('resolved_count', 0)}/{concept.get('membership_count', 0)}",
            f"概念层状态：{concept_status}。"
        ))
    else:
        items = list(concept.get("concepts") or [])
        dates = [_parse(item.get("snapshot_trade_date")) for item in items if item.get("snapshot_trade_date")]
        resolved = int(concept.get("resolved_count") or 0)
        total = int(concept.get("membership_count") or 0)
        if concept_status == "partial" or resolved < total:
            state = "partial"
            reason = "仅部分概念已有本地快照。"
        elif as_of is not None and any(item > as_of for item in dates):
            state = "future_observation"
            reason = "至少一个概念快照日晚于分析日。"
        elif as_of is not None and (not dates or any(item < as_of for item in dates)):
            state = "stale"
            reason = "至少一个概念快照未更新到分析交易日。"
        else:
            state = "current"
            reason = "全部已映射概念快照均对齐分析交易日。"
        evidence = min(dates).isoformat() if dates else concept.get("mapping_observed_on")
        layers.append(ContextLayerIntegrity(
            "concept", state, evidence, concept.get("mapping_source"),
            f"{resolved}/{total}", reason
        ))

    summary_state = (
        "all_current"
        if layers and all(item.state == "current" for item in layers)
        else "issues_present"
    )
    return ContextIntegrity(
        as_of_trade_date=as_of_trade_date,
        summary_state=summary_state,
        layers=tuple(layers),
    )
