from __future__ import annotations

from dataclasses import asdict
from typing import Any

import pandas as pd

from htcn.app.harmonic_service import LocalHarmonicService
from htcn.harmonic.abcd_source import abcd_bc_layering_example, with_abcd_source_prz
from htcn.harmonic.execution import observe_source_execution
from htcn.harmonic.models import PatternDirection
from htcn.harmonic.prz import PRZComponent, PotentialReversalZone
from htcn.harmonic.source_prz_evidence import source_prz_evidence


class SourceAlignedHarmonicService(LocalHarmonicService):
    """Compatibility-preserving API adapter for the source-fidelity contract."""

    @staticmethod
    def _prz_payload(prz: PotentialReversalZone) -> dict[str, Any]:
        effective = with_abcd_source_prz(prz) if prz.pattern_id == "abcd" else prz
        legacy = LocalHarmonicService._prz_payload(prz)
        component_low = float(prz.component_envelope_low)
        component_high = float(prz.component_envelope_high)
        ideal_low = float(prz.ideal_core_low)
        ideal_high = float(prz.ideal_core_high)
        source_available = bool(effective.has_source_prz)
        source_low = float(effective.source_prz_low) if effective.source_prz_low is not None else None
        source_high = float(effective.source_prz_high) if effective.source_prz_high is not None else None
        evidence = source_prz_evidence(prz.pattern_id)
        abcd_evidence_level = (
            "source_specification_plus_market_examples_membership_only"
            if prz.pattern_id == "abcd"
            else "unregistered"
        )

        return {
            **legacy,
            "semantics_version": 3,
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
                "status": effective.source_prz_status,
                "component_names": list(effective.source_prz_component_names),
                "defining_component": effective.source_prz_defining_component,
                "selection_method": effective.source_prz_selection_method,
                "source_refs": list(effective.source_prz_source_refs),
                "source_note": effective.source_prz_note or None,
                "unresolved_reason": effective.source_prz_reason,
                "profile_version": 2,
                "evidence_level": (
                    evidence.evidence_level if evidence else abcd_evidence_level
                ),
                "source_membership_authority": (
                    evidence.source_membership_authority
                    if evidence
                    else ("Carney Vol1/Vol3" if prz.pattern_id == "abcd" else None)
                ),
                "selection_authority": (
                    evidence.selection_authority
                    if evidence
                    else (
                        "Carney-defined equivalent AB=CD + reciprocal BC pair"
                        if prz.pattern_id == "abcd"
                        else None
                    )
                ),
                "market_case_ids": list(evidence.market_case_ids) if evidence else [],
                "known_source_tensions": list(evidence.known_tensions) if evidence else [],
                "coordinate_regression_status": (
                    evidence.coordinate_regression_status if evidence else "pending_book_coordinates"
                ),
            },
        }

    def _abcd_payload(self, *args, **kwargs) -> dict[str, Any]:
        payload = super()._abcd_payload(*args, **kwargs)
        item = args[0] if args else kwargs["item"]
        evaluation = item.evaluation
        layer = abcd_bc_layering_example(
            item.points,
            reciprocal_bc_target=float(evaluation.reciprocal_bc_target),
        )
        payload["execution_tolerance"] = {
            **asdict(layer),
            "raw_prz_membership": False,
            "identity_membership": False,
        }
        return payload

    def _abcd_forming_payload(self, *args, **kwargs) -> dict[str, Any]:
        payload = super()._abcd_forming_payload(*args, **kwargs)
        item = args[0] if args else kwargs["item"]
        projection = item.projection
        layer = abcd_bc_layering_example(
            item.points,
            reciprocal_bc_target=float(projection.reciprocal_bc_target),
        )
        payload["execution_tolerance"] = {
            **asdict(layer),
            "raw_prz_membership": False,
            "identity_membership": False,
        }
        return payload

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

    def _five_zero_payload(self, *args, **kwargs) -> dict[str, Any]:
        payload = super()._five_zero_payload(*args, **kwargs)
        item = args[0] if args else kwargs["item"]
        evaluation = item.evaluation
        contract = evaluation.source_contract
        payload["prz"] = self._prz_payload(evaluation.prz)
        payload["source_contract"] = {
            "status": "structural_source_prz_frozen_execution_label_conflict_quarantined",
            "price_50_bc": float(contract.price_50_bc),
            "reciprocal_abcd_price": float(contract.reciprocal_abcd_price),
            "reciprocal_relation": contract.reciprocal_relation,
            "source_prz_low": float(contract.source_prz_low),
            "source_prz_high": float(contract.source_prz_high),
            "raw_prz_members": list(evaluation.prz.source_prz_component_names),
            "source_raw_prz_test": bool(evaluation.source_raw_prz_test),
            "completion_class": evaluation.completion_class,
        }
        payload["v3_execution_refinement"] = asdict(contract.execution_refinement)
        payload["compatibility_diagnostics"] = {
            "legacy_reciprocal_inside_50_618_band": bool(
                evaluation.reciprocal_inside_execution_band
            ),
            "identity_gate": False,
            "note": "该旧 band 指标仅保留兼容审计，M2.29 起不得参与 5-0 pass/fail。",
        }
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
                pattern["execution_clock_policy"] = (
                    "structural_source_prz_frozen_v3_execution_label_conflict_quarantined"
                )
        analysis["price_zone_contract"] = {
            "version": 3,
            "source_prz_profile_version": 2,
            "static_layers": ["ideal_core", "component_envelope", "source_prz"],
            "dynamic_layer": "execution_clock.pez",
            "execution_only_layers": [
                "ABCD.execution_tolerance",
                "FIVE_ZERO.v3_execution_refinement",
            ],
            "fail_closed_without_source_prz": True,
            "legacy_price_low_high_mean": "ideal_core",
            "source_membership_authority": "Carney source families per pattern",
            "source_selection_authority": "HT-CN operational convergence only where Carney leaves multiple source-valid complements",
        }
        analysis["engine_note"] = (
            str(analysis.get("engine_note") or "")
            + " M2.28 已把 standalone AB=CD 的等距完成价 + reciprocal BC 解冻为 Source Raw PRZ；"
            "Volume Three BC layering 单列为 execution tolerance，绝不进入 identity 或 Raw PRZ。"
            " M2.29 已冻结 5-0 的 Volume Two Structural Raw PRZ=50% BC + Reciprocal AB=CD；"
            "Volume Three 61.8 仅作为 execution refinement/stop reference，并显式保留 XA/AB 标签冲突。"
            "5-0 仍处于 production quarantine；Alternate Bat 仍 source-conflict fail closed。"
        ).strip()
        return analysis
