from __future__ import annotations

from typing import Any

import pandas as pd

from htcn.app.harmonic_service import LocalHarmonicService
from htcn.harmonic.execution import observe_source_execution
from htcn.harmonic.models import PatternDirection
from htcn.harmonic.prz import PRZComponent, PotentialReversalZone
from htcn.harmonic.source_prz_evidence import source_prz_evidence


class SourceAlignedHarmonicService(LocalHarmonicService):
    """Compatibility-preserving API adapter for the source-fidelity contract.

    The legacy service remains the deterministic geometry producer. This adapter makes the
    semantic layers explicit at the API boundary and adds the no-lookahead execution clock to
    current forming patterns. It does not rewrite identity, PRZ geometry or historical outcome
    evidence.
    """

    @staticmethod
    def _prz_payload(prz: PotentialReversalZone) -> dict[str, Any]:
        legacy = LocalHarmonicService._prz_payload(prz)
        component_low = float(prz.component_envelope_low)
        component_high = float(prz.component_envelope_high)
        ideal_low = float(prz.ideal_core_low)
        ideal_high = float(prz.ideal_core_high)
        source_available = bool(prz.has_source_prz)
        source_low = float(prz.source_prz_low) if prz.source_prz_low is not None else None
        source_high = float(prz.source_prz_high) if prz.source_prz_high is not None else None
        evidence = source_prz_evidence(prz.pattern_id)

        return {
            **legacy,
            "semantics_version": 2,
            "legacy_price_semantics": "ideal_core",
            "ideal_core": {
                "price_low": ideal_low,
                "price_high": ideal_high,
                "width": ideal_high - ideal_low,
                "status": "htcn_convergence_selection",
            },
            "component_envelope": {
                "price_low": component_low,
                "price_high": component_high,
                "width": component_high - component_low,
                "status": "audit_envelope_not_source_prz",
            },
            "source_prz": {
                "available": source_available,
                "price_low": source_low,
                "price_high": source_high,
                "width": (
                    source_high - source_low
                    if source_low is not None and source_high is not None
                    else None
                ),
                "status": prz.source_prz_status,
                "component_names": list(prz.source_prz_component_names),
                "defining_component": prz.source_prz_defining_component,
                "selection_method": prz.source_prz_selection_method,
                "source_refs": list(prz.source_prz_source_refs),
                "source_note": prz.source_prz_note or None,
                "unresolved_reason": prz.source_prz_reason,
                "profile_version": 1,
                "evidence_level": evidence.evidence_level if evidence else "unregistered",
                "source_membership_authority": (
                    evidence.source_membership_authority if evidence else None
                ),
                "selection_authority": evidence.selection_authority if evidence else None,
                "market_case_ids": list(evidence.market_case_ids) if evidence else [],
                "known_source_tensions": list(evidence.known_tensions) if evidence else [],
                "coordinate_regression_status": (
                    evidence.coordinate_regression_status if evidence else "unregistered"
                ),
            },
        }

    def _shark_payload(self, *args, **kwargs) -> dict[str, Any]:
        payload = super()._shark_payload(*args, **kwargs)
        item = args[0] if args else kwargs["item"]
        frame = args[1] if len(args) > 1 else kwargs["frame"]
        evaluation = item.evaluation
        completion_index = int(item.points[-1].index)
        targets = payload["reaction_targets"]
        targets.update(
            {
                "initial_target": float(evaluation.initial_target),
                "initial_target_basis": evaluation.initial_target_basis,
                "bars_to_initial_target": self._bars_to_target(
                    frame,
                    completion_index=completion_index,
                    target=float(evaluation.initial_target),
                    direction=item.direction,
                ),
                "management_rule": "first_of_50_percent_or_reciprocal_abcd",
                "source_note": (
                    "Shark 为反应型结构。Volume Three 的初始获利目标取进入 5-0 PRZ 时"
                    "50% BC 回撤与 Reciprocal AB=CD 两项中从 C 点先到达者；61.8% 保留为"
                    "后续 5-0/风险边界测量，不能机械当作 Shark 第一目标。"
                ),
            }
        )
        return payload

    @staticmethod
    def _rebuild_prz_from_payload(pattern: dict[str, Any]) -> PotentialReversalZone:
        raw = pattern["prz"]
        source = raw.get("source_prz") or {}
        components = tuple(PRZComponent(**component) for component in raw.get("components") or [])
        if not components:
            raise ValueError("forming pattern PRZ payload has no auditable components")
        return PotentialReversalZone(
            pattern_id=str(pattern["pattern_id"]),
            direction=PatternDirection(str(pattern["direction"])),
            components=components,
            source_prz_low=(
                float(source["price_low"])
                if source.get("available") is True and source.get("price_low") is not None
                else None
            ),
            source_prz_high=(
                float(source["price_high"])
                if source.get("available") is True and source.get("price_high") is not None
                else None
            ),
            source_prz_component_names=tuple(source.get("component_names") or ()),
            source_prz_defining_component=source.get("defining_component"),
            source_prz_selection_method=source.get("selection_method"),
            source_prz_source_refs=tuple(source.get("source_refs") or ()),
            source_prz_note=str(source.get("source_note") or ""),
            source_prz_reason=source.get("unresolved_reason"),
        )

    @classmethod
    def _execution_clock_from_forming_payload(
        cls,
        pattern: dict[str, Any],
        frame: pd.DataFrame,
    ) -> dict[str, Any] | None:
        """Attach a source clock only where the generic Type-I anchor is well-defined.

        Standard XABCD and standalone AB=CD project D from a confirmed C frontier and use
        A as the later reaction anchor. Shark has a pattern-specific 5-0 target contract and
        5-0 itself remains source-conflict/research-only, so neither is silently forced through
        this generic clock.
        """
        schema = str(pattern.get("schema"))
        if schema not in {"XABCD", "ABCD"}:
            return None
        points = list(pattern.get("points") or [])
        if not points:
            return None
        frontier = points[-1]
        scale = int(pattern["scale"])
        signal_bar = int(frontier["index"]) + scale
        if signal_bar < 0 or signal_bar >= len(frame):
            return {
                "state": "frontier_confirmation_outside_returned_window",
                "signal_bar": signal_bar,
                "signal_clock_basis": "last_frontier_pivot_confirmed_at=index+scale",
                "confirmation_lag_bars": scale,
                "pez": {"available": False, "price_low": None, "price_high": None},
            }

        a_point = next((point for point in points if point.get("label") == "A"), None)
        if a_point is None:
            return None
        prz = cls._rebuild_prz_from_payload(pattern)
        audit = observe_source_execution(
            frame,
            signal_bar=signal_bar,
            direction=PatternDirection(str(pattern["direction"])),
            prz=prz,
            reaction_anchor_price=float(a_point["price"]),
            observation_end_bar=len(frame) - 1,
        )
        clock = audit.as_payload()
        clock.update(
            {
                "signal_clock_basis": "last_frontier_pivot_confirmed_at=index+scale",
                "frontier_pivot_index": int(frontier["index"]),
                "confirmation_lag_bars": scale,
                "retrospective_d_clock_used": False,
                "pez": {
                    "available": audit.pez_low is not None and audit.pez_high is not None,
                    "price_low": audit.pez_low,
                    "price_high": audit.pez_high,
                    "status": (
                        "terminal_integrated_execution_zone"
                        if audit.pez_low is not None and audit.pez_high is not None
                        else "not_available_before_terminal"
                    ),
                },
            }
        )
        return clock

    def analyze(self, *args, **kwargs) -> dict[str, Any]:
        analysis = super().analyze(*args, **kwargs)
        frame = pd.DataFrame(analysis.get("bars") or [])
        for pattern in analysis.get("forming") or []:
            clock = self._execution_clock_from_forming_payload(pattern, frame)
            if clock is not None:
                pattern["execution_clock"] = clock
            elif pattern.get("schema") == "0XABC":
                pattern["execution_clock_policy"] = "shark_uses_pattern_specific_5_0_target_contract"
            elif pattern.get("schema") == "FIVE_ZERO":
                pattern["execution_clock_policy"] = "source_conflict_research_only"
        analysis["price_zone_contract"] = {
            "version": 2,
            "source_prz_profile_version": 1,
            "static_layers": ["ideal_core", "component_envelope", "source_prz"],
            "dynamic_layer": "execution_clock.pez",
            "fail_closed_without_source_prz": True,
            "legacy_price_low_high_mean": "ideal_core",
            "source_membership_authority": "Carney source families per pattern",
            "source_selection_authority": "HT-CN operational convergence inside source-valid families; exposed per pattern",
        }
        analysis["engine_note"] = (
            str(analysis.get("engine_note") or "")
            + " M2.27 标准 XABCD Source PRZ 使用逐形态 Golden Profile 选择并暴露组成测量/来源；"
            "Carney 决定合法测量族，HT-CN 只在合法族内做收敛选择。Ideal Core 继续作为独立工程层，"
            "Alternate Bat 等冲突项继续 fail closed；Book Case Ledger 与坐标级回归状态单独暴露。"
        ).strip()
        return analysis
