from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class DecisionNarrative:
    lifecycle_state: str
    action_state: str
    current_position: str
    first_watch: str
    next_watch: str
    upgrade_blocker: str
    next_key_price: float | None
    next_key_price_role: str | None
    execution_context_gate: str
    context_cautions: tuple[str, ...]
    is_trade_instruction: bool = False
    uses_score: bool = False
    mutates_harmonic_identity: bool = False
    mutates_source_raw_prz: bool = False
    owns_lifecycle: bool = False

    def as_payload(self) -> dict[str, object]:
        return {
            "lifecycle_state": self.lifecycle_state,
            "action_state": self.action_state,
            "current_position": self.current_position,
            "first_watch": self.first_watch,
            "next_watch": self.next_watch,
            "upgrade_blocker": self.upgrade_blocker,
            "next_key_price": self.next_key_price,
            "next_key_price_role": self.next_key_price_role,
            "execution_context_gate": self.execution_context_gate,
            "context_cautions": list(self.context_cautions),
            "is_trade_instruction": self.is_trade_instruction,
            "uses_score": self.uses_score,
            "mutates_harmonic_identity": self.mutates_harmonic_identity,
            "mutates_source_raw_prz": self.mutates_source_raw_prz,
            "owns_lifecycle": self.owns_lifecycle,
        }


_ACTION = {
    "source_clock_unavailable": "evidence_insufficient",
    "source_prz_unresolved": "evidence_insufficient",
    "approaching_source_prz": "waiting",
    "entered_source_prz": "waiting",
    "waiting_terminal": "waiting",
    "source_terminal_complete": "reaction_observation",
    "t_plus_1": "reaction_observation",
    "type_i_early_reaction": "reaction_observation",
    "type_i_confirmed": "execution_evaluation",
    "type_i_failed": "waiting",
    "reaction_only": "waiting",
    "type_ii_retest_forming": "waiting",
    "type_ii_terminal": "execution_evaluation",
    "reversal_evidence": "execution_evaluation",
    "invalidated": "evidence_insufficient",
}


def _texts(state: str) -> tuple[str, str, str, str]:
    if state == "source_clock_unavailable":
        return (
            "Source execution clock 无法从可观察历史重建。",
            "先解决 Source clock 可观察性；不要退回 historical D/C 冒充实时状态。",
            "只有 Source clock 可重建后，才继续判断 PRZ / T-Bar。",
            "Source clock 不可用时，禁止升级为执行评估。",
        )
    if state == "source_prz_unresolved":
        return (
            "Source Raw PRZ 尚未冻结。",
            "先解决 Source PRZ；HT-CN 收敛核心不能替代 Source Raw PRZ。",
            "PRZ 冻结后再看进入、Terminal Price Bar 与 PEZ。",
            "Source Raw PRZ 未冻结就是当前升级阻断条件。",
        )
    if state == "approaching_source_prz":
        return (
            "价格尚未进入 Source Raw PRZ。",
            "先看 Source PRZ 入场边界是否被实际测试。",
            "进入后再看是否继续测试 PRZ terminal side。",
            "未进入 Source PRZ 前，不得把潜在完成当作已完成。",
        )
    if state in {"entered_source_prz", "waiting_terminal"}:
        return (
            "价格已进入/曾进入 Source Raw PRZ，但 Source T-Bar 尚未成立。",
            "先看 PRZ terminal side 是否被完整测试并形成 Source Terminal Price Bar。",
            "T-Bar 成立后再进入 PEZ / T+1 / Type-I 反应观察。",
            "仅进入 PRZ 不等于完成；没有 terminal-side test 就不能升级。",
        )
    if state == "source_terminal_complete":
        return (
            "Source Terminal Price Bar 已完成。",
            "先保留 T-Bar 极值与 PEZ，不在同一根完成 bar 上回填执行结论。",
            "下一交易观察点是 T-Bar+1，再看 Type-I 38.2% 反应。",
            "T-Bar 当根不自动等于可执行确认。",
        )
    if state in {"t_plus_1", "type_i_early_reaction"}:
        return (
            "处于 Source T-Bar 后的早期 Type-I 反应窗口。",
            "先看前 5 根 bar 内是否到达 38.2% Type-I objective。",
            "38.2% 早期确认后，再看 61.8% 与后续是否形成 Type-II 条件。",
            "未到 38.2% 前只能观察反应，不能把它升级为 Type-I confirmed。",
        )
    if state == "type_i_confirmed":
        return (
            "Type-I 38.2% 早期反应已确认。",
            "先看 61.8% 目标及首次 reversal-direction 离开 Source PRZ 的质量。",
            "若后续重新进入 Source PRZ，再按 strict full retest 观察 Type-II。",
            "Type-I confirmation 不等于长期 reversal，也不能跳过 Type-II 的完整回测要求。",
        )
    if state == "type_i_failed":
        return (
            "Source T-Bar 后前 5 根 bar 未达到 38.2% early objective。",
            "先停止把当前路径称为早期 Type-I confirmed。",
            "后续若迟到 38.2%，只记 reaction_only；若形成严格二次回测，再单独评估 Type-II。",
            "早期 Type-I 窗口已经失败，后验反弹不能回填早期确认。",
        )
    if state == "reaction_only":
        return (
            "出现了迟到的 38.2% reaction，但不属于早期 Type-I confirmed。",
            "先把它维持为 reaction-only 证据。",
            "后续只有独立满足 strict Type-II 条件，才能升级新的阶段。",
            "迟到反应不能回写成早期 Type-I confirmation。",
        )
    if state == "type_ii_retest_forming":
        return (
            "已发生 reversal-direction 离区后重新进入 Source PRZ，Type-II 回测形成中。",
            "先看是否完整回测 Source Raw PRZ terminal side。",
            "完整 terminal-side retest 形成 Type-II T-Bar 后，再看再次向反转方向离区。",
            "部分 PRZ overlap 不足以升级为 Type-II Terminal。",
        )
    if state == "type_ii_terminal":
        return (
            "严格 Type-II terminal-side retest 已完成。",
            "先看价格是否再次向 reversal direction 离开 Source PRZ。",
            "离区后才进入 reversal_evidence；否则维持 Type-II Terminal。",
            "Type-II T-Bar 本身不是长期反转证明。",
        )
    if state == "reversal_evidence":
        return (
            "严格 Type-II retest 后已出现 reversal-direction 离区证据。",
            "先跟踪该离区是否保持，以及 Source PRZ 是否再次被破坏性重入。",
            "后续进入更长周期管理，但不能把这一状态解释成确定长期趋势。",
            "当前系统没有冻结额外 Carney 长期失效价，不应凭 context 自造失效线。",
        )
    return (
        "当前 lifecycle 已进入不可升级/保留状态。",
        "先核查 Source PRZ 与 source-clock evidence。",
        "只有重新获得 source-backed 可观察证据后再评估。",
        "禁止用后验价格、市场或题材 context 救活失效身份。",
    )


def build_decision_narrative(
    *,
    source_lifecycle: dict[str, Any] | None,
    context_integrity: dict[str, Any] | None,
    execution_context: dict[str, Any] | None = None,
) -> DecisionNarrative:
    lifecycle = source_lifecycle or {}
    state = str(lifecycle.get("state") or "source_clock_unavailable")
    current, first, next_, blocker = _texts(state)

    cautions: list[str] = []
    execution_integrity_state = "missing"
    for layer in (context_integrity or {}).get("layers") or []:
        layer_name = str(layer.get("layer") or "unknown")
        layer_state = str(layer.get("state") or "missing")
        if layer_name == "execution":
            execution_integrity_state = layer_state
        if layer_state != "current":
            cautions.append(
                f"{layer_name}:{layer_state} — {str(layer.get('reason') or '').strip()}"
            )

    execution = execution_context or {}
    if execution_integrity_state != "current":
        execution_gate = f"execution_{execution_integrity_state}"
    elif execution.get("tradable_on_as_of_date") is False:
        execution_gate = "blocked_suspended"
    elif execution.get("tradable_on_as_of_date") is True:
        execution_gate = "tradable"
    else:
        execution_gate = "tradability_unresolved"

    return DecisionNarrative(
        lifecycle_state=state,
        action_state=_ACTION.get(state, "evidence_insufficient"),
        current_position=current,
        first_watch=first,
        next_watch=next_,
        upgrade_blocker=blocker,
        next_key_price=(
            None if lifecycle.get("next_key_price") is None
            else float(lifecycle["next_key_price"])
        ),
        next_key_price_role=(
            None if lifecycle.get("next_key_price_role") is None
            else str(lifecycle["next_key_price_role"])
        ),
        execution_context_gate=execution_gate,
        context_cautions=tuple(cautions),
    )
